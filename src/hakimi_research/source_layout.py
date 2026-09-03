from __future__ import annotations

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_SOURCE_ROOT = REPOSITORY_ROOT / "src"
CANONICAL_DEPENDENCY_LOCK = REPOSITORY_ROOT / "requirements.research.lock"
LEGACY_PROJECT_ROOT = REPOSITORY_ROOT / "outputs" / "python_quant_bot"
