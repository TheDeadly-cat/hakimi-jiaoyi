"""Bind ADR0350 windows to exact ADR0121 dataset-key lifecycle gates.

The gate delegates signature, freshness, revocation, rotation, binding, and
custody decisions to ADR0121. It only verifies exact source documents and
cross-binds their key lineage to every ADR0350 window. External governance,
registry durability, replay, and trading authority remain unproven.
"""

from __future__ import annotations

from copy import deepcopy
from hmac import compare_digest
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_provider_dataset_key_lifecycle_gate_v1
    as lifecycle_gate_v1,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1
    as provider_binding_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-binding-preregistration-v1"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-lifecycle-binding-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-uncertainty-multi-window-observation-"
    "membership-provider-attestation-lifecycle-binding-gate-v1-synthetic-"
    "unmounted-lock-1"
)
LIFECYCLE_GATE_V1_IMPLEMENTATION_SHA256 = (
    "c779ef769383935dec7b9a9a81ea896ccf505144e0ce1bec46f39fc840c19369"
)
PROVIDER_BINDING_V1_IMPLEMENTATION_SHA256 = (
    "f4cbb7f53dafb45433c6ecbe9065de4549aaabe1a6523445ddfa4e824e6c7340"
)
ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_ADR0350_PREREGISTRATION",
    "PREREGISTER_ONE_ADR0121_BINDING_PER_ADR0350_WINDOW",
    "REQUIRE_SAME_DATASET_KEY_TO_SHARE_GOVERNANCE_AND_POLICY_LINEAGE",
    "VERIFY_EXACT_ADR0350_GATE",
    "VERIFY_EXACT_ADR0121_GATE_PER_WINDOW",
    "BIND_ATTESTATION_AND_DATASET_KEY_LINEAGE_TO_ADR0350_RECEIPTS",
    "REQUIRE_FRESH_NONREVOCATION_BINDING_CUSTODY_AND_DOMAIN_CLAIMS",
    "PRESERVE_ADR0350_BLOCK",
    "BIND_LIFECYCLE_AND_CONTENT_ISSUANCE_REPLAY_BEFORE_ANY_ACTIVATION",
)

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_AUTHORITY = {
    "research_evidence_only": True,
    "current_admission_allowed": False,
    "effective_budget_activation_allowed": False,
    "http_registration_allowed": False,
    "runtime_activation_allowed": False,
    "writer_allowed": False,
    "paper_authorized": False,
    "live_order_allowed": False,
}
_BASE_ACTIVATION_BLOCKERS = (
    "UNMOUNTED_CANDIDATE",
    "EXTERNAL_LIFECYCLE_GOVERNANCE_AUTHORITY_UNPROVEN",
    "EXTERNAL_PROVIDER_DATASET_KEY_CONTROL_UNPROVEN",
    "EXTERNAL_REVOCATION_REGISTRY_DURABILITY_UNPROVEN",
    "LIFECYCLE_RECEIPT_REPLAY_GATE_NOT_BOUND",
    "CONTENT_ISSUANCE_REPLAY_GATE_NOT_BOUND",
    "DURABLE_EXTERNAL_REGISTRY_UNPROVEN",
    "NO_EFFECTIVE_BUDGET_CONSUMER_BOUND",
    "PAPER_LIVE_UNAUTHORIZED",
)
_LIFECYCLE_BINDING_FIELDS = frozenset(
    {
        "custody_policy_hash",
        "custody_policy_id",
        "governance_key_id",
        "governance_public_key_sha256",
        "governance_receipt_issued_at_utc",
        "key_epoch",
        "lifecycle_governance_receipt_hash",
        "lifecycle_registration_hash",
        "lifecycle_verification_hash",
        "previous_provider_dataset_key_commitment",
        "previous_provider_dataset_key_id",
        "provider_dataset_key_id",
        "provider_dataset_public_key_sha256",
        "provider_id_hash",
        "reference_time_utc",
        "revocation_registry_id",
        "revocation_snapshot_at_utc",
        "revocation_snapshot_hash",
        "rotation_policy_hash",
        "rotation_policy_id",
        "source_attestation_hash",
        "source_attestation_verification_hash",
        "source_dataset_registration_hash",
        "window_id",
    }
)
_PREREGISTRATION_FIELDS = frozenset(
    {
        "activation_sequence",
        "authority",
        "expected_lifecycle_bindings",
        "expected_window_count",
        "expected_windows",
        "gate_contract_hash",
        "lifecycle_gate_v1_implementation_sha256",
        "preregistration_hash",
        "provider_binding_preregistration_hash",
        "provider_binding_v1_implementation_sha256",
        "registration_sequence",
        "schema_version",
        "static_fingerprint",
        "status",
        "study_identity_hash",
        "window_order_hash",
    }
)
_LIFECYCLE_BUNDLE_FIELDS = frozenset(
    {
        "attestation_context",
        "attestation_document",
        "governance_public_key_base64",
        "lifecycle_gate_document",
        "lifecycle_receipt",
        "lifecycle_registration",
        "window_id",
    }
)


