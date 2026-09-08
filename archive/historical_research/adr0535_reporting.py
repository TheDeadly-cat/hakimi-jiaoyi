from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
import re


_ARTIFACT_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")


def save_json_report(
    payload: dict,
    directory: str,
    prefix: str,
    *,
    artifact_id: str = "",
) -> str:
    Path(directory).mkdir(parents=True, exist_ok=True)
    if artifact_id:
        if type(artifact_id) is not str or _ARTIFACT_ID_RE.fullmatch(artifact_id) is None:
            raise ValueError("report artifact_id is invalid")
        stamp = artifact_id
    else:
        stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    path = Path(directory) / f"{prefix}_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return str(path)
