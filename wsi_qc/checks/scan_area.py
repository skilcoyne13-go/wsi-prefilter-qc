from ..models import Finding, Severity
from ..pipeline import QCCheck

CODE = "SCAN_AREA_MISMATCH"


class ScanAreaCheck(QCCheck):
    # Bounding-box check (stub): if a pre-scan scan area exists, confirm the
    # digitized region matches it. Not yet implemented.
    code = CODE

    def run(self, current, previous):
        return Finding(code=CODE, severity=Severity.INFO, passed=True, confidence=1.0,
                       message="Scan-area check not yet implemented.")