def _exact_hash(value: Any) -> bool:
    return bool(
        type(value) is str
        and len(value) == 64
        and value == value.lower()
        and all(character in "0123456789abcdef" for character in value)
    )


def _positive_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool) and value > 0


def _nonnegative_int(value: Any) -> bool:
    return type(value) is int and not isinstance(value, bool) and value >= 0


def _strict_id(value: Any) -> bool:
    return type(value) is str and bool(_ID_RE.fullmatch(value))


def _strict_timestamp(value: Any) -> bool:
    return type(value) is str and bool(value) and value == value.strip()


def _sealed_document_valid(document: Any, hash_field: str) -> bool:
    if type(document) is not dict or not _exact_hash(document.get(hash_field)):
        return False
    try:
        unsigned = deepcopy(document)
        unsigned.pop(hash_field)
        expected = seal_strict_canonical_document(unsigned, hash_field)
    except (KeyError, TypeError, ValueError):
        return False
    return strict_json_contract_equal(document, expected)


def _provider_binding_preregistration_exact(
    document: Any,
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
) -> bool:
    if (
        type(document) is not dict
        or type(overlap_preregistration) is not dict
        or type(multi_window_preregistration) is not dict
    ):
        return False
    try:
        expected = provider_binding_v1.build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_preregistration_v1(
            overlap_preregistration,
            multi_window_preregistration,
            document.get("expected_window_issuer_bindings"),
            registration_sequence=document.get("registration_sequence"),
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        type(expected) is dict
        and strict_json_contract_equal(document, expected)
    )


def _lifecycle_binding_valid(value: Any) -> bool:
    if type(value) is not dict or frozenset(value) != _LIFECYCLE_BINDING_FIELDS:
        return False
    hash_fields = {
        "custody_policy_hash",
        "governance_public_key_sha256",
        "lifecycle_governance_receipt_hash",
        "lifecycle_registration_hash",
        "lifecycle_verification_hash",
        "previous_provider_dataset_key_commitment",
        "provider_dataset_public_key_sha256",
        "provider_id_hash",
        "revocation_snapshot_hash",
        "rotation_policy_hash",
        "source_attestation_hash",
        "source_attestation_verification_hash",
        "source_dataset_registration_hash",
    }
    id_fields = {
        "custody_policy_id",
        "governance_key_id",
        "previous_provider_dataset_key_id",
        "provider_dataset_key_id",
        "revocation_registry_id",
        "rotation_policy_id",
        "window_id",
    }
    timestamp_fields = {
        "governance_receipt_issued_at_utc",
        "reference_time_utc",
        "revocation_snapshot_at_utc",
    }
    return bool(
        all(_exact_hash(value.get(field)) for field in hash_fields)
        and all(_strict_id(value.get(field)) for field in id_fields)
        and all(_strict_timestamp(value.get(field)) for field in timestamp_fields)
        and _nonnegative_int(value.get("key_epoch"))
    )


