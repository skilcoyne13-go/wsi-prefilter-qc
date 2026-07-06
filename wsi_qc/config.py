from __future__ import annotations
import json
from pathlib import Path

DEFAULTS = {
    "inbox": "data/inbox",
    "reports": "data/reports",
    "done": "data/done",
    "failed": "data/failed",
    "extensions": [".svs", ".tif", ".tiff", ".ndpi", ".mrxs"],
    "outputs": ["json", "text", "csv"],
    "move_processed": True,
    "watch_interval_seconds": 10,
}


def load_config(path="config.json"):
    cfg = dict(DEFAULTS)
    p = Path(path)
    if p.exists():
        cfg.update(json.loads(p.read_text()))
    cfg["extensions"] = [e.lower() if e.startswith(".") else "." + e.lower()
                         for e in cfg["extensions"]]
    return cfg


def ensure_dirs(cfg):
    for key in ("inbox", "reports", "done", "failed"):
        Path(cfg[key]).mkdir(parents=True, exist_ok=True)
