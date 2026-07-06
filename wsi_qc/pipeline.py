from __future__ import annotations
from abc import ABC, abstractmethod
from .models import QCResult, Severity

BLOCKING = (Severity.CRITICAL, Severity.ERROR)


class QCCheck(ABC):
    code = "BASE"

    @abstractmethod
    def run(self, current, previous):
        raise NotImplementedError


class QCPipeline:
    def __init__(self, checks):
        self.checks = checks

    def run(self, current, previous=None) -> QCResult:
        findings = [c.run(current, previous) for c in self.checks]
        blocking = [f for f in findings if (not f.passed) and f.severity in BLOCKING]
        confidence = min([f.confidence for f in findings], default=1.0)

        def failed(code):
            # Counts only as a real failure if it is a blocking severity, so an
            # "unreadable / cannot tell" WARNING does not register as a mismatch.
            return any(
                (f.code == code and not f.passed and f.severity in BLOCKING)
                for f in findings
            )

        passed = len(blocking) == 0
        return QCResult(
            qc_passed=passed,
            mismatch_detected=failed("MACRO_LABEL_MISMATCH"),
            tissue_omission_detected=failed("TISSUE_FINDER_EXCLUSION"),
            duplicate_label_detected=failed("DUPLICATE_MACRO_LABEL"),
            confidence_score=confidence,
            findings_summary=self._summarize(findings),
            findings=findings,
        )

    @staticmethod
    def _summarize(findings):
        problems = [f.message for f in findings if not f.passed]
        if not problems:
            return "All QC checks passed."
        return " | ".join(problems)
