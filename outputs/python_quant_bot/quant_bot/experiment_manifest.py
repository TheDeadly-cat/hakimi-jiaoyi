from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.experiment_manifest import (  # noqa: E402
    SCHEMA_VERSION,
    _requirements_fully_pinned,
    build_local_experiment_context,
    build_reproducible_experiment_manifest,
    canonical_payload_hash,
    verify_reproducible_experiment_manifest,
)


__all__ = [
    "SCHEMA_VERSION",
    "build_local_experiment_context",
    "build_reproducible_experiment_manifest",
    "canonical_payload_hash",
    "verify_reproducible_experiment_manifest",
]