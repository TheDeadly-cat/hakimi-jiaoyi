from __future__ import annotations

import math
import re
from typing import Any

from hakimi_research.experiment_manifest import canonical_payload_hash
from hakimi_research.experiment_provenance_consumer_adapter_v1 import (
    build_frozen_run_provenance_candidate,
    build_multiple_testing_observation_provenance_candidate,
    verify_frozen_run_provenance_candidate,
    verify_multiple_testing_observation_provenance_candidate,
)


FROZEN_EXPERIMENT_PROVENANCE_LEDGER_VERSION = (
    "frozen-experiment-provenance-ledger-v1"
)
FROZEN_EXPERIMENT_PROVENANCE_TRUST_MODEL = (
    "SELF_CONTAINED_REQUIRES_EXTERNAL_ARTIFACT_HASH"
)
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_UNCLASSIFIED_RUN_KINDS = frozenset({
    "FIXED_PARAMETER_WALK_FORWARD",
    "PARAMETER_STABILITY_OBSERVATION",
})
_ENTRY_FIELDS = frozenset({
    "consumer_record_hash",
    "expected_reproducibility",
    "frozen_receipt",
    "multiple_testing_receipt",
})
_LEDGER_FIELDS = frozenset({
    "schema_version",
    "trust_model",
    "external_artifact_hash_required",
    "entry_count",
    "entries",
    "status",
    "classification",
    "ranking_allowed",
    "paper_authorized",
    "live_order_allowed",
    "order_entry_allowed",
    "result_is_profitability_proof",
    "ledger_hash",
})


