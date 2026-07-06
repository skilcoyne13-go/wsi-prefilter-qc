from __future__ import annotations
import csv
import json
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from .. import __version__

LABELS = {
    "MACRO_LABEL_MISMATCH": "Macro/label match",
    "TISSUE_FINDER_EXCLUSION": "Tissue finder",
    "DUPLICATE_MACRO_LABEL": "Duplicate label",
    "SCAN_AREA_MISMATCH": "Scan area",
}


def _stem(slide_path):
    return Path(slide_path).stem


class Reporter(ABC):
    name = "base"

    @abstractmethod
    def write(self, slide_path, result, cfg):
        raise NotImplementedError


class JsonReporter(Reporter):
    name = "json"

    def write(self, slide_path, result, cfg):
        payload = dict(result.to_dict())
        payload["slide"] = Path(slide_path).name
        payload["processed_at"] = datetime.now().isoformat(timespec="seconds")
        payload["tool_version"] = __version__
        payload["macro_label_confidence"] = result.confidence_for("MACRO_LABEL_MISMATCH")
        payload["findings"] = [
            {"code": f.code, "passed": f.passed, "severity": f.severity.value,
             "confidence": f.confidence, "message": f.message}
            for f in result.findings
        ]
        out = Path(cfg["reports"]) / (_stem(slide_path) + ".qcreport.json")
        out.write_text(json.dumps(payload, indent=2))


class TextReporter(Reporter):
    name = "text"

    def write(self, slide_path, result, cfg):
        d = result.to_dict()
        lines = ["WSI QC Report", "============="]
        lines.append("Slide:        " + Path(slide_path).name)
        lines.append("Processed:    " + datetime.now().isoformat(timespec="seconds"))
        lines.append("Tool version: " + __version__)
        lines.append("")
        verdict = "PASS" if d["qc_passed"] else "REVIEW"
        lines.append("VERDICT: " + verdict + "   (overall confidence "
                     + str(d["confidence_score"]) + ")")
        lines.append("Macro/label confidence: "
                     + str(result.confidence_for("MACRO_LABEL_MISMATCH")))
        lines.append("")
        lines.append("Findings:")
        for f in result.findings:
            tag = "PASS" if f.passed else "FLAG"
            label = LABELS.get(f.code, f.code)
            lines.append("  [" + tag + "] " + label + " (" + f.severity.value
                         + ", conf " + ("%.2f" % f.confidence) + ")")
            lines.append("         " + f.message)
        out = Path(cfg["reports"]) / (_stem(slide_path) + ".qcreport.txt")
        out.write_text("\n".join(lines) + "\n")


class CsvManifestReporter(Reporter):
    # One row per slide appended to reports/manifest.csv - the high-volume view,
    # and an easy import target for a LIS.
    name = "csv"
    COLUMNS = ["processed_at", "slide", "qc_passed", "confidence_score",
               "macro_label_confidence", "mismatch_detected",
               "tissue_omission_detected", "duplicate_label_detected",
               "findings_summary"]

    def write(self, slide_path, result, cfg):
        d = result.to_dict()
        path = Path(cfg["reports"]) / "manifest.csv"
        is_new = not path.exists()
        with path.open("a", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            if is_new:
                w.writerow(self.COLUMNS)
            w.writerow([
                datetime.now().isoformat(timespec="seconds"),
                Path(slide_path).name, d["qc_passed"], d["confidence_score"],
                result.confidence_for("MACRO_LABEL_MISMATCH"),
                d["mismatch_detected"], d["tissue_omission_detected"],
                d["duplicate_label_detected"], d["findings_summary"],
            ])


REPORTERS = {
    JsonReporter.name: JsonReporter,
    TextReporter.name: TextReporter,
    CsvManifestReporter.name: CsvManifestReporter,
}


def build_reporters(cfg):
    return [REPORTERS[name]() for name in cfg["outputs"] if name in REPORTERS]
