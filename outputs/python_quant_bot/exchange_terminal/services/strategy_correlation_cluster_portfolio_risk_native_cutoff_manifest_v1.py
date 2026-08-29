from __future__ import annotations

from datetime import datetime
from typing import Any

from .strict_governance_primitives import strict_sha256

from .strategy_correlation_cluster_temporal_date_grid import DATE_GRID_RULE
from .strategy_correlation_common_support_calendar_provider_composition_v1 import (
    SCHEMA_VERSION as CALENDAR_PROVIDER_COMPOSITION_SCHEMA_VERSION,
    verify_correlation_common_support_calendar_provider_composition_v1,
)
from .strategy_correlation_common_support_derivation_receipt_v1 import (
    RECEIPT_SCHEMA_VERSION as DERIVATION_RECEIPT_SCHEMA_VERSION,
    verify_correlation_common_support_derivation_receipt_v1,
)
from .strategy_correlation_cross_lag_factor_calibration_long_horizon_calendar_session_verifier_v1 import (
    SCHEMA_VERSION as CALENDAR_SESSION_SCHEMA_VERSION,
)
from .strategy_correlation_return_replay import (
    COMPLETED_PRICE_INPUT_SCHEMA_VERSION,
    CORRELATION_MATRIX_REPLAY_SCHEMA_VERSION,
    REQUIRED_PRICE_ROWS,
    verify_correlation_completed_price_input,
    verify_correlation_matrix_replay,
)
from .strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


MANIFEST_SCHEMA_VERSION = (
    "strategy-correlation-cluster-portfolio-risk-native-cutoff-manifest-v1"
)
MANIFEST_VERIFICATION_SCHEMA_VERSION = f"{MANIFEST_SCHEMA_VERSION}-verification-v1"
STATIC_FINGERPRINT = "20260822-native-cutoff-session-label-lock-1"
CUTOFF_UTC_SEMANTICS = (
    "SESSION_LABEL_DATE_AT_UTC_MIDNIGHT_NOT_SESSION_CLOSE_INGESTION_OR_FRESHNESS"
)

_COMPOSITION_CONTEXT_KEYS = {
    "calendar_session_verification",
    "calendar_verification_bundle",
    "derivation_receipt",
    "matrix_replay",
    "provider_identity_verification",
    "provider_verification_bundle",
}


def _dict(value: Any) -> dict[str, Any]:
    return value if type(value) is dict else {}


def _list(value: Any) -> list[Any]:
    return value if type(value) is list else []


def _text_or_none(value: Any) -> str | None:
    return value if type(value) is str else None