def _lifecycle_bindings_valid(value: Any, windows: Any) -> bool:
    if (
        type(value) is not list
        or type(windows) is not list
        or len(value) != len(windows)
        or not value
        or not all(_lifecycle_binding_valid(row) for row in value)
        or [row["window_id"] for row in value] != windows
    ):
        return False
    for field in (
        "lifecycle_governance_receipt_hash",
        "lifecycle_registration_hash",
        "lifecycle_verification_hash",
        "source_attestation_verification_hash",
    ):
        if len({row[field] for row in value}) != len(value):
            return False
    consistency_fields = (
        "custody_policy_hash",
        "custody_policy_id",
        "governance_key_id",
        "governance_public_key_sha256",
        "key_epoch",
        "previous_provider_dataset_key_commitment",
        "previous_provider_dataset_key_id",
        "reference_time_utc",
        "revocation_registry_id",
        "revocation_snapshot_at_utc",
        "revocation_snapshot_hash",
        "rotation_policy_hash",
        "rotation_policy_id",
    )
    grouped: dict[tuple[str, str, str], tuple[Any, ...]] = {}
    for row in value:
        key = (
            row["provider_id_hash"],
            row["provider_dataset_key_id"],
            row["provider_dataset_public_key_sha256"],
        )
        policy = tuple(row[field] for field in consistency_fields)
        previous = grouped.setdefault(key, policy)
        if previous != policy:
            return False
    return True


_CONTRACT_MANIFEST = {
    "schema_version": GATE_SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "source_contracts": {
        "adr0121": {
            "schema_version": lifecycle_gate_v1.SCHEMA_VERSION,
            "implementation_sha256": LIFECYCLE_GATE_V1_IMPLEMENTATION_SHA256,
            "exact_verifier_required": True,
        },
        "adr0350": {
            "schema_version": provider_binding_v1.GATE_SCHEMA_VERSION,
            "implementation_sha256": PROVIDER_BINDING_V1_IMPLEMENTATION_SHA256,
            "exact_verifier_required": True,
        },
    },
    "required_positive_lifecycle_facts": [
        "GOVERNANCE_RECEIPT_SIGNATURE_VERIFIED",
        "ROTATION_EPOCH_AND_PREVIOUS_COMMITMENT_BOUND",
        "FRESH_NONREVOCATION_CLAIM_VERIFIED",
        "PROVIDER_KEY_BINDING_CLAIM_VERIFIED",
        "PROVIDER_DATASET_KEY_CUSTODY_CLAIM_VERIFIED",
        "CUSTODY_DOMAIN_SEPARATION_CLAIM_VERIFIED",
    ],
    "same_dataset_key_cross_window_policy": (
        "EXACT_GOVERNANCE_EPOCH_POLICY_SNAPSHOT_AND_REFERENCE_TIME_MATCH"
    ),
    "upstream_block_action": "PRESERVE_ADR0350_BLOCK",
    "external_governance_claimed": False,
    "lifecycle_replay_claimed": False,
    "content_issuance_replay_claimed": False,
    "activation_sequence": list(ACTIVATION_SEQUENCE),
}
GATE_CONTRACT_HASH = strict_canonical_hash(_CONTRACT_MANIFEST)


