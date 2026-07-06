from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import numpy as np


class Severity(str, Enum):
    # Severity only controls how prominently a finding is surfaced to the
    # pathologist. It NEVER blocks a case (this layer is advisory).
    CRITICAL = "critical"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class BoundingBox:
    # Pre-scan scan-area annotation, normalized 0..1 against the macro image.
    x: float
    y: float
    w: float
    h: float


@dataclass
class SlideMetadata:
    patient_id: str
    case_id: str
    barcode_string: str
    expected_fragment_count: Optional[int] = None
    bounding_box: Optional[BoundingBox] = None
    source_props: dict = field(default_factory=dict)


@dataclass
class SlideInputs:
    wsi_path: object
    macro_image: np.ndarray
    thumbnail_image: np.ndarray
    metadata: SlideMetadata
    label_image: Optional[np.ndarray] = None
    is_composite_macro: bool = False


@dataclass
class Finding:
    code: str
    severity: Severity
    passed: bool
    message: str
    confidence: float = 1.0


@dataclass
class QCResult:
    qc_passed: bool
    mismatch_detected: bool
    tissue_omission_detected: bool
    duplicate_label_detected: bool
    confidence_score: float
    findings_summary: str
    findings: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "qc_passed": self.qc_passed,
            "mismatch_detected": self.mismatch_detected,
            "tissue_omission_detected": self.tissue_omission_detected,
            "duplicate_label_detected": self.duplicate_label_detected,
            "confidence_score": round(self.confidence_score, 2),
            "findings_summary": self.findings_summary,
        }

    def confidence_for(self, code):
        for f in self.findings:
            if f.code == code:
                return f.confidence
        return None
