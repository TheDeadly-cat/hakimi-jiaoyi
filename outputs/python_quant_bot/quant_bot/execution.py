from _canonical_source import activate_canonical_source

activate_canonical_source()

from hakimi_research.execution import (
    EXECUTION_SIMULATOR_SCHEMA_VERSION,
    ResearchExecutionSimulator,
)

__all__ = ["EXECUTION_SIMULATOR_SCHEMA_VERSION", "ResearchExecutionSimulator"]
