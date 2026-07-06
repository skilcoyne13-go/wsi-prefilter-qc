import argparse

import numpy as np

from wsi_qc.config import load_config
from wsi_qc.runner import QCRunner
from wsi_qc.models import SlideInputs, SlideMetadata


def _demo(runner):
    rng = np.random.default_rng(0)
    macro = (rng.random((200, 600, 3)) * 255).astype(np.uint8)
    label = np.full((200, 200, 3), 240, dtype=np.uint8)  # blank on purpose
    thumb = (rng.random((200, 600, 3)) * 255).astype(np.uint8)
    meta = SlideMetadata(patient_id="P123", case_id="C-2026-0001",
                         barcode_string="C-2026-0001")
    inputs = SlideInputs(wsi_path="DEMO_slide.svs", macro_image=macro,
                         thumbnail_image=thumb, label_image=label, metadata=meta)
    result = runner.pipeline.run(inputs)
    runner.report_result("DEMO_slide.svs", result)
    print("Demo reports written to", runner.cfg["reports"])
    print("(synthetic slide has a blank label, so it correctly flags for review)")


def main():
    ap = argparse.ArgumentParser(description="WSI QC folder processor")
    ap.add_argument("--config", default="config.json")
    ap.add_argument("--watch", action="store_true", help="keep watching the inbox")
    ap.add_argument("--demo", action="store_true", help="write a sample report, no slide needed")
    args = ap.parse_args()

    cfg = load_config(args.config)
    runner = QCRunner(cfg)

    if args.demo:
        _demo(runner)
    elif args.watch:
        runner.run_watch()
    else:
        runner.run_once()


if __name__ == "__main__":
    main()
