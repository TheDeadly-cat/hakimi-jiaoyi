"""Installed terminal adapter; it never discovers or adds a source checkout."""
from pathlib import Path
import sys

SOURCE_LAYOUT_SCHEMA_VERSION = "terminal-installed-source-layout-v1"


def activate_canonical_source() -> Path:
    from hakimi_research import source_layout
    component = Path(__file__).resolve().parent
    if source_layout.LEGACY_PROJECT_ROOT != component:
        raise RuntimeError("terminal_installed_layout_not_initialized")
    root = Path(source_layout.CANONICAL_SOURCE_ROOT).resolve()
    if str(root) not in sys.path or not root.is_relative_to(component.parent):
        raise RuntimeError("terminal_installed_canonical_path_invalid")
    return root
