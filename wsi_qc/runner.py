from __future__ import annotations
import shutil
import time
import traceback
from pathlib import Path

from .config import ensure_dirs
from .loader import load_slide
from .pipeline import QCPipeline
from .io.reporters import build_reporters
from .io.sources import FolderSource
from .checks.label_match import MacroLabelMatchCheck
from .checks.tissue_finder import TissueFinderCheck
from .checks.duplicate_label import DuplicateLabelCheck
from .checks.scan_area import ScanAreaCheck
from .checks.tissue_clipping import TissueClippingCheck


def default_pipeline():
    return QCPipeline([
        MacroLabelMatchCheck(),
        TissueFinderCheck(),
        TissueClippingCheck(),
        DuplicateLabelCheck(),
        ScanAreaCheck(),
    ])


class QCRunner:
    def __init__(self, cfg, pipeline=None, source=None, reporters=None):
        self.cfg = cfg
        ensure_dirs(cfg)
        self.pipeline = pipeline or default_pipeline()
        self.source = source or FolderSource(cfg["inbox"], cfg["extensions"])
        self.reporters = reporters if reporters is not None else build_reporters(cfg)

    def run_once(self, announce_empty=True):
        pending = self.source.pending()
        if not pending:
            if announce_empty:
                print("Nothing to process in", self.cfg["inbox"])
            return 0
        for path in pending:
            self._process_one(path)
        print("Processed", len(pending), "slide(s). Reports in", self.cfg["reports"])
        return len(pending)

    def run_watch(self):
        interval = self.cfg.get("watch_interval_seconds", 10)
        print("Watching", self.cfg["inbox"], "every", interval, "s. Ctrl+C to stop.")
        try:
            while True:
                self.run_once(announce_empty=False)
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\nStopped.")

    def report_result(self, slide_name, result):
        # Lets demo mode exercise the reporters without a real file on disk.
        for r in self.reporters:
            r.write(slide_name, result, self.cfg)

    def _process_one(self, path):
        path = Path(path)
        print("->", path.name)
        try:
            inputs = load_slide(path)
            result = self.pipeline.run(inputs)
            for r in self.reporters:
                r.write(path, result, self.cfg)
            verdict = "PASS" if result.qc_passed else "REVIEW"
            print("   ", verdict, "(confidence " + str(result.confidence_score) + ")")
            self._move(path, self.cfg["done"])
        except Exception as exc:
            print("    ERROR:", exc)
            self._write_error(path, exc)
            self._move(path, self.cfg["failed"])

    def _move(self, path, dest_dir):
        if not self.cfg.get("move_processed", True):
            return
        dest = Path(dest_dir)
        dest.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(path), str(dest / path.name))
            sidecar = path.with_suffix(".qc.json")
            if sidecar.exists():
                shutil.move(str(sidecar), str(dest / sidecar.name))
        except Exception as exc:
            print("    (could not move file:", exc, ")")

    def _write_error(self, path, exc):
        out = Path(self.cfg["reports"]) / (path.stem + ".error.txt")
        out.write_text("Failed to process " + path.name + "\n\n"
                       + "".join(traceback.format_exception_only(type(exc), exc)))
