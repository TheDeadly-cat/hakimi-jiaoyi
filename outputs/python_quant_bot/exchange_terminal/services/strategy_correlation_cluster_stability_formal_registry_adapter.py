from __future__ import annotations

import copy
import re
from datetime import date, datetime
from typing import Any

try:
    from .strategy_correlation_cluster_stability_registry import (
        verify_strategy_correlation_cluster_stability_registry_asset,
        verify_strategy_correlation_cluster_stability_registry_binding,
    )
    from .strict_canonical_json_hash import (
        seal_strict_canonical_document,
        strict_canonical_hash,
        strict_json_contract_equal,
    )
    from .strict_research_authority import strict_research_authority_invalid
except ImportError:  # pragma: no cover - project-root service import compatibility
    from services.strategy_correlation_cluster_stability_registry import (
        verify_strategy_correlation_cluster_stability_registry_asset,
        verify_strategy_correlation_cluster_stability_registry_binding,
    )
    from services.strict_canonical_json_hash import (
        seal_strict_canonical_document,
        strict_canonical_hash,
        strict_json_contract_equal,
    )
    from services.strict_research_authority import strict_research_authority_invalid


READ_RECORD_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-registry-read-record-v1"
)
READ_RECORD_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-registry-read-record-verification-v1"
)
READ_ASSESSMENT_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-registry-read-assessment-v1"
)
READ_ASSESSMENT_VERIFICATION_SCHEMA_VERSION = (
    "strategy-correlation-cluster-stability-formal-registry-read-assessment-verification-v1"
)

STATUS_CANDIDATE_RECORD_VERIFIED = "CANDIDATE_RECORD_VERIFIED"
STATUS_MISSING = "MISSING"
STATUS_DUPLICATE = "DUPLICATE"
STATUS_DRIFT = "DRIFT"
STATUS_UNKNOWN = "UNKNOWN"

_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_LOCK_FIELDS = (
    "formal_registry_bound",
    "formal_registry_activation_allowed",
    "writer_implemented",
    "current_writer_activation_allowed",
    "current_admission_allowed",
)


def _native_true(value: Any) -> bool:
    return type(value) is bool and value is True


def _native_false(value: Any) -> bool:
    return type(value) is bool and value is False


def _nonempty_string(value: Any) -> bool:
    return type(value) is str and bool(value.strip())


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_PATTERN.fullmatch(value) is not None


def _is_date(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        return date.fromisoformat(value).isoformat() == value
    except ValueError:
        return False


def _is_utc_timestamp(value: Any) -> bool:
    if type(value) is not str:
        return False
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ) == value
    except ValueError:
        return False


def _before_evidence_date(value: Any, evidence_cutoff_date: Any) -> bool:
    return (
        _is_date(value)
        and _is_date(evidence_cutoff_date)
        and value < evidence_cutoff_date
    )


def _timestamp_before_evidence(value: Any, evidence_cutoff_date: Any) -> bool:
    return (
        _is_utc_timestamp(value)
        and _is_date(evidence_cutoff_date)
        and value[:10] < evidence_cutoff_date
    )


def _locked_document(value: Any) -> bool:
    return isinstance(value, dict) and all(
        _native_false(value.get(field)) for field in _LOCK_FIELDS
    )