def _strict_midnight_cutoff(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT00:00:00Z")
    except ValueError:
        return False
    return parsed.strftime("%Y-%m-%dT00:00:00Z") == value


def _check(name: str, ok: bool, pass_message: str, block_message: str) -> dict[str, Any]:
    return {
        "name": name,
        "ok": ok,
        "blocking": True,
        "message": pass_message if ok else block_message,
    }


def _research_authority() -> dict[str, bool]:
    return {
        "current_admission_allowed": False,
        "current_pointer_written": False,
        "descriptive_only": True,
        "formal_registry_activation_allowed": False,
        "live_order_allowed": False,
        "migration_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
        "writer_allowed": False,
    }


def _verify_composition(
    composition_document: Any,
    composition_context: Any,
) -> bool:
    if (
        type(composition_document) is not dict
        or composition_document.get("schema_version")
        != CALENDAR_PROVIDER_COMPOSITION_SCHEMA_VERSION
        or type(composition_context) is not dict
        or set(composition_context) != _COMPOSITION_CONTEXT_KEYS
    ):
        return False
    try:
        verification = (
            verify_correlation_common_support_calendar_provider_composition_v1(
                composition_document,
                composition_context["derivation_receipt"],
                composition_context["matrix_replay"],
                composition_context["calendar_session_verification"],
                composition_context["calendar_verification_bundle"],
                composition_context["provider_identity_verification"],
                composition_context["provider_verification_bundle"],
            )
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        return False
    return bool(
        type(verification) is dict
        and verification.get("status") == "PASS"
        and not _list(verification.get("blockers"))
    )


def _derive_native_date_evidence(
    completed_price_input: Any,
) -> tuple[bool, list[dict[str, Any]], list[str]]:
    datasets = _list(_dict(completed_price_input).get("datasets"))
    if len(datasets) < 2:
        return False, [], []
    evidence: list[dict[str, Any]] = []
    grids: list[list[str]] = []
    symbols: list[str] = []
    for dataset in datasets:
        if type(dataset) is not dict:
            return False, [], []
        symbol = dataset.get("symbol")
        rows = dataset.get("price_rows")
        if (
            type(symbol) is not str
            or symbol != symbol.strip().upper()
            or not symbol
            or type(rows) is not list
            or len(rows) != REQUIRED_PRICE_ROWS
            or symbol in symbols
        ):
            return False, [], []
        dates: list[str] = []
        for row in rows:
            if (
                type(row) is not dict
                or type(row.get("date")) is not str
                or row.get("complete") is not True
            ):
                return False, [], []
            dates.append(row["date"])
        if dates != sorted(dates) or len(set(dates)) != len(dates):
            return False, [], []
        if (
            dataset.get("price_row_count") != REQUIRED_PRICE_ROWS
            or type(dataset.get("manifest_row_count")) is not int
            or dataset.get("manifest_row_count") < REQUIRED_PRICE_ROWS
            or dataset.get("first_date") != dates[0]
            or dataset.get("last_date") != dates[-1]
            or type(dataset.get("dataset_data_hash")) is not str
            or type(dataset.get("dataset_manifest_hash")) is not str
        ):
            return False, [], []
        symbols.append(symbol)
        grids.append(dates)
        evidence.append(
            {
                "symbol": symbol,
                "dataset_data_hash": dataset["dataset_data_hash"],
                "dataset_manifest_hash": dataset["dataset_manifest_hash"],
                "price_row_count": REQUIRED_PRICE_ROWS,
                "first_session_label": dates[0],
                "last_session_label": dates[-1],
                "date_grid_hash": strict_canonical_hash(dates),
            }
        )
    exact_grid = bool(
        symbols == sorted(symbols)
        and all(grid == grids[0] for grid in grids[1:])
    )
    return exact_grid, evidence, grids[0] if exact_grid else []


def build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
    completed_price_input: Any,
    matrix_replay: Any,
    derivation_receipt: Any,
    composition_document: Any,
    composition_context: Any,
    *,
    expected_observation_cutoff_utc: Any,
) -> dict[str, Any]:
    replay_document = _dict(matrix_replay)
    preregistration = _dict(replay_document.get("preregistration"))
    completed_verification: dict[str, Any] = {}
    try:
        candidate = verify_correlation_completed_price_input(
            completed_price_input,
            preregistration=preregistration,
        )
        if type(candidate) is dict:
            completed_verification = candidate
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        completed_verification = {}
    completed_ok = bool(
        _dict(completed_price_input).get("schema_version")
        == COMPLETED_PRICE_INPUT_SCHEMA_VERSION
        and completed_verification.get("status") == "PASS"
        and not _list(completed_verification.get("blockers"))
    )

    replay_verification: dict[str, Any] = {}
    try:
        candidate = verify_correlation_matrix_replay(matrix_replay)
        if type(candidate) is dict:
            replay_verification = candidate
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        replay_verification = {}
    replay_ok = bool(
        replay_document.get("schema_version") == CORRELATION_MATRIX_REPLAY_SCHEMA_VERSION
        and replay_document.get("status") == "PASS"
        and replay_verification.get("status") == "PASS"
        and not _list(replay_verification.get("blockers"))
        and strict_json_contract_equal(
            replay_document.get("completed_price_input"),
            completed_price_input,
        )
    )

    derivation_verification: dict[str, Any] = {}
    try:
        candidate = verify_correlation_common_support_derivation_receipt_v1(
            derivation_receipt,
            matrix_replay=matrix_replay,
        )
        if type(candidate) is dict:
            derivation_verification = candidate
    except (AttributeError, IndexError, KeyError, TypeError, ValueError, OverflowError):
        derivation_verification = {}
    derivation_ok = bool(
        _dict(derivation_receipt).get("schema_version")
        == DERIVATION_RECEIPT_SCHEMA_VERSION
        and _dict(derivation_receipt).get("status") == "PASS"
        and derivation_verification.get("status") == "PASS"
        and not _list(derivation_verification.get("blockers"))
    )
    composition = _dict(composition_document)
    composition_ok = _verify_composition(composition_document, composition_context)

    date_grid_ok, dataset_evidence, common_date_grid = (
        _derive_native_date_evidence(completed_price_input)
    )
    completed_document = _dict(completed_price_input)
    derivation_document = _dict(derivation_receipt)
    calendar_verification = _dict(
        _dict(composition_context).get("calendar_session_verification")
    )
    calendar_bundle = _dict(
        _dict(composition_context).get("calendar_verification_bundle")
    )
    calendar_facts = _dict(calendar_verification.get("facts"))
    cutoff_date = completed_document.get("cutoff_date")
    expected_cutoff_ok = _strict_midnight_cutoff(expected_observation_cutoff_utc)
    expected_cutoff_date = (
        expected_observation_cutoff_utc[:10] if expected_cutoff_ok else None
    )
    native_cutoff_ok = bool(
        completed_ok
        and date_grid_ok
        and type(cutoff_date) is str
        and common_date_grid
        and common_date_grid[-1] == cutoff_date
        and all(item["last_session_label"] == cutoff_date for item in dataset_evidence)
    )
    calendar_session_ok = bool(
        composition_ok
        and calendar_verification.get("schema_version") == CALENDAR_SESSION_SCHEMA_VERSION
        and calendar_verification.get("source_state") == "VERIFIED"
        and strict_sha256(
            calendar_verification.get("source_calendar_registration_hash")
        )
        and calendar_verification.get("source_calendar_registration_hash")
        == calendar_bundle.get("expected_calendar_registration_hash")
        == composition.get("source_calendar_registration_hash")
        and calendar_verification.get("last_observation_date") == cutoff_date
        and type(calendar_verification.get("completed_common_session_count")) is int
        and calendar_verification.get("completed_common_session_count")
        >= len(common_date_grid)
        and calendar_facts.get("calendar_sessions_evaluated") is True
        and calendar_facts.get("common_session_intersection_verified") is True
        and calendar_facts.get("all_registered_sessions_completed") is True
    )
    expected_cutoff_aligned = bool(
        expected_cutoff_ok
        and native_cutoff_ok
        and expected_cutoff_date == cutoff_date
        and expected_observation_cutoff_utc == f"{cutoff_date}T00:00:00Z"
    )
    common_index_ok = bool(
        derivation_ok
        and date_grid_ok
        and derivation_document.get("common_price_row_count")
        == len(common_date_grid)
        and derivation_document.get("common_price_index_hash")
        == strict_canonical_hash(common_date_grid)
    )

    checks = [
        _check(
            "completed_price_input_exact",
            completed_ok,
            "Completed-price input verifies against preregistration.",
            "Completed-price input is invalid or unverifiable.",
        ),
        _check(
            "matrix_replay_exact",
            replay_ok,
            "Matrix replay exactly embeds the completed-price input.",
            "Matrix replay is invalid or binds a different input.",
        ),
        _check(
            "common_support_derivation_exact",
            derivation_ok,
            "Common-support derivation exactly matches matrix replay.",
            "Common-support derivation is invalid or mismatched.",
        ),
        _check(
            "calendar_provider_composition_exact",
            composition_ok,
            "Calendar/provider composition exactly matches its context.",
            "Calendar/provider composition is invalid or mismatched.",
        ),
        _check(
            "all_symbol_date_grids_exact",
            date_grid_ok,
            "Every symbol has the same completed 61-session date grid.",
            "Symbol date grids differ or contain invalid sessions.",
        ),
        _check(
            "native_completed_price_cutoff",
            native_cutoff_ok,
            "Completed-price cutoff equals every dataset last session label.",
            "Completed-price cutoff is not native to every dataset.",
        ),
        _check(
            "calendar_session_cutoff",
            calendar_session_ok,
            "Cutoff is the last verified completed common calendar session.",
            "Calendar-session evidence does not verify the cutoff.",
        ),
        _check(
            "common_price_index_cutoff",
            common_index_ok,
            "Derived common price index matches the exact date grid.",
            "Derived common price index differs from the exact date grid.",
        ),
        _check(
            "expected_midnight_cutoff_alignment",
            expected_cutoff_aligned,
            "Expected UTC midnight encodes the verified session-label date.",
            "Expected cutoff is invalid or differs from the session-label date.",
        ),
    ]
    blockers = [item["name"] for item in checks if item["ok"] is not True]
    status = "PASS" if not blockers else "BLOCK"
    document: dict[str, Any] = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "decision": (
            "NATIVE_SESSION_LABEL_CUTOFF_VERIFIED_NOT_FRESHNESS"
            if status == "PASS"
            else "BLOCKED_NATIVE_CUTOFF_MANIFEST"
        ),
        "source": {
            "completed_price_input_hash": (
                _text_or_none(completed_document.get("input_hash"))
                if completed_ok
                else None
            ),
            "matrix_replay_hash": (
                _text_or_none(replay_document.get("replay_hash")) if replay_ok else None
            ),
            "derivation_receipt_hash": (
                _text_or_none(derivation_document.get("receipt_hash"))
                if derivation_ok
                else None
            ),
            "composition_hash": (
                _text_or_none(composition.get("composition_hash"))
                if composition_ok
                else None
            ),
            "calendar_registration_hash": (
                _text_or_none(
                    calendar_verification.get("source_calendar_registration_hash")
                )
                if calendar_session_ok
                else None
            ),
            "calendar_session_verification_hash": (
                _text_or_none(
                    calendar_verification.get("verification_hash")
                )
                if calendar_session_ok
                else None
            ),
        },
        "cutoff": {
            "session_label_date": cutoff_date if native_cutoff_ok else None,
            "observation_cutoff_utc": (
                expected_observation_cutoff_utc
                if expected_cutoff_aligned
                else None
            ),
            "utc_semantics": CUTOFF_UTC_SEMANTICS,
            "common_session_count": (
                len(common_date_grid) if common_index_ok else None
            ),
            "date_grid_hash": (
                strict_canonical_hash(common_date_grid) if date_grid_ok else None
            ),
            "date_grid_rule": DATE_GRID_RULE,
        },
        "datasets": dataset_evidence if native_cutoff_ok else [],
        "checks": checks,
        "blockers": blockers,
        "facts": {
            "cutoff_native_to_completed_price_input": native_cutoff_ok,
            "all_registered_sessions_completed": calendar_session_ok,
            "freshness_policy_defined": False,
            "freshness_evaluated": False,
            "session_close_time_claimed": False,
            "provider_timestamp_claimed": False,
            "ingestion_time_claimed": False,
            "external_provider_identity_authenticated": False,
            "price_rows_embedded": False,
            "runtime_assets_accessed": False,
            "runtime_consumer_bound": False,
        },
        "authority": _research_authority(),
    }
    return seal_strict_canonical_document(document, "manifest_hash")