def build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_preregistration_v1(
    provider_binding_preregistration: Any,
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
    expected_lifecycle_bindings: Any,
    *,
    registration_sequence: Any,
) -> dict[str, Any] | None:
    """Preregister exact lifecycle evidence for every provider-attested window."""
    if (
        not _provider_binding_preregistration_exact(
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
        )
        or not _positive_int(registration_sequence)
        or registration_sequence
        <= provider_binding_preregistration["registration_sequence"]
    ):
        return None
    windows = provider_binding_preregistration["expected_windows"]
    if not _lifecycle_bindings_valid(expected_lifecycle_bindings, windows):
        return None
    issuer_rows = provider_binding_preregistration[
        "expected_window_issuer_bindings"
    ]
    for issuer, lifecycle in zip(
        issuer_rows,
        expected_lifecycle_bindings,
        strict=True,
    ):
        if (
            issuer["window_id"] != lifecycle["window_id"]
            or issuer["provider_id_hash"] != lifecycle["provider_id_hash"]
            or issuer["provider_dataset_key_id"]
            != lifecycle["provider_dataset_key_id"]
            or issuer["provider_dataset_public_key_sha256"]
            != lifecycle["provider_dataset_public_key_sha256"]
            or issuer["provider_dataset_verification_hash"]
            != lifecycle["source_attestation_verification_hash"]
            or issuer["provider_dataset_attestation_hash"]
            != lifecycle["source_attestation_hash"]
            or issuer["provider_dataset_registration_hash"]
            != lifecycle["source_dataset_registration_hash"]
        ):
            return None
    document = {
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "authority": deepcopy(_AUTHORITY),
        "expected_lifecycle_bindings": deepcopy(expected_lifecycle_bindings),
        "expected_window_count": len(windows),
        "expected_windows": deepcopy(windows),
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "lifecycle_gate_v1_implementation_sha256": (
            LIFECYCLE_GATE_V1_IMPLEMENTATION_SHA256
        ),
        "provider_binding_preregistration_hash": (
            provider_binding_preregistration["preregistration_hash"]
        ),
        "provider_binding_v1_implementation_sha256": (
            PROVIDER_BINDING_V1_IMPLEMENTATION_SHA256
        ),
        "registration_sequence": registration_sequence,
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "study_identity_hash": provider_binding_preregistration[
            "study_identity_hash"
        ],
        "window_order_hash": provider_binding_preregistration[
            "window_order_hash"
        ],
    }
    return seal_strict_canonical_document(document, "preregistration_hash")


def _preregistration_valid(document: Any) -> bool:
    return bool(
        type(document) is dict
        and frozenset(document) == _PREREGISTRATION_FIELDS
        and document.get("schema_version") == PREREGISTRATION_SCHEMA_VERSION
        and document.get("static_fingerprint") == STATIC_FINGERPRINT
        and document.get("status") == "PREREGISTERED_UNMOUNTED"
        and document.get("gate_contract_hash") == GATE_CONTRACT_HASH
        and document.get("authority") == _AUTHORITY
        and document.get("activation_sequence") == list(ACTIVATION_SEQUENCE)
        and document.get("lifecycle_gate_v1_implementation_sha256")
        == LIFECYCLE_GATE_V1_IMPLEMENTATION_SHA256
        and document.get("provider_binding_v1_implementation_sha256")
        == PROVIDER_BINDING_V1_IMPLEMENTATION_SHA256
        and _exact_hash(document.get("provider_binding_preregistration_hash"))
        and _exact_hash(document.get("study_identity_hash"))
        and _exact_hash(document.get("window_order_hash"))
        and _positive_int(document.get("registration_sequence"))
        and type(document.get("expected_windows")) is list
        and document.get("expected_window_count")
        == len(document.get("expected_windows", []))
        and document.get("window_order_hash")
        == strict_canonical_hash(document.get("expected_windows"))
        and _lifecycle_bindings_valid(
            document.get("expected_lifecycle_bindings"),
            document.get("expected_windows"),
        )
        and _sealed_document_valid(document, "preregistration_hash")
    )


