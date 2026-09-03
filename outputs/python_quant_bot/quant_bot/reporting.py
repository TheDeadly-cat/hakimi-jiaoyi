"""Compatibility imports for canonical deterministic JSON reporting."""

from hakimi_research.reporting import (
    RESEARCH_JSON_REPORT_SCHEMA_VERSION,
    plan_json_report_path,
    render_json_report,
    save_json_report,
)

__all__ = [
    "RESEARCH_JSON_REPORT_SCHEMA_VERSION",
    "plan_json_report_path",
    "render_json_report",
    "save_json_report",
]