def verify_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
    document: Any,
    completed_price_input: Any,
    matrix_replay: Any,
    derivation_receipt: Any,
    composition_document: Any,
    composition_context: Any,
    *,
    expected_observation_cutoff_utc: Any,
) -> dict[str, Any]:
    expected = build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1(
        completed_price_input,
        matrix_replay,
        derivation_receipt,
        composition_document,
        composition_context,
        expected_observation_cutoff_utc=expected_observation_cutoff_utc,
    )
    exact = strict_json_contract_equal(document, expected)
    return {
        "schema_version": MANIFEST_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if exact else "BLOCK",
        "blockers": [] if exact else ["native_cutoff_manifest_exact_rebuild_mismatch"],
        "manifest_decision": expected["decision"] if exact else "UNKNOWN",
        "manifest_exactly_verified": exact,
        "current_admission_allowed": False,
        "live_order_allowed": False,
        "paper_authorized": False,
        "runtime_gate_activation_allowed": False,
        "shadow_consumer_activation_allowed": False,
    }


__all__ = [
    "MANIFEST_SCHEMA_VERSION",
    "MANIFEST_VERIFICATION_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "CUTOFF_UTC_SEMANTICS",
    "build_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1",
    "verify_strategy_correlation_cluster_portfolio_risk_native_cutoff_manifest_v1",
]
