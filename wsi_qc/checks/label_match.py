from __future__ import annotations
import re
from difflib import SequenceMatcher
from pathlib import Path

from ..models import Finding, Severity
from ..pipeline import QCCheck
from ..identity import parse_identity

CODE = "MACRO_LABEL_MISMATCH"


def _norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", s or "").upper()


def _similarity(a, b):
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _read_barcode(label):
    try:
        import zxingcpp
        results = zxingcpp.read_barcodes(label)
        return results[0].text if results else None
    except Exception:
        return None


_READER = None


def _ocr(label):
    global _READER
    try:
        import easyocr
        if _READER is None:
            _READER = easyocr.Reader(["en"], gpu=False)
        out = _READER.readtext(label)
        if not out:
            return "", 0.0
        text = " ".join([t for _, t, _ in out])
        conf = float(sum([c for _, _, c in out]) / len(out))
        return text, conf
    except Exception:
        return "", 0.0


def _structured_match(read_id, ref_id):
    # True/False when case is known on both sides (a definite verdict); None
    # when there isn't enough to decide (e.g. the ref isn't in
    # case/partset/stain form) and the caller should fall back to fuzzy text
    # similarity instead. Stain is never compared here - a barcode that omits
    # the stain, or has a different one, is not a mismatch by itself.
    if not read_id.case or not ref_id.case:
        return None
    if read_id.case != ref_id.case:
        return False
    if read_id.partset and ref_id.partset:
        return read_id.partset == ref_id.partset
    return None


def _file_stem(current):
    try:
        return Path(str(current.wsi_path)).stem
    except Exception:
        return ""


class MacroLabelMatchCheck(QCCheck):
    code = CODE

    def __init__(self, ocr_match_threshold=0.85, filename_match_threshold=0.90):
        self.ocr_match_threshold = ocr_match_threshold
        self.filename_match_threshold = filename_match_threshold

    def _references(self, current):
        m = current.metadata
        refs = []
        if m.barcode_string:
            refs.append(("barcode", m.barcode_string))
        if m.case_id:
            refs.append(("case_id", m.case_id))
        if m.patient_id:
            refs.append(("patient_id", m.patient_id))
        return refs

    def run(self, current, previous):
        label = current.label_image

        decoded = _read_barcode(label) if label is not None else None
        read_value, read_kind, read_conf = None, None, 0.0
        if decoded:
            read_value, read_kind, read_conf = decoded, "barcode", 0.99
        else:
            text, ocr_conf = _ocr(label) if label is not None else ("", 0.0)
            if text:
                read_value, read_kind, read_conf = text, "OCR text", ocr_conf

        if not read_value:
            return Finding(code=CODE, severity=Severity.WARNING, passed=False,
                           confidence=0.10,
                           message="Label unreadable: no barcode decoded and OCR empty. Flag for review.")

        refs = self._references(current)
        read_id = parse_identity(read_value)

        if refs:
            for kind, val in refs:
                ref_id = parse_identity(val)
                verdict = _structured_match(read_id, ref_id)
                if verdict is None:
                    continue
                if verdict:
                    conf = round(min(0.99, read_conf), 2) if read_kind == "barcode" \
                        else round(min(0.90, 0.5 * read_conf + 0.5), 2)
                    stain_note = ""
                    if not read_id.stain:
                        stain_note = " (barcode omits stain, as usual)"
                    return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=conf,
                                   message="Label " + read_kind + " '" + read_value
                                           + "' matches expected " + kind + " '" + val
                                           + "' - case and partset agree" + stain_note + ".")
                return Finding(code=CODE, severity=Severity.CRITICAL, passed=False,
                               confidence=round(min(0.99, read_conf), 2),
                               message="Label " + read_kind + " '" + read_value + "' (case "
                                       + str(read_id.case) + ", partset " + str(read_id.partset)
                                       + ") does not match expected " + kind + " '" + val + "' (case "
                                       + str(ref_id.case) + ", partset " + str(ref_id.partset)
                                       + "). Possible label swap.")

            # No ref gave a structured verdict (not in case/partset form) -
            # fall back to plain fuzzy text similarity.
            best_kind, best = None, 0.0
            for kind, val in refs:
                sim = _similarity(read_value, val)
                if sim > best:
                    best_kind, best = kind, sim
            if best >= self.ocr_match_threshold:
                if read_kind == "barcode":
                    conf = round(min(0.99, read_conf), 2)
                else:
                    conf = round(min(0.90, 0.5 * read_conf + 0.5 * best), 2)
                return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=conf,
                               message="Label " + read_kind + " '" + read_value
                                       + "' matches metadata " + best_kind + ".")
            return Finding(code=CODE, severity=Severity.CRITICAL, passed=False,
                           confidence=round(min(0.99, read_conf), 2),
                           message="Label " + read_kind + " '" + read_value
                                   + "' does not match metadata " + best_kind
                                   + " (similarity " + ("%.2f" % best) + "). Possible label swap.")

        stem = _file_stem(current)
        stem_id = parse_identity(stem)
        stem_verdict = _structured_match(read_id, stem_id)
        fn_sim = _similarity(read_value, stem)

        if stem_verdict or (stem_verdict is None and stem and fn_sim >= self.filename_match_threshold):
            detail = "case and partset agree" if stem_verdict else ("similarity " + ("%.2f" % fn_sim))
            return Finding(code=CODE, severity=Severity.INFO, passed=True,
                           confidence=round(min(0.85, 0.6 + 0.3 * fn_sim), 2),
                           message="No case metadata provided; label " + read_kind + " '"
                                   + read_value + "' matches the filename (" + detail + ").")
        return Finding(code=CODE, severity=Severity.WARNING, passed=False, confidence=0.40,
                       message="Label read as '" + read_value + "' but no case metadata "
                               "was provided to verify it against (filename similarity "
                               + ("%.2f" % fn_sim) + "). Supply a .qc.json sidecar to enable the swap check.")