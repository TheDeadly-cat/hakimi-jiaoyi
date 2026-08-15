from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


def save_json_report(payload: dict, directory: str, prefix: str) -> str:
    Path(directory).mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = Path(directory) / f"{prefix}_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