def _is_exact_native_json(value: Any) -> bool:
    if value is None or type(value) in {bool, int, str}:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is list:
        return all(_is_exact_native_json(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str and _is_exact_native_json(item)
            for key, item in value.items()
        )
    return False


def _document(value: Any, label: str) -> dict[str, Any]:
    if type(value) is not dict or not _is_exact_native_json(value):
        raise ValueError(f"frozen_provenance_{label}_exact_native_required")
    return value


def _manifest_identity(
    record: dict[str, Any],
    expected_reproducibility: dict[str, Any],
    *,
    protocol_hash: str,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    result_hash = canonical_payload_hash(record["result"])
    identity_hash = canonical_payload_hash({
        "source_run_hash": expected_reproducibility["run_hash"],
        "result_hash": result_hash,
    })
    evaluation_role = (
        "UNCLASSIFIED"
        if record["run_kind"] in _UNCLASSIFIED_RUN_KINDS
        else record["role"]
    )
    return {
        "experiment_id": f"hexp-{identity_hash[:20]}",
        "strategy_name": record["strategy_name"],
        "strategy_version": record["strategy_version"],
        "symbol": symbol,
        "timeframe": timeframe,
        "fee_rate": record["fee_rate"],
        "slippage_pct": record["slippage_pct"],
        "evaluation_role": evaluation_role,
        "evaluation_protocol_hash": protocol_hash,
        "evaluation_protocol_verified": True,
    }


def build_frozen_experiment_provenance_ledger(
    records: list[dict[str, Any]],
    expected_reproducibility_by_record_hash: dict[str, dict[str, Any]],
    *,
    expected_context: dict[str, Any],
    protocol_hash: str,
    symbol: str,
    timeframe: str,
) -> dict[str, Any]:
    if type(records) is not list or not _is_exact_native_json(records):
        raise ValueError("frozen_provenance_records_exact_native_required")
    expectations = _document(
        expected_reproducibility_by_record_hash,
        "expectations",
    )
    context = _document(expected_context, "context")
    for label, value in (
        ("protocol_hash", protocol_hash),
        ("symbol", symbol),
        ("timeframe", timeframe),
    ):
        if type(value) is not str or not value:
            raise ValueError(f"frozen_provenance_{label}_invalid")
    if _SHA256_RE.fullmatch(protocol_hash) is None:
        raise ValueError("frozen_provenance_protocol_hash_invalid")

    entries: list[dict[str, Any]] = []
    observed_hashes: set[str] = set()
    for record_value in records:
        record = _document(record_value, "record")
        record_hash = canonical_payload_hash(record)
        if record_hash in observed_hashes:
            raise ValueError("frozen_provenance_record_hash_duplicate")
        observed_hashes.add(record_hash)
        reproducibility = _document(
            expectations.get(record_hash),
            "expected_reproducibility",
        )
        record_identity = {
            key: value
            for key, value in record.items()
            if key not in {"result", "experiment_manifest"}
        }
        manifest_identity = _manifest_identity(
            record,
            reproducibility,
            protocol_hash=protocol_hash,
            symbol=symbol,
            timeframe=timeframe,
        )
        common = {
            "expected_reproducibility": reproducibility,
            "expected_context": context,
            "expected_manifest_identity": manifest_identity,
        }
        frozen_receipt = build_frozen_run_provenance_candidate(
            record,
            **common,
            expected_record_identity=record_identity,
        )
        if not verify_frozen_run_provenance_candidate(
            frozen_receipt,
            record,
            **common,
            expected_record_identity=record_identity,
        ):
            raise ValueError("frozen_provenance_frozen_receipt_invalid")

        multiple_testing_receipt = None
        if record["run_kind"] == "PARAMETER_STABILITY_OBSERVATION":
            multiple_testing_receipt = (
                build_multiple_testing_observation_provenance_candidate(
                    record,
                    **common,
                    expected_observation_identity=record_identity,
                )
            )
            if not verify_multiple_testing_observation_provenance_candidate(
                multiple_testing_receipt,
                record,
                **common,
                expected_observation_identity=record_identity,
            ):
                raise ValueError(
                    "frozen_provenance_multiple_testing_receipt_invalid"
                )
        entries.append({
            "consumer_record_hash": record_hash,
            "expected_reproducibility": reproducibility,
            "frozen_receipt": frozen_receipt,
            "multiple_testing_receipt": multiple_testing_receipt,
        })

    if observed_hashes != set(expectations):
        raise ValueError("frozen_provenance_expectation_matrix_invalid")
    entries.sort(key=lambda item: item["consumer_record_hash"])
    core = {
        "schema_version": FROZEN_EXPERIMENT_PROVENANCE_LEDGER_VERSION,
        "trust_model": FROZEN_EXPERIMENT_PROVENANCE_TRUST_MODEL,
        "external_artifact_hash_required": True,
        "entry_count": len(entries),
        "entries": entries,
        "status": "PASS",
        "classification": "CONSISTENT_REQUIRES_EXTERNAL_ARTIFACT_HASH",
        "ranking_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
        "order_entry_allowed": False,
        "result_is_profitability_proof": False,
    }
    return {**core, "ledger_hash": canonical_payload_hash(core)}


def verify_frozen_experiment_provenance_ledger(
    ledger: Any,
    records: Any,
    *,
    expected_context: Any,
    protocol_hash: Any,
    symbol: Any,
    timeframe: Any,
) -> bool:
    if (
        type(ledger) is not dict
        or not _is_exact_native_json(ledger)
        or set(ledger) != _LEDGER_FIELDS
        or type(ledger.get("entries")) is not list
        or any(
            type(entry) is not dict or set(entry) != _ENTRY_FIELDS
            for entry in ledger["entries"]
        )
    ):
        return False
    try:
        expectations = {
            entry["consumer_record_hash"]: entry["expected_reproducibility"]
            for entry in ledger["entries"]
        }
        if len(expectations) != len(ledger["entries"]):
            return False
        expected = build_frozen_experiment_provenance_ledger(
            records,
            expectations,
            expected_context=expected_context,
            protocol_hash=protocol_hash,
            symbol=symbol,
            timeframe=timeframe,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return ledger == expected


def verified_multiple_testing_receipt_hashes(
    ledger: Any,
    records: Any,
    *,
    expected_context: Any,
    protocol_hash: Any,
    symbol: Any,
    timeframe: Any,
) -> dict[str, str]:
    if not verify_frozen_experiment_provenance_ledger(
        ledger,
        records,
        expected_context=expected_context,
        protocol_hash=protocol_hash,
        symbol=symbol,
        timeframe=timeframe,
    ):
        raise ValueError("frozen_provenance_ledger_verification_failed")
    return {
        entry["consumer_record_hash"]: entry["multiple_testing_receipt"][
            "receipt_hash"
        ]
        for entry in ledger["entries"]
        if entry["multiple_testing_receipt"] is not None
    }


__all__ = [
    "FROZEN_EXPERIMENT_PROVENANCE_LEDGER_VERSION",
    "FROZEN_EXPERIMENT_PROVENANCE_TRUST_MODEL",
    "build_frozen_experiment_provenance_ledger",
    "verified_multiple_testing_receipt_hashes",
    "verify_frozen_experiment_provenance_ledger",
]