def _unknown(reason: str) -> dict[str, Any]:
    return seal_strict_canonical_document(
        {
            "activation_blockers": list(_BASE_ACTIVATION_BLOCKERS),
            "authority": deepcopy(_AUTHORITY),
            "facts": {
                "all_lifecycle_gates_exactly_verified": False,
                "all_provider_binding_windows_lifecycle_bound": False,
                "content_issuance_replay_verified": False,
                "current_activated": False,
                "dataset_key_lifecycle_verified": False,
                "external_governance_authority_verified": False,
                "external_provider_dataset_key_control_verified": False,
                "external_revocation_registry_durability_verified": False,
                "fresh_nonrevocation_claims_verified": False,
                "historical_market_data_accessed": False,
                "independence_units_claimed": False,
                "lifecycle_receipt_replay_registry_checked": False,
                "profitability_proven": False,
                "provider_binding_gate_exactly_verified": False,
                "provider_dataset_private_key_accepted": False,
                "raw_governance_material_embedded": False,
                "raw_observation_ids_embedded": False,
                "runtime_mutations_performed": False,
                "source_documents_embedded": False,
                "synthetic_only": True,
            },
            "gate_blockers": [reason],
            "gate_contract_hash": GATE_CONTRACT_HASH,
            "reason_code": "UNKNOWN_PROVIDER_ATTESTATION_LIFECYCLE_BINDING",
            "schema_version": GATE_SCHEMA_VERSION,
            "source": {
                "lifecycle_binding_preregistration_hash": None,
                "lifecycle_gate_v1_implementation_sha256": (
                    LIFECYCLE_GATE_V1_IMPLEMENTATION_SHA256
                ),
                "provider_binding_gate_hash": None,
                "provider_binding_preregistration_hash": None,
                "provider_binding_v1_implementation_sha256": (
                    PROVIDER_BINDING_V1_IMPLEMENTATION_SHA256
                ),
                "study_identity_hash": None,
                "window_order_hash": None,
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "UNKNOWN",
            "summary": None,
            "window_lifecycle_receipts": [],
        },
        "gate_hash",
    )


def evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1(
    preregistration: Any,
    provider_binding_gate_document: Any,
    provider_binding_preregistration: Any,
    overlap_gate_document: Any,
    overlap_preregistration: Any,
    overlap_evidence: Any,
    multi_window_gate_document: Any,
    multi_window_preregistration: Any,
    window_audits: Any,
    window_provider_attestation_bundles: Any,
    window_lifecycle_bundles: Any,
    *,
    expected_preregistration_hash: Any,
    expected_provider_binding_gate_hash: Any,
    expected_provider_binding_preregistration_hash: Any,
    expected_overlap_gate_hash: Any,
    expected_overlap_preregistration_hash: Any,
    expected_overlap_evidence_hash: Any,
    expected_multi_window_gate_hash: Any,
    expected_multi_window_preregistration_hash: Any,
    expected_window_audit_hashes: Any,
) -> dict[str, Any]:
    """Verify exact fresh lifecycle claims for every ADR0350 window."""
    if (
        not _preregistration_valid(preregistration)
        or not _exact_hash(expected_preregistration_hash)
        or preregistration["preregistration_hash"]
        != expected_preregistration_hash
        or preregistration["provider_binding_preregistration_hash"]
        != expected_provider_binding_preregistration_hash
        or type(provider_binding_preregistration) is not dict
        or provider_binding_preregistration.get("preregistration_hash")
        != expected_provider_binding_preregistration_hash
        or not _provider_binding_preregistration_exact(
            provider_binding_preregistration,
            overlap_preregistration,
            multi_window_preregistration,
        )
        or preregistration["study_identity_hash"]
        != provider_binding_preregistration["study_identity_hash"]
        or preregistration["window_order_hash"]
        != provider_binding_preregistration["window_order_hash"]
        or preregistration["expected_windows"]
        != provider_binding_preregistration["expected_windows"]
    ):
        return _unknown("LIFECYCLE_OR_PROVIDER_BINDING_PREREGISTRATION_INVALID")
    try:
        provider_binding_exact = provider_binding_v1.verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1(
            provider_binding_gate_document,
            provider_binding_preregistration,
            overlap_gate_document,
            overlap_preregistration,
            overlap_evidence,
            multi_window_gate_document,
            multi_window_preregistration,
            window_audits,
            window_provider_attestation_bundles,
            expected_gate_hash=expected_provider_binding_gate_hash,
            expected_preregistration_hash=(
                expected_provider_binding_preregistration_hash
            ),
            expected_overlap_gate_hash=expected_overlap_gate_hash,
            expected_overlap_preregistration_hash=(
                expected_overlap_preregistration_hash
            ),
            expected_overlap_evidence_hash=expected_overlap_evidence_hash,
            expected_multi_window_gate_hash=expected_multi_window_gate_hash,
            expected_multi_window_preregistration_hash=(
                expected_multi_window_preregistration_hash
            ),
            expected_window_audit_hashes=expected_window_audit_hashes,
        )
    except (KeyError, TypeError, ValueError):
        provider_binding_exact = False
    if not provider_binding_exact:
        return _unknown("ADR0350_GATE_EXACT_REBUILD_FAILED")
    if (
        type(provider_binding_gate_document) is not dict
        or provider_binding_gate_document.get("status") not in {"PASS", "BLOCK"}
        or provider_binding_gate_document.get("facts", {}).get(
            "all_provider_attestations_exactly_verified"
        )
        is not True
    ):
        return _unknown("ADR0350_GATE_STATUS_NOT_DECISION_KNOWN")

    windows = preregistration["expected_windows"]
    expected_rows = preregistration["expected_lifecycle_bindings"]
    provider_receipts = provider_binding_gate_document.get(
        "window_binding_receipts"
    )
    if (
        type(window_lifecycle_bundles) is not list
        or type(provider_receipts) is not list
        or len(window_lifecycle_bundles) != len(windows)
        or len(provider_receipts) != len(windows)
    ):
        return _unknown("WINDOW_LIFECYCLE_SET_NOT_EXACT")

    receipts: list[dict[str, Any]] = []
    for index, window_id in enumerate(windows):
        expected = expected_rows[index]
        provider_receipt = provider_receipts[index]
        bundle = window_lifecycle_bundles[index]
        if (
            type(bundle) is not dict
            or frozenset(bundle) != _LIFECYCLE_BUNDLE_FIELDS
            or bundle.get("window_id") != window_id
            or type(provider_receipt) is not dict
            or provider_receipt.get("window_id") != window_id
        ):
            return _unknown("WINDOW_LIFECYCLE_ORDER_OR_SHAPE_INVALID")
        lifecycle_document = bundle["lifecycle_gate_document"]
        lifecycle_registration = bundle["lifecycle_registration"]
        lifecycle_receipt = bundle["lifecycle_receipt"]
        attestation_document = bundle["attestation_document"]
        try:
            lifecycle_exact = lifecycle_gate_v1.verify_provider_dataset_key_lifecycle_gate_v1(
                lifecycle_document,
                attestation_document,
                bundle["attestation_context"],
                lifecycle_registration,
                bundle["governance_public_key_base64"],
                lifecycle_receipt,
                expected_registration_hash=expected[
                    "lifecycle_registration_hash"
                ],
                expected_lifecycle_receipt_hash=expected[
                    "lifecycle_governance_receipt_hash"
                ],
                reference_time_utc=expected["reference_time_utc"],
            )
        except (KeyError, TypeError, ValueError):
            lifecycle_exact = False
        if not lifecycle_exact:
            return _unknown("ADR0121_LIFECYCLE_GATE_EXACT_REBUILD_FAILED")
        try:
            facts = lifecycle_document["facts"]
            lifecycle_facts_valid = (
                lifecycle_document["status"] == "PASS"
                and facts["governance_receipt_signature_verified"] is True
                and facts["rotation_epoch_and_previous_commitment_bound"] is True
                and facts["fresh_non_revocation_claim_verified"] is True
                and facts["provider_key_binding_claim_verified"] is True
                and facts["provider_dataset_key_custody_claim_verified"] is True
                and facts["custody_domain_separation_claim_verified"] is True
                and facts["external_governance_authority_verified"] is False
                and facts["external_provider_dataset_key_control_verified"]
                is False
                and facts["external_revocation_registry_durability_verified"]
                is False
                and facts["lifecycle_receipt_replay_registry_checked"] is False
            )
            exact_bindings = (
                lifecycle_document["verification_hash"]
                == expected["lifecycle_verification_hash"]
                and lifecycle_document["lifecycle_registration_hash"]
                == lifecycle_registration["registration_hash"]
                == expected["lifecycle_registration_hash"]
                and lifecycle_document["lifecycle_governance_receipt_hash"]
                == lifecycle_receipt["lifecycle_receipt_hash"]
                == expected["lifecycle_governance_receipt_hash"]
                and lifecycle_document["source_attestation_verification_hash"]
                == attestation_document["verification_hash"]
                == provider_receipt["provider_dataset_verification_hash"]
                == expected["source_attestation_verification_hash"]
                and lifecycle_document["source_attestation_hash"]
                == attestation_document["source_attestation_hash"]
                == provider_receipt["provider_dataset_attestation_hash"]
                == expected["source_attestation_hash"]
                and lifecycle_document["source_dataset_registration_hash"]
                == attestation_document["source_registration_hash"]
                == provider_receipt["provider_dataset_registration_hash"]
                == expected["source_dataset_registration_hash"]
                and lifecycle_document["provider_id_hash"]
                == provider_receipt["provider_id_hash"]
                == expected["provider_id_hash"]
                and lifecycle_document["provider_dataset_key_id"]
                == provider_receipt["provider_dataset_key_id"]
                == expected["provider_dataset_key_id"]
                and lifecycle_document["provider_dataset_public_key_sha256"]
                == provider_receipt["provider_dataset_public_key_sha256"]
                == expected["provider_dataset_public_key_sha256"]
                and lifecycle_document["governance_key_id"]
                == expected["governance_key_id"]
                and lifecycle_document["governance_public_key_sha256"]
                == expected["governance_public_key_sha256"]
                and lifecycle_document["key_epoch"] == expected["key_epoch"]
                and lifecycle_document["previous_provider_dataset_key_id"]
                == expected["previous_provider_dataset_key_id"]
                and lifecycle_document[
                    "previous_provider_dataset_key_commitment"
                ]
                == expected["previous_provider_dataset_key_commitment"]
                and lifecycle_document["rotation_policy_id"]
                == expected["rotation_policy_id"]
                and lifecycle_document["rotation_policy_hash"]
                == expected["rotation_policy_hash"]
                and lifecycle_document["revocation_registry_id"]
                == expected["revocation_registry_id"]
                and lifecycle_document["revocation_snapshot_hash"]
                == expected["revocation_snapshot_hash"]
                and lifecycle_document["revocation_snapshot_at_utc"]
                == expected["revocation_snapshot_at_utc"]
                and lifecycle_document["custody_policy_id"]
                == expected["custody_policy_id"]
                and lifecycle_document["custody_policy_hash"]
                == expected["custody_policy_hash"]
                and lifecycle_document["governance_receipt_issued_at_utc"]
                == expected["governance_receipt_issued_at_utc"]
                and lifecycle_document["reference_time_utc"]
                == expected["reference_time_utc"]
            )
        except (KeyError, TypeError):
            lifecycle_facts_valid = False
            exact_bindings = False
        if not lifecycle_facts_valid:
            return _unknown("ADR0121_LIFECYCLE_FACTS_INVALID")
        if not exact_bindings:
            return _unknown("LIFECYCLE_TO_PROVIDER_BINDING_SPLICE")
        receipts.append(deepcopy(expected))

    provider_status = provider_binding_gate_document["status"]
    blockers = (
        ["PROVIDER_ATTESTATION_BINDING_GATE_V1_BLOCKED"]
        if provider_status == "BLOCK"
        else []
    )
    status = "PASS" if not blockers else "BLOCK"
    reason_code = (
        "PASS_PROVIDER_ATTESTATION_LIFECYCLE_BINDING"
        if status == "PASS"
        else "BLOCK_PROVIDER_ATTESTATION_LIFECYCLE_BINDING"
    )
    document = {
        "activation_blockers": list(_BASE_ACTIVATION_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
        "facts": {
            "all_lifecycle_gates_exactly_verified": True,
            "all_provider_binding_windows_lifecycle_bound": True,
            "content_issuance_replay_verified": False,
            "current_activated": False,
            "dataset_key_lifecycle_verified": True,
            "external_governance_authority_verified": False,
            "external_provider_dataset_key_control_verified": False,
            "external_revocation_registry_durability_verified": False,
            "fresh_nonrevocation_claims_verified": True,
            "historical_market_data_accessed": False,
            "independence_units_claimed": False,
            "lifecycle_receipt_replay_registry_checked": False,
            "profitability_proven": False,
            "provider_binding_gate_exactly_verified": True,
            "provider_dataset_private_key_accepted": False,
            "raw_governance_material_embedded": False,
            "raw_observation_ids_embedded": False,
            "runtime_mutations_performed": False,
            "source_documents_embedded": False,
            "synthetic_only": True,
        },
        "gate_blockers": blockers,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "reason_code": reason_code,
        "schema_version": GATE_SCHEMA_VERSION,
        "source": {
            "lifecycle_binding_preregistration_hash": preregistration[
                "preregistration_hash"
            ],
            "lifecycle_gate_v1_implementation_sha256": (
                LIFECYCLE_GATE_V1_IMPLEMENTATION_SHA256
            ),
            "provider_binding_gate_hash": provider_binding_gate_document[
                "gate_hash"
            ],
            "provider_binding_preregistration_hash": (
                provider_binding_preregistration["preregistration_hash"]
            ),
            "provider_binding_v1_implementation_sha256": (
                PROVIDER_BINDING_V1_IMPLEMENTATION_SHA256
            ),
            "study_identity_hash": preregistration["study_identity_hash"],
            "window_order_hash": preregistration["window_order_hash"],
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "distinct_dataset_key_count": len(
                {
                    (
                        receipt["provider_id_hash"],
                        receipt["provider_dataset_key_id"],
                        receipt["provider_dataset_public_key_sha256"],
                    )
                    for receipt in receipts
                }
            ),
            "distinct_governance_key_count": len(
                {
                    (
                        receipt["governance_key_id"],
                        receipt["governance_public_key_sha256"],
                    )
                    for receipt in receipts
                }
            ),
            "lifecycle_verified_window_count": len(receipts),
            "provider_binding_gate_status": provider_status,
            "window_count": len(windows),
        },
        "window_lifecycle_receipts": receipts,
    }
    return seal_strict_canonical_document(document, "gate_hash")


def verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1(
    document: Any,
    preregistration: Any,
    provider_binding_gate_document: Any,
    provider_binding_preregistration: Any,
    overlap_gate_document: Any,
    overlap_preregistration: Any,
    overlap_evidence: Any,
    multi_window_gate_document: Any,
    multi_window_preregistration: Any,
    window_audits: Any,
    window_provider_attestation_bundles: Any,
    window_lifecycle_bundles: Any,
    *,
    expected_gate_hash: Any,
    expected_preregistration_hash: Any,
    expected_provider_binding_gate_hash: Any,
    expected_provider_binding_preregistration_hash: Any,
    expected_overlap_gate_hash: Any,
    expected_overlap_preregistration_hash: Any,
    expected_overlap_evidence_hash: Any,
    expected_multi_window_gate_hash: Any,
    expected_multi_window_preregistration_hash: Any,
    expected_window_audit_hashes: Any,
) -> bool:
    if type(document) is not dict or not _exact_hash(expected_gate_hash):
        return False
    try:
        expected = evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1(
            preregistration,
            provider_binding_gate_document,
            provider_binding_preregistration,
            overlap_gate_document,
            overlap_preregistration,
            overlap_evidence,
            multi_window_gate_document,
            multi_window_preregistration,
            window_audits,
            window_provider_attestation_bundles,
            window_lifecycle_bundles,
            expected_preregistration_hash=expected_preregistration_hash,
            expected_provider_binding_gate_hash=expected_provider_binding_gate_hash,
            expected_provider_binding_preregistration_hash=(
                expected_provider_binding_preregistration_hash
            ),
            expected_overlap_gate_hash=expected_overlap_gate_hash,
            expected_overlap_preregistration_hash=(
                expected_overlap_preregistration_hash
            ),
            expected_overlap_evidence_hash=expected_overlap_evidence_hash,
            expected_multi_window_gate_hash=expected_multi_window_gate_hash,
            expected_multi_window_preregistration_hash=(
                expected_multi_window_preregistration_hash
            ),
            expected_window_audit_hashes=expected_window_audit_hashes,
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        strict_json_contract_equal(document, expected)
        and document.get("gate_hash") == expected_gate_hash
        and compare_digest(expected["gate_hash"], expected_gate_hash)
    )


__all__ = [
    "ACTIVATION_SEQUENCE",
    "GATE_CONTRACT_HASH",
    "GATE_SCHEMA_VERSION",
    "LIFECYCLE_GATE_V1_IMPLEMENTATION_SHA256",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROVIDER_BINDING_V1_IMPLEMENTATION_SHA256",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_preregistration_v1",
    "evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1",
    "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_lifecycle_binding_gate_v1",
]
