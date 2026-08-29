"""Bind ADR0349 observation memberships to provider-signed compositions.

This unmounted gate does not introduce a signing protocol. It exactly rebuilds
ADR0349 and the existing ADR0120 provider dataset-content attestation for every
window, then binds ADR0349 membership, price-grid, sample-count, and uncertainty
replay commitments to fields covered by the signed ADR0119 composition hash.
External provider key control, lifecycle, replay, and durable registry trust
remain explicitly unproven.
"""

from __future__ import annotations

from copy import deepcopy
from hmac import compare_digest
import re
from typing import Any

from exchange_terminal.services import (
    strategy_correlation_common_support_calendar_provider_composition_v1
    as composition_v1,
)
from exchange_terminal.services import (
    strategy_correlation_provider_dataset_content_attestation_v1
    as provider_attestation_v1,
)
from exchange_terminal.services import (
    strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1
    as overlap_gate_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)


PREREGISTRATION_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-binding-preregistration-v1"
)
GATE_SCHEMA_VERSION = (
    "strategy-correlation-uncertainty-multi-window-observation-membership-"
    "provider-attestation-binding-gate-v1"
)
STATIC_FINGERPRINT = (
    "20260824-strategy-correlation-uncertainty-multi-window-observation-"
    "membership-provider-attestation-binding-gate-v1-synthetic-unmounted-lock-1"
)
COMPOSITION_V1_IMPLEMENTATION_SHA256 = (
    "922e626c72c3eb6be64a7a7d07ea0339655318eacac44a5121370cf8e11b1197"
)
PROVIDER_ATTESTATION_V1_IMPLEMENTATION_SHA256 = (
    "91dcad9660f379c47c2e912bda5032cbabc72dc5af8c42ece2ea3bede19bc654"
)
OVERLAP_GATE_V1_IMPLEMENTATION_SHA256 = (
    "927cf4b7205347552211aab7ccf64a54f59aadfcb2fc944beef76885d1b0f239"
)
ACTIVATION_SEQUENCE = (
    "VERIFY_EXACT_ADR0349_PREREGISTRATION",
    "PREREGISTER_PROVIDER_ATTESTATION_BINDINGS_BEFORE_OVERLAP_EVIDENCE",
    "VERIFY_EXACT_ADR0349_GATE",
    "VERIFY_ONE_EXACT_ADR0120_ATTESTATION_PER_WINDOW",
    "BIND_SIGNED_ADR0119_COMPOSITION_TO_WINDOW_UNCERTAINTY_REPLAY",
    "BIND_SIGNED_COMMON_PRICE_INDEX_TO_ADR0349_PRICE_GRID_HASH",
    "BIND_SIGNED_COMMON_OBSERVATION_INDEX_TO_ADR0349_MEMBERSHIP_HASH",
    "BIND_SIGNED_COMMON_OBSERVATION_COUNT_TO_ADR0349_SAMPLE_COUNT",
    "PRESERVE_ADR0349_BLOCK",
    "BIND_DATASET_KEY_LIFECYCLE_AND_ISSUANCE_REPLAY_BEFORE_ANY_ACTIVATION",
)