def _permissions() -> dict[str, bool]:
    return {
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class InMemoryFormalRegistryReadAdapter:
    """Immutable copy-on-read adapter for isolated formal-registry contract tests."""

    __slots__ = ("_records", "_snapshot_hash")

    def __init__(self, records: Any) -> None:
        if type(records) not in (list, tuple):
            raise TypeError("records must be a list or tuple")
        frozen_records = copy.deepcopy(list(records))
        snapshot_hash = strict_canonical_hash(frozen_records)
        self._records = tuple(frozen_records)
        self._snapshot_hash = snapshot_hash

    @property
    def read_only(self) -> bool:
        return True

    @property
    def snapshot_hash(self) -> str:
        return self._snapshot_hash

    @property
    def record_count(self) -> int:
        return len(self._records)

    def lookup(self, registry_id: Any) -> tuple[Any, ...]:
        if not _nonempty_string(registry_id):
            return ()
        return tuple(
            copy.deepcopy(record)
            for record in self._records
            if isinstance(record, dict)
            and type(record.get("registry_id")) is str
            and record.get("registry_id") == registry_id
        )


def build_strategy_correlation_cluster_stability_formal_registry_read_record(
    protocol_registration: Any,
    registry_asset: Any,
    binding_assessment: Any,
    *,
    registry_id: Any,
    formal_registry_source: Any,
    formal_registry_source_version: Any,
    formal_registry_source_hash: Any,
    registry_snapshot_hash: Any,
    effective_date: Any,
    frozen_at: Any,
) -> dict[str, Any]:
    asset = registry_asset if isinstance(registry_asset, dict) else {}
    binding = binding_assessment if isinstance(binding_assessment, dict) else {}
    protocol = protocol_registration if isinstance(protocol_registration, dict) else {}
    document = {
        "schema_version": READ_RECORD_SCHEMA_VERSION,
        "registry_id": registry_id,
        "formal_registry_source": formal_registry_source,
        "formal_registry_source_version": formal_registry_source_version,
        "formal_registry_source_hash": formal_registry_source_hash,
        "registry_snapshot_hash": registry_snapshot_hash,
        "effective_date": effective_date,
        "frozen_at": frozen_at,
        "protocol_registration_schema_version": protocol.get("schema_version"),
        "protocol_registration_hash": asset.get("protocol_registration_hash"),
        "candidate_registry_asset_schema_version": asset.get("schema_version"),
        "candidate_registry_asset_hash": asset.get("registry_asset_hash"),
        "candidate_registry_source_hash": asset.get("registry_source_hash"),
        "candidate_binding_schema_version": binding.get("schema_version"),
        "candidate_binding_assessment_hash": binding.get("assessment_hash"),
        "cluster_stability_policy_hash": asset.get(
            "cluster_stability_policy_hash"
        ),
        "evidence_cutoff_date": binding.get("evidence_cutoff_date"),
        "target_protocol_schema_version": asset.get(
            "target_protocol_schema_version"
        ),
        "target_report_schema_version": asset.get("target_report_schema_version"),
        "status": "FROZEN_READ_RECORD",
        "adapter_scope": "ISOLATED_IN_MEMORY_READ_ONLY",
        "adapter_read_only": True,
        "candidate_only": True,
        "formal_persistence_verified": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
        "methodology": {
            "lookup_policy": "EXACT_REGISTRY_ID_EXACTLY_ONE",
            "snapshot_policy": "CALLER_BOUND_SOURCE_AND_ADAPTER_HASHES",
            "mutation_policy": "COPY_ON_CONSTRUCT_AND_READ",
            "persistence_claim": "NOT_ESTABLISHED",
        },
    }
    return seal_strict_canonical_document(document, "record_hash")


def verify_strategy_correlation_cluster_stability_formal_registry_read_record(
    document: Any,
    *,
    protocol_registration: Any,
    registry_asset: Any,
    binding_assessment: Any,
    evidence_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_cluster_stability_policy_hash: Any,
    registry_id: Any,
    formal_registry_source: Any,
    formal_registry_source_version: Any,
    formal_registry_source_hash: Any,
    registry_snapshot_hash: Any,
    effective_date: Any,
    frozen_at: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    record = document if isinstance(document, dict) else {}

    if not isinstance(document, dict):
        blockers.append("RECORD_NOT_OBJECT")
    if not _nonempty_string(registry_id):
        blockers.append("REGISTRY_ID_INVALID")
    if not _nonempty_string(formal_registry_source):
        blockers.append("FORMAL_REGISTRY_SOURCE_INVALID")
    if not _nonempty_string(formal_registry_source_version):
        blockers.append("FORMAL_REGISTRY_SOURCE_VERSION_INVALID")
    if not _is_sha256(formal_registry_source_hash):
        blockers.append("FORMAL_REGISTRY_SOURCE_HASH_INVALID")
    if not _is_sha256(registry_snapshot_hash):
        blockers.append("REGISTRY_SNAPSHOT_HASH_INVALID")
    if not _before_evidence_date(effective_date, evidence_cutoff_date):
        blockers.append("EFFECTIVE_DATE_NOT_BEFORE_EVIDENCE")
    if not _timestamp_before_evidence(frozen_at, evidence_cutoff_date):
        blockers.append("FROZEN_AT_NOT_BEFORE_EVIDENCE")
    if not isinstance(protocol_registration, dict):
        blockers.append("PROTOCOL_REGISTRATION_INVALID")
    if not isinstance(registry_asset, dict):
        blockers.append("CANDIDATE_REGISTRY_ASSET_INVALID")
    if not isinstance(binding_assessment, dict):
        blockers.append("CANDIDATE_BINDING_INVALID")
    if not all(
        _is_sha256(value)
        for value in (
            expected_registry_asset_hash,
            expected_registry_source_hash,
            expected_protocol_registration_hash,
            expected_cluster_stability_policy_hash,
        )
    ):
        blockers.append("EXPECTED_CANDIDATE_HASH_INVALID")

    try:
        expected = (
            build_strategy_correlation_cluster_stability_formal_registry_read_record(
                protocol_registration,
                registry_asset,
                binding_assessment,
                registry_id=registry_id,
                formal_registry_source=formal_registry_source,
                formal_registry_source_version=formal_registry_source_version,
                formal_registry_source_hash=formal_registry_source_hash,
                registry_snapshot_hash=registry_snapshot_hash,
                effective_date=effective_date,
                frozen_at=frozen_at,
            )
        )
        if not strict_json_contract_equal(record, expected):
            blockers.append("READ_RECORD_REBUILD_MISMATCH")
    except Exception:
        blockers.append("READ_RECORD_REBUILD_FAILED")

    documents = (protocol_registration, registry_asset, binding_assessment, record)
    if any(strict_research_authority_invalid(item) for item in documents):
        blockers.append("RESEARCH_AUTHORITY_INVALID")
    if not _locked_document(record):
        blockers.append("READ_RECORD_AUTHORITY_NOT_LOCKED")
    if not _native_true(record.get("adapter_read_only")):
        blockers.append("READ_RECORD_NOT_READ_ONLY")
    if not _native_true(record.get("candidate_only")):
        blockers.append("READ_RECORD_NOT_CANDIDATE_ONLY")
    if not _native_false(record.get("formal_persistence_verified")):
        blockers.append("FORMAL_PERSISTENCE_ALIAS")
    if record.get("status") != "FROZEN_READ_RECORD":
        blockers.append("READ_RECORD_STATUS_INVALID")
    if isinstance(registry_asset, dict) and registry_asset.get("registry_id") != registry_id:
        blockers.append("CANDIDATE_ASSET_REGISTRY_ID_MISMATCH")
    if (
        isinstance(binding_assessment, dict)
        and binding_assessment.get("registry_id") != registry_id
    ):
        blockers.append("CANDIDATE_BINDING_REGISTRY_ID_MISMATCH")

    try:
        asset_verification = (
            verify_strategy_correlation_cluster_stability_registry_asset(
                registry_asset,
                protocol_registration=protocol_registration,
            )
        )
        binding_verification = (
            verify_strategy_correlation_cluster_stability_registry_binding(
                binding_assessment,
                registry_asset=registry_asset,
                protocol_registration=protocol_registration,
                evidence_cutoff_date=evidence_cutoff_date,
                expected_registry_asset_hash=expected_registry_asset_hash,
                expected_registry_source_hash=expected_registry_source_hash,
                expected_protocol_registration_hash=expected_protocol_registration_hash,
                expected_cluster_stability_policy_hash=(
                    expected_cluster_stability_policy_hash
                ),
            )
        )
        if asset_verification.get("status") != "PASS":
            blockers.append("CANDIDATE_ASSET_VERIFICATION_FAILED")
        if binding_verification.get("status") != "PASS":
            blockers.append("CANDIDATE_BINDING_VERIFICATION_FAILED")
        if binding_assessment.get("status") != "CANDIDATE_BOUND":
            blockers.append("CANDIDATE_BINDING_NOT_BOUND")
        if not _native_true(binding_assessment.get("candidate_bound")):
            blockers.append("CANDIDATE_BINDING_FLAG_INVALID")
        if not _native_true(binding_verification.get("candidate_bound")):
            blockers.append("CANDIDATE_BINDING_VERIFICATION_FLAG_INVALID")
    except Exception:
        blockers.append("CANDIDATE_VERIFICATION_FAILED")

    unique_blockers = list(dict.fromkeys(blockers))
    passed = not unique_blockers
    return {
        "schema_version": READ_RECORD_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "blockers": unique_blockers,
        "record_verified": passed,
        "candidate_record_verified": passed,
        "adapter_read_only": True,
        "formal_persistence_verified": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }


def assess_strategy_correlation_cluster_stability_formal_registry_read(
    adapter: Any,
    *,
    expected_adapter_snapshot_hash: Any,
    protocol_registration: Any,
    registry_asset: Any,
    binding_assessment: Any,
    evidence_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_cluster_stability_policy_hash: Any,
    registry_id: Any,
    formal_registry_source: Any,
    formal_registry_source_version: Any,
    formal_registry_source_hash: Any,
    registry_snapshot_hash: Any,
    effective_date: Any,
    frozen_at: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    adapter_valid = type(adapter) is InMemoryFormalRegistryReadAdapter
    actual_adapter_snapshot_hash = adapter.snapshot_hash if adapter_valid else None
    adapter_snapshot_bound = (
        adapter_valid
        and _is_sha256(expected_adapter_snapshot_hash)
        and actual_adapter_snapshot_hash == expected_adapter_snapshot_hash
    )
    read_performed = False
    lookup_cardinality: int | None = None
    observed_record_hash: Any = None
    record_verification_status = "NOT_RUN"
    record_verified = False

    if not adapter_valid:
        status = STATUS_UNKNOWN
        blockers.append("ADAPTER_TYPE_INVALID")
    elif not _nonempty_string(registry_id):
        status = STATUS_UNKNOWN
        blockers.append("REGISTRY_ID_INVALID")
    elif not adapter_snapshot_bound:
        status = STATUS_DRIFT
        blockers.append("ADAPTER_SNAPSHOT_MISMATCH")
    else:
        records = adapter.lookup(registry_id)
        read_performed = True
        lookup_cardinality = len(records)
        if lookup_cardinality == 0:
            status = STATUS_MISSING
            blockers.append("READ_RECORD_MISSING")
        elif lookup_cardinality > 1:
            status = STATUS_DUPLICATE
            blockers.append("READ_RECORD_DUPLICATE")
        else:
            record = records[0]
            if isinstance(record, dict):
                observed_record_hash = record.get("record_hash")
            verification = (
                verify_strategy_correlation_cluster_stability_formal_registry_read_record(
                    record,
                    protocol_registration=protocol_registration,
                    registry_asset=registry_asset,
                    binding_assessment=binding_assessment,
                    evidence_cutoff_date=evidence_cutoff_date,
                    expected_registry_asset_hash=expected_registry_asset_hash,
                    expected_registry_source_hash=expected_registry_source_hash,
                    expected_protocol_registration_hash=(
                        expected_protocol_registration_hash
                    ),
                    expected_cluster_stability_policy_hash=(
                        expected_cluster_stability_policy_hash
                    ),
                    registry_id=registry_id,
                    formal_registry_source=formal_registry_source,
                    formal_registry_source_version=formal_registry_source_version,
                    formal_registry_source_hash=formal_registry_source_hash,
                    registry_snapshot_hash=registry_snapshot_hash,
                    effective_date=effective_date,
                    frozen_at=frozen_at,
                )
            )
            record_verification_status = verification.get("status", "BLOCK")
            record_verified = verification.get("record_verified") is True
            if record_verification_status == "PASS" and record_verified:
                status = STATUS_CANDIDATE_RECORD_VERIFIED
            else:
                status = STATUS_DRIFT
                blockers.append("READ_RECORD_VERIFICATION_FAILED")

    document = {
        "schema_version": READ_ASSESSMENT_SCHEMA_VERSION,
        "status": status,
        "blockers": blockers,
        "registry_id": registry_id if _nonempty_string(registry_id) else None,
        "expected_adapter_snapshot_hash": expected_adapter_snapshot_hash,
        "actual_adapter_snapshot_hash": actual_adapter_snapshot_hash,
        "adapter_snapshot_bound": adapter_snapshot_bound,
        "adapter_read_only": adapter_valid,
        "read_performed": read_performed,
        "lookup_cardinality": lookup_cardinality,
        "observed_record_hash": observed_record_hash,
        "record_verification_status": record_verification_status,
        "record_verified": record_verified,
        "candidate_record_verified": (
            status == STATUS_CANDIDATE_RECORD_VERIFIED and record_verified
        ),
        "candidate_only": True,
        "formal_persistence_verified": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
        "methodology": {
            "adapter": "IN_MEMORY_COPY_ON_READ_V1",
            "lookup_policy": "EXACT_REGISTRY_ID_EXACTLY_ONE",
            "formal_persistence_claim": "NOT_ESTABLISHED",
        },
    }
    return seal_strict_canonical_document(document, "assessment_hash")


def verify_strategy_correlation_cluster_stability_formal_registry_read_assessment(
    document: Any,
    *,
    adapter: Any,
    expected_adapter_snapshot_hash: Any,
    protocol_registration: Any,
    registry_asset: Any,
    binding_assessment: Any,
    evidence_cutoff_date: Any,
    expected_registry_asset_hash: Any,
    expected_registry_source_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_cluster_stability_policy_hash: Any,
    registry_id: Any,
    formal_registry_source: Any,
    formal_registry_source_version: Any,
    formal_registry_source_hash: Any,
    registry_snapshot_hash: Any,
    effective_date: Any,
    frozen_at: Any,
) -> dict[str, Any]:
    blockers: list[str] = []
    assessment = document if isinstance(document, dict) else {}
    if not isinstance(document, dict):
        blockers.append("ASSESSMENT_NOT_OBJECT")
    try:
        expected = assess_strategy_correlation_cluster_stability_formal_registry_read(
            adapter,
            expected_adapter_snapshot_hash=expected_adapter_snapshot_hash,
            protocol_registration=protocol_registration,
            registry_asset=registry_asset,
            binding_assessment=binding_assessment,
            evidence_cutoff_date=evidence_cutoff_date,
            expected_registry_asset_hash=expected_registry_asset_hash,
            expected_registry_source_hash=expected_registry_source_hash,
            expected_protocol_registration_hash=expected_protocol_registration_hash,
            expected_cluster_stability_policy_hash=(
                expected_cluster_stability_policy_hash
            ),
            registry_id=registry_id,
            formal_registry_source=formal_registry_source,
            formal_registry_source_version=formal_registry_source_version,
            formal_registry_source_hash=formal_registry_source_hash,
            registry_snapshot_hash=registry_snapshot_hash,
            effective_date=effective_date,
            frozen_at=frozen_at,
        )
        if not strict_json_contract_equal(assessment, expected):
            blockers.append("ASSESSMENT_REBUILD_MISMATCH")
    except Exception:
        expected = {}
        blockers.append("ASSESSMENT_REBUILD_FAILED")
    if strict_research_authority_invalid(assessment):
        blockers.append("RESEARCH_AUTHORITY_INVALID")
    if not _locked_document(assessment):
        blockers.append("ASSESSMENT_AUTHORITY_NOT_LOCKED")
    if not _native_false(assessment.get("formal_persistence_verified")):
        blockers.append("FORMAL_PERSISTENCE_ALIAS")

    unique_blockers = list(dict.fromkeys(blockers))
    passed = not unique_blockers
    return {
        "schema_version": READ_ASSESSMENT_VERIFICATION_SCHEMA_VERSION,
        "status": "PASS" if passed else "BLOCK",
        "blockers": unique_blockers,
        "assessment_verified": passed,
        "decision_status": expected.get("status", STATUS_UNKNOWN),
        "candidate_record_verified": (
            passed and expected.get("candidate_record_verified") is True
        ),
        "formal_persistence_verified": False,
        "formal_registry_bound": False,
        "formal_registry_activation_allowed": False,
        "writer_implemented": False,
        "current_writer_activation_allowed": False,
        "current_admission_allowed": False,
        "permissions": _permissions(),
    }


__all__ = [
    "READ_RECORD_SCHEMA_VERSION",
    "READ_RECORD_VERIFICATION_SCHEMA_VERSION",
    "READ_ASSESSMENT_SCHEMA_VERSION",
    "READ_ASSESSMENT_VERIFICATION_SCHEMA_VERSION",
    "STATUS_CANDIDATE_RECORD_VERIFIED",
    "STATUS_MISSING",
    "STATUS_DUPLICATE",
    "STATUS_DRIFT",
    "STATUS_UNKNOWN",
    "InMemoryFormalRegistryReadAdapter",
    "build_strategy_correlation_cluster_stability_formal_registry_read_record",
    "verify_strategy_correlation_cluster_stability_formal_registry_read_record",
    "assess_strategy_correlation_cluster_stability_formal_registry_read",
    "verify_strategy_correlation_cluster_stability_formal_registry_read_assessment",
]
