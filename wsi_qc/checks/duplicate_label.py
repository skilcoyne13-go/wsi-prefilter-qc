from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from ..models import Finding, Severity
from ..pipeline import QCCheck
from ..identity import parse_identity

CODE = "DUPLICATE_MACRO_LABEL"


def _dhash_bits(label_image, hash_size=8):
    # Perceptual difference-hash: resize to (hash_size+1) x hash_size and
    # record, per row, whether each pixel is brighter than its left neighbor.
    # Robust to the label's exact scale/exposure, unlike a pixel diff.
    img = np.asarray(label_image)
    gray = img if img.ndim == 2 else cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    resized = cv2.resize(gray, (hash_size + 1, hash_size), interpolation=cv2.INTER_AREA)
    return (resized[:, 1:] > resized[:, :-1]).flatten()


def _hamming(a, b):
    return int(np.count_nonzero(a != b))


def _slide_identity(current):
    # Prefer metadata (barcode_string is usually the most literal
    # case/partset text, case_id sometimes lacks the partset) and fall back
    # to the filename, which always follows the <case>_<partset>_<stain>
    # convention even when no sidecar was filled in.
    m = current.metadata
    for val in (m.barcode_string, m.case_id):
        ident = parse_identity(val)
        if ident.case:
            return ident
    try:
        stem = Path(str(current.wsi_path)).stem
    except Exception:
        stem = str(current.wsi_path)
    return parse_identity(stem)


class DuplicateLabelCheck(QCCheck):
    # Failure Mode 3: catches a scanner "buffer freeze" - the camera captures
    # the same label frame for two consecutive slides instead of advancing to
    # the next physical glass. Detected with a perceptual dHash of the label
    # image compared against the previous slide THIS instance processed, then
    # disambiguated with (case, partset, stain) identity: two slides are the
    # same specimen only if ALL THREE agree. A different stain (e.g. HE vs
    # ABPAS on the same case/partset) is a legitimately distinct slide, not a
    # duplicate, even if the label images are visually near-identical.
    #
    # Note: QCPipeline.run() is only ever invoked with a single `current`
    # slide (the runner has no history mechanism), so the `previous` argument
    # is always None in practice. State therefore lives on the instance
    # itself and is updated on every call to run().
    code = CODE

    def __init__(self, hash_size=8, near_duplicate_bits=5):
        self.hash_size = hash_size
        self.near_duplicate_bits = near_duplicate_bits
        self._prev_hash = None
        self._prev_name = None
        self._prev_identity = None

    def run(self, current, previous):
        label = current.label_image
        name = self._slide_name(current)
        identity = _slide_identity(current)

        if label is None:
            self._remember(None, name, identity)
            return Finding(code=CODE, severity=Severity.WARNING, passed=True, confidence=0.3,
                           message="Duplicate-label check skipped: no label image available.")

        cur_hash = _dhash_bits(label, self.hash_size)
        prev_hash, prev_name, prev_identity = self._prev_hash, self._prev_name, self._prev_identity
        self._remember(cur_hash, name, identity)

        if prev_hash is None:
            return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=0.6,
                           message="Duplicate-label check: first slide in this run, nothing to compare against.")

        distance = _hamming(cur_hash, prev_hash)

        if distance > self.near_duplicate_bits:
            return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=0.7,
                           message="Label distinct from previous slide '" + prev_name
                                   + "' (dHash distance " + str(distance) + "/"
                                   + str(cur_hash.size) + "); no duplication detected.")

        prefix = ("Label nearly identical to previous slide '" + prev_name
                  + "' (dHash distance " + str(distance) + ")")

        if not identity.case or not prev_identity.case:
            return Finding(code=CODE, severity=Severity.WARNING, passed=False, confidence=0.4,
                           message=prefix + " but no case metadata is available on one or both "
                                   "slides to confirm whether this is a real duplicate or a scanner "
                                   "buffer freeze. Supply a .qc.json sidecar to enable this check.")

        if identity.case != prev_identity.case:
            return Finding(code=CODE, severity=Severity.WARNING, passed=False, confidence=0.5,
                           message=prefix + " but the cases differ ('" + prev_identity.case + "' vs '"
                                   + identity.case + "'). Flagging for review.")

        if not identity.partset or not prev_identity.partset:
            return Finding(code=CODE, severity=Severity.WARNING, passed=False, confidence=0.4,
                           message=prefix + " - same case ('" + identity.case + "') but the partset "
                                   "could not be confirmed on one or both slides.")

        if identity.partset != prev_identity.partset:
            return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=0.8,
                           message=prefix + ", but the case ('" + identity.case + "') matches with a "
                                   "different partset ('" + prev_identity.partset + "' vs '"
                                   + identity.partset + "') - normal for adjacent blocks from the same "
                                   "case, not a duplicate.")

        if not identity.stain or not prev_identity.stain:
            return Finding(code=CODE, severity=Severity.WARNING, passed=False, confidence=0.5,
                           message=prefix + " - same case ('" + identity.case + "') and partset ('"
                                   + identity.partset + "') but the stain could not be confirmed on "
                                   "one or both slides, so a true buffer-freeze duplicate can't be "
                                   "ruled out.")

        if identity.stain != prev_identity.stain:
            return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=0.8,
                           message=prefix + ", same case ('" + identity.case + "') and partset ('"
                                   + identity.partset + "'), but different stains ('"
                                   + prev_identity.stain + "' vs '" + identity.stain
                                   + "') - a distinct slide, not a duplicate.")

        return Finding(code=CODE, severity=Severity.CRITICAL, passed=False, confidence=0.9,
                       message=prefix + " and case ('" + identity.case + "'), partset ('"
                               + identity.partset + "') and stain ('" + identity.stain
                               + "') all match between two different slide files. Possible scanner "
                               "buffer freeze: the camera may have captured the same frame twice "
                               "instead of advancing to the next physical label.")

    def _remember(self, hash_, name, identity):
        self._prev_hash = hash_
        self._prev_name = name
        self._prev_identity = identity

    @staticmethod
    def _slide_name(current):
        try:
            return Path(str(current.wsi_path)).name
        except Exception:
            return str(current.wsi_path)
