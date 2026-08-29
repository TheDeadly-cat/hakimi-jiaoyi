from __future__ import annotations

from pathlib import Path
import sys


SOURCE_LAYOUT_SCHEMA_VERSION = "canonical-source-layout-v1"


def activate_canonical_source() -> Path:
    source_root = Path(__file__).resolve().parents[2] / "src"
    package_root = source_root / "hakimi_research"
    if not package_root.is_dir():
        raise RuntimeError("canonical_source_root_missing")
    source_text = str(source_root)
    if source_text not in sys.path:
        sys.path.insert(0, source_text)
    return source_root
