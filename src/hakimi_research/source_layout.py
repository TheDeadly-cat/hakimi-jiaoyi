from __future__ import annotations

import os
from pathlib import Path


PACKAGE_ROOT = Path(__file__).resolve().parent
_CHECKOUT_CANDIDATE = PACKAGE_ROOT.parent.parent
# Never infer installed runtime resources or Git identity from site-packages.
REPOSITORY_ROOT = (
    _CHECKOUT_CANDIDATE
    if PACKAGE_ROOT.parent.name == "src"
    and (_CHECKOUT_CANDIDATE / "pyproject.toml").is_file()
    else None
)
CANONICAL_SOURCE_ROOT = PACKAGE_ROOT.parent
RESOURCE_ROOT = PACKAGE_ROOT / "resources"
DEFAULT_CONFIG_PATH = RESOURCE_ROOT / "config.example.json"
DEFAULT_EXPERIMENT_SPEC_PATH = RESOURCE_ROOT / "experiment.example.json"
CANONICAL_DEPENDENCY_LOCK = (
    REPOSITORY_ROOT / "requirements.research.lock"
    if REPOSITORY_ROOT is not None
    else RESOURCE_ROOT / "requirements.research.lock"
)
LEGACY_PROJECT_ROOT = (
    REPOSITORY_ROOT / "outputs" / "python_quant_bot"
    if REPOSITORY_ROOT is not None else None
)


def default_artifact_root() -> Path:
    """Independent writable storage; merely resolving it creates nothing."""
    configured = os.environ.get("HAKIMI_RESEARCH_HOME")
    return (Path(configured).expanduser() if configured else Path.home() / ".hakimi-research").resolve()
