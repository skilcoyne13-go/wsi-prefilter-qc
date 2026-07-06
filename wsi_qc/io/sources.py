from __future__ import annotations
import time
from abc import ABC, abstractmethod
from pathlib import Path


class SlideSource(ABC):
    # Produces slide files ready for QC. A future IMSApiSource implements the
    # same .pending() contract, so the runner never changes.
    @abstractmethod
    def pending(self):
        raise NotImplementedError


class FolderSource(SlideSource):
    def __init__(self, inbox, extensions, stability_seconds=2.0):
        self.inbox = Path(inbox)
        self.extensions = tuple(extensions)
        self.stability_seconds = stability_seconds

    @staticmethod
    def _size(p):
        try:
            return p.stat().st_size
        except OSError:
            return None

    def pending(self):
        files = [p for p in self.inbox.glob("*")
                 if p.is_file() and p.suffix.lower() in self.extensions]
        if not files:
            return []
        # Skip files still being copied: size must hold steady briefly.
        sizes = {p: self._size(p) for p in files}
        time.sleep(self.stability_seconds)
        stable = [p for p in files
                  if sizes[p] is not None and self._size(p) == sizes[p]]
        return sorted(stable)