_KEY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
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
    "EXTERNAL_PROVIDER_DATASET_KEY_CONTROL_UNPROVEN",
    "DATASET_KEY_LIFECYCLE_GATE_NOT_BOUND",
    "CONTENT_ISSUANCE_REPLAY_GATE_NOT_BOUND",
    "DURABLE_EXTERNAL_REGISTRY_UNPROVEN",
    "NO_EFFECTIVE_BUDGET_CONSUMER_BOUND",
    "PAPER_LIVE_UNAUTHORIZED",
)
_ISSUER_BINDING_FIELDS = frozenset(
    {
        "common_observation_count",
        "common_observation_index_hash",
        "common_price_index_hash",
        "composition_hash",
        "dataset_provider_binding_hash",
        "provider_dataset_attestation_hash",
        "provider_dataset_key_id",
        "provider_dataset_public_key_sha256",
        "provider_dataset_registration_hash",
        "provider_dataset_verification_hash",
        "provider_id_hash",
        "source_matrix_replay_hash",
        "window_id",
    }
)
_PREREGISTRATION_FIELDS = frozenset(
    {
        "activation_sequence",
        "authority",
        "expected_window_count",
        "expected_window_issuer_bindings",
        "expected_windows",
        "gate_contract_hash",
        "multi_window_preregistration_hash",
        "observation_identifier_scheme_hash",
        "overlap_preregistration_hash",
        "preregistration_hash",
        "provider_attestation_v1_implementation_sha256",
        "registration_sequence",
        "schema_version",
        "source_composition_v1_implementation_sha256",
        "source_overlap_gate_v1_implementation_sha256",
        "static_fingerprint",
        "status",
        "study_identity_hash",
        "window_order_hash",
    }
)
_PROVIDER_BUNDLE_FIELDS = frozenset(
    {
        "attestation_receipt",
        "composition_context",
        "composition_document",
        "provider_dataset_public_key_base64",
        "registration",
        "verification_document",
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


def _overlap_preregistration_exact(
    document: Any,
    multi_window_preregistration: Any,
) -> bool:
    if type(document) is not dict or type(multi_window_preregistration) is not dict:
        return False
    try:
        expected = overlap_gate_v1.build_strategy_correlation_uncertainty_multi_window_observation_overlap_preregistration_v1(
            multi_window_preregistration,
            study_identity_hash=document.get("study_identity_hash"),
            observation_identifier_scheme_hash=document.get(
                "observation_identifier_scheme_hash"
            ),
            registration_sequence=document.get("registration_sequence"),
        )
    except (KeyError, TypeError, ValueError):
        return False
    return bool(
        type(expected) is dict
        and strict_json_contract_equal(document, expected)
    )


def _issuer_binding_valid(value: Any) -> bool:
    return bool(
        type(value) is dict
        and frozenset(value) == _ISSUER_BINDING_FIELDS
        and type(value.get("window_id")) is str
        and value["window_id"]
        and value["window_id"] == value["window_id"].strip()
        and type(value.get("provider_dataset_key_id")) is str
        and _KEY_ID_RE.fullmatch(value["provider_dataset_key_id"])
        and _positive_int(value.get("common_observation_count"))
        and all(
            _exact_hash(value.get(field))
            for field in _ISSUER_BINDING_FIELDS
            if field
            not in {
                "common_observation_count",
                "provider_dataset_key_id",
                "window_id",
            }
        )
    )


def _issuer_bindings_valid(value: Any, windows: Any) -> bool:
    if (
        type(value) is not list
        or type(windows) is not list
        or len(value) != len(windows)
        or not value
        or not all(_issuer_binding_valid(row) for row in value)
        or [row["window_id"] for row in value] != windows
    ):
        return False
    unique_fields = (
        "composition_hash",
        "provider_dataset_attestation_hash",
        "provider_dataset_registration_hash",
        "provider_dataset_verification_hash",
        "source_matrix_replay_hash",
    )
    if any(
        len({row[field] for row in value}) != len(value)
        for field in unique_fields
    ):
        return False
    key_bindings: dict[tuple[str, str], str] = {}
    for row in value:
        identity = (row["provider_id_hash"], row["provider_dataset_key_id"])
        public_key_hash = row["provider_dataset_public_key_sha256"]
        previous = key_bindings.setdefault(identity, public_key_hash)
        if previous != public_key_hash:
            return False
    return True


_CONTRACT_MANIFEST = {
    "schema_version": GATE_SCHEMA_VERSION,
    "static_fingerprint": STATIC_FINGERPRINT,
    "source_contracts": {
        "adr0119": {
            "schema_version": composition_v1.SCHEMA_VERSION,
            "implementation_sha256": COMPOSITION_V1_IMPLEMENTATION_SHA256,
        },
        "adr0120": {
            "schema_version": provider_attestation_v1.SCHEMA_VERSION,
            "attestation_scope": provider_attestation_v1.ATTESTATION_SCOPE,
            "implementation_sha256": (
                PROVIDER_ATTESTATION_V1_IMPLEMENTATION_SHA256
            ),
            "exact_verifier_required": True,
        },
        "adr0349": {
            "schema_version": overlap_gate_v1.GATE_SCHEMA_VERSION,
            "implementation_sha256": OVERLAP_GATE_V1_IMPLEMENTATION_SHA256,
            "exact_verifier_required": True,
        },
    },
    "cross_bindings": [
        "WINDOW_ID",
        "PROVIDER_ID_HASH",
        "PROVIDER_DATASET_KEY_ID_AND_PUBLIC_KEY_HASH",
        "COMPOSITION_HASH",
        "DATASET_PROVIDER_BINDING_HASH",
        "SOURCE_MATRIX_REPLAY_HASH",
        "COMMON_PRICE_INDEX_HASH",
        "COMMON_OBSERVATION_INDEX_HASH",
        "COMMON_OBSERVATION_COUNT",
    ],
    "upstream_block_action": "PRESERVE_ADR0349_BLOCK",
    "external_provider_key_control_claimed": False,
    "dataset_key_lifecycle_claimed": False,
    "content_issuance_replay_claimed": False,
    "activation_sequence": list(ACTIVATION_SEQUENCE),
}
GATE_CONTRACT_HASH = strict_canonical_hash(_CONTRACT_MANIFEST)


def build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_preregistration_v1(
    overlap_preregistration: Any,
    multi_window_preregistration: Any,
    expected_window_issuer_bindings: Any,
    *,
    registration_sequence: Any,
) -> dict[str, Any] | None:
    """Preregister exact signed-composition bindings before overlap evidence."""
    if (
        not _overlap_preregistration_exact(
            overlap_preregistration,
            multi_window_preregistration,
        )
        or not _positive_int(registration_sequence)
        or registration_sequence <= overlap_preregistration["registration_sequence"]
    ):
        return None
    windows = overlap_preregistration["expected_windows"]
    if not _issuer_bindings_valid(expected_window_issuer_bindings, windows):
        return None
    document = {
        "activation_sequence": list(ACTIVATION_SEQUENCE),
        "authority": deepcopy(_AUTHORITY),
        "expected_window_count": len(windows),
        "expected_window_issuer_bindings": deepcopy(
            expected_window_issuer_bindings
        ),
        "expected_windows": deepcopy(windows),
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "multi_window_preregistration_hash": overlap_preregistration[
            "multi_window_preregistration_hash"
        ],
        "observation_identifier_scheme_hash": overlap_preregistration[
            "observation_identifier_scheme_hash"
        ],
        "overlap_preregistration_hash": overlap_preregistration[
            "preregistration_hash"
        ],
        "provider_attestation_v1_implementation_sha256": (
            PROVIDER_ATTESTATION_V1_IMPLEMENTATION_SHA256
        ),
        "registration_sequence": registration_sequence,
        "schema_version": PREREGISTRATION_SCHEMA_VERSION,
        "source_composition_v1_implementation_sha256": (
            COMPOSITION_V1_IMPLEMENTATION_SHA256
        ),
        "source_overlap_gate_v1_implementation_sha256": (
            OVERLAP_GATE_V1_IMPLEMENTATION_SHA256
        ),
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": "PREREGISTERED_UNMOUNTED",
        "study_identity_hash": overlap_preregistration["study_identity_hash"],
        "window_order_hash": overlap_preregistration["window_order_hash"],
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
        and document.get("source_composition_v1_implementation_sha256")
        == COMPOSITION_V1_IMPLEMENTATION_SHA256
        and document.get("provider_attestation_v1_implementation_sha256")
        == PROVIDER_ATTESTATION_V1_IMPLEMENTATION_SHA256
        and document.get("source_overlap_gate_v1_implementation_sha256")
        == OVERLAP_GATE_V1_IMPLEMENTATION_SHA256
        and _exact_hash(document.get("overlap_preregistration_hash"))
        and _exact_hash(document.get("multi_window_preregistration_hash"))
        and _exact_hash(document.get("observation_identifier_scheme_hash"))
        and _exact_hash(document.get("study_identity_hash"))
        and _exact_hash(document.get("window_order_hash"))
        and _positive_int(document.get("registration_sequence"))
        and type(document.get("expected_windows")) is list
        and document.get("expected_window_count")
        == len(document.get("expected_windows", []))
        and document.get("window_order_hash")
        == strict_canonical_hash(document.get("expected_windows"))
        and _issuer_bindings_valid(
            document.get("expected_window_issuer_bindings"),
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
                "all_memberships_bound_to_signed_compositions": False,
                "all_price_grids_bound_to_signed_compositions": False,
                "all_provider_attestations_exactly_verified": False,
                "all_uncertainty_replays_bound_to_signed_compositions": False,
                "content_issuance_replay_verified": False,
                "current_activated": False,
                "dataset_key_lifecycle_verified": False,
                "durable_external_registry_verified": False,
                "external_provider_data_issuance_verified": False,
                "external_provider_dataset_key_control_verified": False,
                "historical_market_data_accessed": False,
                "independence_units_claimed": False,
                "overlap_gate_exactly_verified": False,
                "profitability_proven": False,
                "provider_dataset_private_key_accepted": False,
                "provider_dataset_signature_verified": False,
                "raw_dates_embedded_in_gate_output": False,
                "raw_observation_ids_embedded_in_gate_output": False,
                "runtime_mutations_performed": False,
                "source_documents_embedded": False,
                "synthetic_only": True,
            },
            "gate_blockers": [reason],
            "gate_contract_hash": GATE_CONTRACT_HASH,
            "reason_code": "UNKNOWN_PROVIDER_ATTESTED_MEMBERSHIP_BINDING",
            "schema_version": GATE_SCHEMA_VERSION,
            "source": {
                "binding_preregistration_hash": None,
                "overlap_evidence_hash": None,
                "overlap_gate_hash": None,
                "overlap_preregistration_hash": None,
                "provider_attestation_v1_implementation_sha256": (
                    PROVIDER_ATTESTATION_V1_IMPLEMENTATION_SHA256
                ),
                "source_composition_v1_implementation_sha256": (
                    COMPOSITION_V1_IMPLEMENTATION_SHA256
                ),
                "source_overlap_gate_v1_implementation_sha256": (
                    OVERLAP_GATE_V1_IMPLEMENTATION_SHA256
                ),
                "study_identity_hash": None,
                "window_order_hash": None,
            },
            "static_fingerprint": STATIC_FINGERPRINT,
            "status": "UNKNOWN",
            "summary": None,
            "window_binding_receipts": [],
        },
        "gate_hash",
    )


def evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1(
    preregistration: Any,
    overlap_gate_document: Any,
    overlap_preregistration: Any,
    overlap_evidence: Any,
    multi_window_gate_document: Any,
    multi_window_preregistration: Any,
    window_audits: Any,
    window_provider_attestation_bundles: Any,
    *,
    expected_preregistration_hash: Any,
    expected_overlap_gate_hash: Any,
    expected_overlap_preregistration_hash: Any,
    expected_overlap_evidence_hash: Any,
    expected_multi_window_gate_hash: Any,
    expected_multi_window_preregistration_hash: Any,
    expected_window_audit_hashes: Any,
) -> dict[str, Any]:
    """Verify provider-signed source lineage for every ADR0349 window."""
    if (
        not _preregistration_valid(preregistration)
        or not _exact_hash(expected_preregistration_hash)
        or preregistration["preregistration_hash"]
        != expected_preregistration_hash
        or not _exact_hash(expected_overlap_preregistration_hash)
        or preregistration["overlap_preregistration_hash"]
        != expected_overlap_preregistration_hash
        or type(overlap_preregistration) is not dict
        or overlap_preregistration.get("preregistration_hash")
        != expected_overlap_preregistration_hash
        or not _overlap_preregistration_exact(
            overlap_preregistration,
            multi_window_preregistration,
        )
    ):
        return _unknown("BINDING_OR_OVERLAP_PREREGISTRATION_INVALID")
    if (
        preregistration["multi_window_preregistration_hash"]
        != expected_multi_window_preregistration_hash
        or preregistration["study_identity_hash"]
        != overlap_preregistration["study_identity_hash"]
        or preregistration["observation_identifier_scheme_hash"]
        != overlap_preregistration["observation_identifier_scheme_hash"]
        or preregistration["window_order_hash"]
        != overlap_preregistration["window_order_hash"]
        or preregistration["expected_windows"]
        != overlap_preregistration["expected_windows"]
        or type(overlap_evidence) is not dict
        or overlap_evidence.get("evidence_hash") != expected_overlap_evidence_hash
        or overlap_evidence.get("evidence_sequence")
        <= preregistration["registration_sequence"]
    ):
        return _unknown("BINDING_PREREGISTRATION_SOURCE_SPLICE")
    try:
        overlap_exact = overlap_gate_v1.verify_strategy_correlation_uncertainty_multi_window_observation_overlap_gate_v1(
            overlap_gate_document,
            overlap_preregistration,
            overlap_evidence,
            multi_window_gate_document,
            multi_window_preregistration,
            window_audits,
            expected_gate_hash=expected_overlap_gate_hash,
            expected_preregistration_hash=expected_overlap_preregistration_hash,
            expected_evidence_hash=expected_overlap_evidence_hash,
            expected_multi_window_gate_hash=expected_multi_window_gate_hash,
            expected_multi_window_preregistration_hash=(
                expected_multi_window_preregistration_hash
            ),
            expected_window_audit_hashes=expected_window_audit_hashes,
        )
    except (KeyError, TypeError, ValueError):
        overlap_exact = False
    if not overlap_exact:
        return _unknown("ADR0349_GATE_EXACT_REBUILD_FAILED")
    if (
        type(overlap_gate_document) is not dict
        or overlap_gate_document.get("status") not in {"PASS", "BLOCK"}
        or overlap_gate_document.get("facts", {}).get("all_windows_exactly_bound")
        is not True
    ):
        return _unknown("ADR0349_GATE_STATUS_NOT_DECISION_KNOWN")

    windows = preregistration["expected_windows"]
    expected_bindings = preregistration["expected_window_issuer_bindings"]
    evidence_rows = overlap_evidence.get("window_observations")
    if (
        type(window_provider_attestation_bundles) is not list
        or type(window_audits) is not list
        or type(evidence_rows) is not list
        or len(window_provider_attestation_bundles) != len(windows)
        or len(window_audits) != len(windows)
        or len(evidence_rows) != len(windows)
    ):
        return _unknown("WINDOW_PROVIDER_ATTESTATION_SET_NOT_EXACT")

    receipts: list[dict[str, Any]] = []
    for index, window_id in enumerate(windows):
        expected = expected_bindings[index]
        bundle = window_provider_attestation_bundles[index]
        evidence_row = evidence_rows[index]
        audit_input = window_audits[index]
        if (
            type(bundle) is not dict
            or frozenset(bundle) != _PROVIDER_BUNDLE_FIELDS
            or bundle.get("window_id") != window_id
            or type(evidence_row) is not dict
            or evidence_row.get("window_id") != window_id
            or type(audit_input) is not dict
            or audit_input.get("window_id") != window_id
        ):
            return _unknown("WINDOW_PROVIDER_ATTESTATION_ORDER_OR_SHAPE_INVALID")
        verification_document = bundle["verification_document"]
        composition_document = bundle["composition_document"]
        registration = bundle["registration"]
        attestation_receipt = bundle["attestation_receipt"]
        audit = audit_input.get("uncertainty_audit")
        matrix_replay = audit.get("matrix_replay") if type(audit) is dict else None
        try:
            provider_exact = provider_attestation_v1.verify_provider_dataset_content_attestation_v1(
                verification_document,
                composition_document,
                bundle["composition_context"],
                registration,
                bundle["provider_dataset_public_key_base64"],
                attestation_receipt,
                expected_registration_hash=expected[
                    "provider_dataset_registration_hash"
                ],
                expected_attestation_hash=expected[
                    "provider_dataset_attestation_hash"
                ],
            )
        except (KeyError, TypeError, ValueError):
            provider_exact = False
        if not provider_exact:
            return _unknown("ADR0120_PROVIDER_ATTESTATION_EXACT_REBUILD_FAILED")
        try:
            source_facts_valid = (
                verification_document["source_state"] == "VERIFIED"
                and verification_document["facts"][
                    "provider_dataset_signature_verified"
                ]
                is True
                and verification_document["facts"]["all_dataset_hashes_bound"]
                is True
                and verification_document["facts"][
                    "provider_dataset_content_claim_verified"
                ]
                is True
                and verification_document["facts"][
                    "external_provider_dataset_key_control_verified"
                ]
                is False
                and verification_document["facts"][
                    "external_provider_data_issuance_verified"
                ]
                is False
                and verification_document["facts"]["replay_registry_checked"]
                is False
            )
            exact_bindings = (
                verification_document["verification_hash"]
                == expected["provider_dataset_verification_hash"]
                and verification_document["source_composition_hash"]
                == composition_document["composition_hash"]
                == expected["composition_hash"]
                and verification_document["source_registration_hash"]
                == registration["registration_hash"]
                == expected["provider_dataset_registration_hash"]
                and verification_document["source_attestation_hash"]
                == attestation_receipt["attestation_hash"]
                == expected["provider_dataset_attestation_hash"]
                and verification_document["provider_id_hash"]
                == composition_document["provider_id_hash"]
                == expected["provider_id_hash"]
                and verification_document["provider_dataset_key_id"]
                == registration["provider_dataset_key_id"]
                == expected["provider_dataset_key_id"]
                and verification_document["provider_dataset_public_key_sha256"]
                == registration["provider_dataset_public_key_sha256"]
                == expected["provider_dataset_public_key_sha256"]
                and verification_document["dataset_provider_binding_hash"]
                == composition_document["dataset_provider_binding_hash"]
                == expected["dataset_provider_binding_hash"]
                and composition_document["source_matrix_replay_hash"]
                == matrix_replay["replay_hash"]
                == expected["source_matrix_replay_hash"]
                and composition_document["common_price_index_hash"]
                == evidence_row["common_price_date_grid_hash"]
                == expected["common_price_index_hash"]
                and composition_document["common_observation_index_hash"]
                == evidence_row["common_observation_membership_hash"]
                == expected["common_observation_index_hash"]
                and composition_document["common_observation_count"]
                == evidence_row["common_sample_count"]
                == expected["common_observation_count"]
            )
        except (KeyError, TypeError):
            source_facts_valid = False
            exact_bindings = False
        if not source_facts_valid:
            return _unknown("ADR0120_PROVIDER_ATTESTATION_FACTS_INVALID")
        if not exact_bindings:
            return _unknown("SIGNED_COMPOSITION_MEMBERSHIP_BINDING_SPLICE")
        receipts.append(
            {
                "common_observation_count": expected[
                    "common_observation_count"
                ],
                "common_observation_index_hash": expected[
                    "common_observation_index_hash"
                ],
                "common_price_index_hash": expected["common_price_index_hash"],
                "composition_hash": expected["composition_hash"],
                "dataset_provider_binding_hash": expected[
                    "dataset_provider_binding_hash"
                ],
                "provider_dataset_attestation_hash": expected[
                    "provider_dataset_attestation_hash"
                ],
                "provider_dataset_key_id": expected[
                    "provider_dataset_key_id"
                ],
                "provider_dataset_public_key_sha256": expected[
                    "provider_dataset_public_key_sha256"
                ],
                "provider_dataset_registration_hash": expected[
                    "provider_dataset_registration_hash"
                ],
                "provider_dataset_verification_hash": expected[
                    "provider_dataset_verification_hash"
                ],
                "provider_id_hash": expected["provider_id_hash"],
                "source_matrix_replay_hash": expected[
                    "source_matrix_replay_hash"
                ],
                "window_id": window_id,
            }
        )

    overlap_status = overlap_gate_document["status"]
    blockers = (
        ["OBSERVATION_OVERLAP_GATE_V1_BLOCKED"]
        if overlap_status == "BLOCK"
        else []
    )
    status = "PASS" if not blockers else "BLOCK"
    reason_code = (
        "PASS_PROVIDER_ATTESTED_OBSERVATION_MEMBERSHIP_BINDING"
        if status == "PASS"
        else "BLOCK_PROVIDER_ATTESTED_MEMBERSHIP_OVERLAP_GATE"
    )
    document = {
        "activation_blockers": list(_BASE_ACTIVATION_BLOCKERS),
        "authority": deepcopy(_AUTHORITY),
        "facts": {
            "all_memberships_bound_to_signed_compositions": True,
            "all_price_grids_bound_to_signed_compositions": True,
            "all_provider_attestations_exactly_verified": True,
            "all_uncertainty_replays_bound_to_signed_compositions": True,
            "content_issuance_replay_verified": False,
            "current_activated": False,
            "dataset_key_lifecycle_verified": False,
            "durable_external_registry_verified": False,
            "external_provider_data_issuance_verified": False,
            "external_provider_dataset_key_control_verified": False,
            "historical_market_data_accessed": False,
            "independence_units_claimed": False,
            "overlap_gate_exactly_verified": True,
            "profitability_proven": False,
            "provider_dataset_private_key_accepted": False,
            "provider_dataset_signature_verified": True,
            "raw_dates_embedded_in_gate_output": False,
            "raw_observation_ids_embedded_in_gate_output": False,
            "runtime_mutations_performed": False,
            "source_documents_embedded": False,
            "synthetic_only": True,
        },
        "gate_blockers": blockers,
        "gate_contract_hash": GATE_CONTRACT_HASH,
        "reason_code": reason_code,
        "schema_version": GATE_SCHEMA_VERSION,
        "source": {
            "binding_preregistration_hash": preregistration[
                "preregistration_hash"
            ],
            "overlap_evidence_hash": overlap_evidence["evidence_hash"],
            "overlap_gate_hash": overlap_gate_document["gate_hash"],
            "overlap_preregistration_hash": overlap_preregistration[
                "preregistration_hash"
            ],
            "provider_attestation_v1_implementation_sha256": (
                PROVIDER_ATTESTATION_V1_IMPLEMENTATION_SHA256
            ),
            "source_composition_v1_implementation_sha256": (
                COMPOSITION_V1_IMPLEMENTATION_SHA256
            ),
            "source_overlap_gate_v1_implementation_sha256": (
                OVERLAP_GATE_V1_IMPLEMENTATION_SHA256
            ),
            "study_identity_hash": preregistration["study_identity_hash"],
            "window_order_hash": preregistration["window_order_hash"],
        },
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "summary": {
            "distinct_provider_count": len(
                {receipt["provider_id_hash"] for receipt in receipts}
            ),
            "distinct_provider_dataset_key_count": len(
                {
                    (
                        receipt["provider_id_hash"],
                        receipt["provider_dataset_key_id"],
                        receipt["provider_dataset_public_key_sha256"],
                    )
                    for receipt in receipts
                }
            ),
            "overlap_gate_status": overlap_status,
            "provider_attestation_verified_window_count": len(receipts),
            "signed_membership_bound_window_count": len(receipts),
            "window_count": len(windows),
        },
        "window_binding_receipts": receipts,
    }
    return seal_strict_canonical_document(document, "gate_hash")


def verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1(
    document: Any,
    preregistration: Any,
    overlap_gate_document: Any,
    overlap_preregistration: Any,
    overlap_evidence: Any,
    multi_window_gate_document: Any,
    multi_window_preregistration: Any,
    window_audits: Any,
    window_provider_attestation_bundles: Any,
    *,
    expected_gate_hash: Any,
    expected_preregistration_hash: Any,
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
        expected = evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1(
            preregistration,
            overlap_gate_document,
            overlap_preregistration,
            overlap_evidence,
            multi_window_gate_document,
            multi_window_preregistration,
            window_audits,
            window_provider_attestation_bundles,
            expected_preregistration_hash=expected_preregistration_hash,
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
    "COMPOSITION_V1_IMPLEMENTATION_SHA256",
    "GATE_CONTRACT_HASH",
    "GATE_SCHEMA_VERSION",
    "OVERLAP_GATE_V1_IMPLEMENTATION_SHA256",
    "PREREGISTRATION_SCHEMA_VERSION",
    "PROVIDER_ATTESTATION_V1_IMPLEMENTATION_SHA256",
    "STATIC_FINGERPRINT",
    "build_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_preregistration_v1",
    "evaluate_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1",
    "verify_strategy_correlation_uncertainty_multi_window_observation_membership_provider_attestation_binding_gate_v1",
]
