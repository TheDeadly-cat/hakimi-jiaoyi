from __future__ import annotations

from pathlib import Path
import sys


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SOURCE_ROOT = REPOSITORY_ROOT / "src"
LEGACY_PROJECT_ROOT = REPOSITORY_ROOT / "outputs" / "python_quant_bot"


def activate_legacy_project_root() -> Path:
    package_root = LEGACY_PROJECT_ROOT / "quant_bot"
    if not package_root.is_dir():
        raise RuntimeError("legacy_project_root_missing_during_source_migration")
    project_text = str(LEGACY_PROJECT_ROOT)
    if project_text not in sys.path:
        sys.path.insert(0, project_text)
    return LEGACY_PROJECT_ROOT
