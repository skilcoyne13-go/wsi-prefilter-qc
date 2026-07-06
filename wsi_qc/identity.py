from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

# Real naming convention (filenames, and usually barcodes too):
#   <case>_<partset>_<stain>
# - <case> is like "SK26-493035" - the hyphen is part of the case number, so
#   only "_" is treated as a field separator, never "-".
# - <partset> is one or more block letters (A, AB, ABC, ...).
# - <stain> (HE, HP, ABPAS, ...) is optional - barcodes frequently omit it,
#   since the barcode is usually just "<case>_<partset>".


@dataclass(frozen=True)
class SlideIdentity:
    case: Optional[str] = None
    partset: Optional[str] = None
    stain: Optional[str] = None


def parse_identity(text):
    # Splits on "_" only, positionally: 1st field is case, 2nd is partset,
    # 3rd (if present) is stain. Normalized to upper-case so comparisons
    # between filename/barcode/OCR text are case-insensitive.
    if not text:
        return SlideIdentity()
    parts = [p for p in str(text).strip().upper().split("_") if p]
    case = parts[0] if len(parts) >= 1 else None
    partset = parts[1] if len(parts) >= 2 else None
    stain = parts[2] if len(parts) >= 3 else None
    return SlideIdentity(case=case, partset=partset, stain=stain)
