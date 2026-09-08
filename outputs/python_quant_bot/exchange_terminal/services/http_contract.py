from __future__ import annotations

from _canonical_source import activate_canonical_source

activate_canonical_source()

from hakimi_research.http_contract import (
    ARCHIVED_PAPER_READ_ONLY_PATHS,
    LOCAL_CLIENT_HOSTS,
    LOCAL_LOOPBACK_HOSTS,
    MUTATION_PATHS,
    POST_API_PATHS,
    READABLE_MUTATION_PATHS,
    RETIRED_MANAGEMENT_PATHS,
    allowed_web_origin,
    archived_execution_route_state,
    payload_to_query,
    read_only_get_mutation_requested,
    trusted_refresh_get_allowed,
)

__all__ = (
    "ARCHIVED_PAPER_READ_ONLY_PATHS",
    "LOCAL_CLIENT_HOSTS",
    "LOCAL_LOOPBACK_HOSTS",
    "MUTATION_PATHS",
    "POST_API_PATHS",
    "READABLE_MUTATION_PATHS",
    "RETIRED_MANAGEMENT_PATHS",
    "allowed_web_origin",
    "archived_execution_route_state",
    "payload_to_query",
    "read_only_get_mutation_requested",
    "trusted_refresh_get_allowed",
)
