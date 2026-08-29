"""Signed structural evidence quorum for an unmounted snapshot storage adapter.

The contract verifies canonical report structure, Ed25519 signatures, complete
requirement coverage, and local observer separation.  It does not verify the
external identity of observers or any real persistence behavior.
"""

from __future__ import annotations

from hashlib import sha256
import re
from typing import Any

from cryptography.exceptions import InvalidSignature

from exchange_terminal.application import (
    witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1 as storage_preregistration,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
    strict_json_contract_equal,
)
from exchange_terminal.services.strict_ed25519_public_contract_v1 import (
    decode_canonical_base64_v1,
    load_canonical_ed25519_public_key_v1,
)


OBSERVER_REGISTRATION_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-observer-registration-v1"
)
OBSERVER_REPORT_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-observer-report-v1"
)
SIGNED_REPORT_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-signed-observer-report-v1"
)
QUORUM_EVALUATION_SCHEMA_VERSION = (
    "witness-ownership-snapshot-storage-evidence-quorum-evaluation-v1"
)
STATIC_FINGERPRINT = (
    "20260824-witness-ownership-snapshot-storage-evidence-quorum-v1-lock-1"
)
SIGNATURE_DOMAIN = (
    "hakimi.strategy-correlation.witness-ownership.snapshot-storage-evidence.v1"
)
OBSERVER_ROLE = "INDEPENDENT_STORAGE_CONFORMANCE_OBSERVER"

OUTCOME_PASS = "PASS"
OUTCOME_BLOCK = "BLOCK"
OUTCOME_UNKNOWN = "UNKNOWN"
ALLOWED_OUTCOMES = frozenset({OUTCOME_PASS, OUTCOME_BLOCK, OUTCOME_UNKNOWN})

REGISTERED_OBSERVER_COUNT = 3
REQUIRED_OBSERVER_QUORUM = 2
STATUS_SIGNED_STRUCTURAL_COVERAGE = (
    "SIGNED_STRUCTURAL_STORAGE_EVIDENCE_QUORUM_"
    "EXTERNAL_PERSISTENCE_UNPROVEN"
)
STATUS_BLOCK = "BLOCK"
GATE_STATUS_UNKNOWN = "UNKNOWN"
GATE_STATUS_BLOCK = "BLOCK"
PERMISSION_STATE = "RESEARCH_ONLY"

STORAGE_PREREGISTRATION_IMPLEMENTATION_SHA256 = (
    "04afd17f55c4a287852f727aadf771772d6770e0f1f9db8ebd98040bb95bb52f"
)

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}$")


def _is_sha256(value: Any) -> bool:
    return type(value) is str and _SHA256_RE.fullmatch(value) is not None


def _is_token(value: Any) -> bool:
    return type(value) is str and _TOKEN_RE.fullmatch(value) is not None


def build_witness_ownership_snapshot_storage_observer_registration_v1(
    *,
    observer_id: Any,
    trust_domain: Any,
    public_key_spki_sha256: Any,
) -> dict[str, Any]:
    if (
        not _is_token(observer_id)
        or not _is_token(trust_domain)
        or not _is_sha256(public_key_spki_sha256)
    ):
        return {}
    document = {
        "schema_version": OBSERVER_REGISTRATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "observer_role": OBSERVER_ROLE,
        "observer_id": observer_id,
        "trust_domain": trust_domain,
        "public_key_spki_sha256": public_key_spki_sha256,
        "external_observer_identity_verified": False,
    }
    return seal_strict_canonical_document(document, "observer_registration_hash")


def _is_exact_observer_registration(document: Any) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_witness_ownership_snapshot_storage_observer_registration_v1(
            observer_id=document["observer_id"],
            trust_domain=document["trust_domain"],
            public_key_spki_sha256=document["public_key_spki_sha256"],
        )
    except KeyError:
        return False
    return bool(expected) and strict_json_contract_equal(document, expected)


def _requirement_map(
    storage_preregistration_document: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    requirements = storage_preregistration_document.get("required_evidence")
    if type(requirements) is not list:
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for requirement in requirements:
        if type(requirement) is not dict:
            return {}
        requirement_id = requirement.get("requirement_id")
        if not _is_token(requirement_id) or requirement_id in mapped:
            return {}
        mapped[requirement_id] = requirement
    return mapped


def build_witness_ownership_snapshot_storage_observer_report_v1(
    storage_preregistration_document: Any,
    *,
    requirement_id: Any,
    observer_id: Any,
    observer_trust_domain: Any,
    run_context_hash: Any,
    scenario_preregistration_hash: Any,
    observed_artifact_hash: Any,
    declared_outcome: Any,
    storage_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if type(storage_preregistration_kwargs) is not dict:
        return {}
    if not storage_preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
        storage_preregistration_document,
        **storage_preregistration_kwargs,
    ):
        return {}
    if not _is_token(requirement_id):
        return {}
    requirements = _requirement_map(storage_preregistration_document)
    requirement = requirements.get(requirement_id)
    if requirement is None:
        return {}
    if not _is_token(observer_id) or not _is_token(observer_trust_domain):
        return {}
    hashes = (
        run_context_hash,
        scenario_preregistration_hash,
        observed_artifact_hash,
    )
    if not all(_is_sha256(value) for value in hashes) or len(set(hashes)) != 3:
        return {}
    if declared_outcome not in ALLOWED_OUTCOMES:
        return {}
    document = {
        "schema_version": OBSERVER_REPORT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "storage_adapter_preregistration_hash": storage_preregistration_document[
            "storage_adapter_preregistration_hash"
        ],
        "storage_backend_kind": storage_preregistration_document[
            "storage_domain"
        ]["storage_backend_kind"],
        "requirement_id": requirement_id,
        "requirement_scope": requirement["requirement_scope"],
        "observer_id": observer_id,
        "observer_trust_domain": observer_trust_domain,
        "run_context_hash": run_context_hash,
        "scenario_preregistration_hash": scenario_preregistration_hash,
        "observed_artifact_hash": observed_artifact_hash,
        "declared_outcome": declared_outcome,
        "isolated_storage_domain_claimed": True,
        "runtime_mutations_outside_isolated_domain_claimed": False,
        "paper_or_live_operation_claimed": False,
    }
    return seal_strict_canonical_document(document, "observer_report_hash")


def _is_exact_report(
    document: Any,
    storage_preregistration_document: Any,
    *,
    storage_preregistration_kwargs: Any,
) -> bool:
    if type(document) is not dict:
        return False
    try:
        expected = build_witness_ownership_snapshot_storage_observer_report_v1(
            storage_preregistration_document,
            requirement_id=document["requirement_id"],
            observer_id=document["observer_id"],
            observer_trust_domain=document["observer_trust_domain"],
            run_context_hash=document["run_context_hash"],
            scenario_preregistration_hash=document["scenario_preregistration_hash"],
            observed_artifact_hash=document["observed_artifact_hash"],
            declared_outcome=document["declared_outcome"],
            storage_preregistration_kwargs=storage_preregistration_kwargs,
        )
    except KeyError:
        return False
    return bool(expected) and strict_json_contract_equal(document, expected)


def build_witness_ownership_snapshot_storage_observer_signature_message_hash_v1(
    report_document: Any,
    storage_preregistration_document: Any,
    *,
    storage_preregistration_kwargs: Any,
) -> str:
    if not _is_exact_report(
        report_document,
        storage_preregistration_document,
        storage_preregistration_kwargs=storage_preregistration_kwargs,
    ):
        return ""
    return strict_canonical_hash(
        {
            "signature_domain": SIGNATURE_DOMAIN,
            "signed_report_schema_version": SIGNED_REPORT_SCHEMA_VERSION,
            "storage_adapter_preregistration_hash": storage_preregistration_document[
                "storage_adapter_preregistration_hash"
            ],
            "observer_report_hash": report_document["observer_report_hash"],
        }
    )


def build_signed_witness_ownership_snapshot_storage_observer_report_v1(
    report_document: Any,
    storage_preregistration_document: Any,
    observer_registration_document: Any,
    *,
    public_key_spki_base64: Any,
    signature_base64: Any,
    storage_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if not _is_exact_observer_registration(observer_registration_document):
        return {}
    if not _is_exact_report(
        report_document,
        storage_preregistration_document,
        storage_preregistration_kwargs=storage_preregistration_kwargs,
    ):
        return {}
    if (
        report_document["observer_id"]
        != observer_registration_document["observer_id"]
        or report_document["observer_trust_domain"]
        != observer_registration_document["trust_domain"]
    ):
        return {}
    message_hash = build_witness_ownership_snapshot_storage_observer_signature_message_hash_v1(
        report_document,
        storage_preregistration_document,
        storage_preregistration_kwargs=storage_preregistration_kwargs,
    )
    if not _is_sha256(message_hash):
        return {}
    try:
        spki_bytes = decode_canonical_base64_v1(
            public_key_spki_base64,
            "observer_public_key_spki_base64",
        )
        signature = decode_canonical_base64_v1(
            signature_base64,
            "observer_signature_base64",
        )
        if sha256(spki_bytes).hexdigest() != observer_registration_document[
            "public_key_spki_sha256"
        ]:
            return {}
        public_key = load_canonical_ed25519_public_key_v1(spki_bytes)
        public_key.verify(signature, bytes.fromhex(message_hash))
    except (InvalidSignature, TypeError, ValueError, UnicodeError):
        return {}
    document = {
        "schema_version": SIGNED_REPORT_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "signature_domain": SIGNATURE_DOMAIN,
        "report_document": report_document,
        "observer_registration_hash": observer_registration_document[
            "observer_registration_hash"
        ],
        "observer_public_key_spki_base64": public_key_spki_base64,
        "observer_signature_base64": signature_base64,
        "signature_message_hash": message_hash,
    }
    return seal_strict_canonical_document(document, "signed_observer_report_hash")


def _build_evaluation(
    storage_preregistration_document: dict[str, Any],
    *,
    status: str,
    gate_status: str,
    blocker_codes: tuple[str, ...],
    expected_requirement_count: int,
    covered_requirement_count: int,
    observed_signed_report_count: int,
    used_observer_count: int,
    signed_report_hashes: list[str],
    verified: bool,
) -> dict[str, Any]:
    evidence_bundle_hash = (
        strict_canonical_hash(
            {"signed_observer_report_hashes": sorted(signed_report_hashes)}
        )
        if signed_report_hashes
        else None
    )
    document = {
        "schema_version": QUORUM_EVALUATION_SCHEMA_VERSION,
        "static_fingerprint": STATIC_FINGERPRINT,
        "status": status,
        "gate_status": gate_status,
        "blocker_codes": list(blocker_codes),
        "storage_adapter_preregistration_hash": storage_preregistration_document[
            "storage_adapter_preregistration_hash"
        ],
        "storage_preregistration_implementation_sha256": (
            STORAGE_PREREGISTRATION_IMPLEMENTATION_SHA256
        ),
        "storage_backend_kind": storage_preregistration_document[
            "storage_domain"
        ]["storage_backend_kind"],
        "registered_observer_count": REGISTERED_OBSERVER_COUNT,
        "required_observer_quorum": REQUIRED_OBSERVER_QUORUM,
        "expected_requirement_count": expected_requirement_count,
        "covered_requirement_count": covered_requirement_count,
        "expected_signed_report_count": (
            expected_requirement_count * REQUIRED_OBSERVER_QUORUM
        ),
        "observed_signed_report_count": observed_signed_report_count,
        "used_observer_count": used_observer_count,
        "evidence_bundle_hash": evidence_bundle_hash,
        "observer_registration_structure_verified": verified,
        "signed_report_signatures_verified": verified,
        "requirement_coverage_verified": verified,
        "observer_quorum_structure_verified": verified,
        "scenario_and_artifact_consensus_verified": verified,
        "run_context_replay_absent": verified,
        "external_observer_identity_verified": False,
        "adapter_runtime_execution_verified": False,
        "external_persistence_independently_verified": False,
        "permission_state": PERMISSION_STATE,
        "permission": False,
        "paper_authorized": False,
        "live_authorized": False,
        "snapshot_publication_authorized": False,
        "current_chain_activated": False,
    }
    return seal_strict_canonical_document(document, "quorum_evaluation_hash")


def evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
    signed_report_documents: Any,
    storage_preregistration_document: Any,
    observer_registration_documents: Any,
    *,
    storage_preregistration_kwargs: Any,
) -> dict[str, Any]:
    if type(storage_preregistration_kwargs) is not dict:
        return {}
    if not storage_preregistration.verify_witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1(
        storage_preregistration_document,
        **storage_preregistration_kwargs,
    ):
        return {}
    requirements = _requirement_map(storage_preregistration_document)
    expected_count = len(requirements)

    if (
        type(observer_registration_documents) is not list
        or len(observer_registration_documents) != REGISTERED_OBSERVER_COUNT
        or not all(
            _is_exact_observer_registration(item)
            for item in observer_registration_documents
        )
    ):
        return _build_evaluation(
            storage_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("observer_registration_set_invalid",),
            expected_requirement_count=expected_count,
            covered_requirement_count=0,
            observed_signed_report_count=0,
            used_observer_count=0,
            signed_report_hashes=[],
            verified=False,
        )
    observer_by_id = {
        item["observer_id"]: item for item in observer_registration_documents
    }
    if (
        len(observer_by_id) != REGISTERED_OBSERVER_COUNT
        or len({item["trust_domain"] for item in observer_registration_documents})
        != REGISTERED_OBSERVER_COUNT
        or len(
            {
                item["public_key_spki_sha256"]
                for item in observer_registration_documents
            }
        )
        != REGISTERED_OBSERVER_COUNT
    ):
        return _build_evaluation(
            storage_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("observer_structural_independence_invalid",),
            expected_requirement_count=expected_count,
            covered_requirement_count=0,
            observed_signed_report_count=0,
            used_observer_count=0,
            signed_report_hashes=[],
            verified=False,
        )

    expected_report_count = expected_count * REQUIRED_OBSERVER_QUORUM
    if (
        type(signed_report_documents) is not list
        or len(signed_report_documents) != expected_report_count
    ):
        observed_count = (
            len(signed_report_documents)
            if type(signed_report_documents) is list
            else 0
        )
        return _build_evaluation(
            storage_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=("signed_report_collection_cardinality_invalid",),
            expected_requirement_count=expected_count,
            covered_requirement_count=0,
            observed_signed_report_count=observed_count,
            used_observer_count=0,
            signed_report_hashes=[],
            verified=False,
        )

    groups: dict[str, list[dict[str, Any]]] = {}
    signed_hashes: list[str] = []
    run_context_hashes: list[str] = []
    used_observers: set[str] = set()
    for signed_document in signed_report_documents:
        if type(signed_document) is not dict:
            blocker = "signed_observer_report_invalid"
            break
        report = signed_document.get("report_document")
        observer_id = report.get("observer_id") if type(report) is dict else None
        observer_registration = observer_by_id.get(observer_id)
        if observer_registration is None:
            blocker = "signed_observer_report_invalid"
            break
        rebuilt = build_signed_witness_ownership_snapshot_storage_observer_report_v1(
            report,
            storage_preregistration_document,
            observer_registration,
            public_key_spki_base64=signed_document.get(
                "observer_public_key_spki_base64"
            ),
            signature_base64=signed_document.get("observer_signature_base64"),
            storage_preregistration_kwargs=storage_preregistration_kwargs,
        )
        if not rebuilt or not strict_json_contract_equal(signed_document, rebuilt):
            blocker = "signed_observer_report_invalid"
            break
        requirement_id = report["requirement_id"]
        if requirement_id not in requirements:
            blocker = "signed_observer_report_requirement_invalid"
            break
        groups.setdefault(requirement_id, []).append(report)
        signed_hashes.append(signed_document["signed_observer_report_hash"])
        run_context_hashes.append(report["run_context_hash"])
        used_observers.add(observer_id)
    else:
        blocker = ""

    if blocker:
        return _build_evaluation(
            storage_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=(blocker,),
            expected_requirement_count=expected_count,
            covered_requirement_count=len(groups),
            observed_signed_report_count=len(signed_report_documents),
            used_observer_count=len(used_observers),
            signed_report_hashes=signed_hashes,
            verified=False,
        )
    if len(set(signed_hashes)) != len(signed_hashes):
        blocker = "signed_observer_report_replay_detected"
    elif len(set(run_context_hashes)) != len(run_context_hashes):
        blocker = "run_context_replay_detected"
    elif set(groups) != set(requirements):
        blocker = "requirement_coverage_invalid"
    elif len(used_observers) != REGISTERED_OBSERVER_COUNT:
        blocker = "registered_observer_coverage_invalid"
    else:
        blocker = ""
        for requirement_id in requirements:
            reports = groups[requirement_id]
            if len(reports) != REQUIRED_OBSERVER_QUORUM:
                blocker = "requirement_quorum_cardinality_invalid"
                break
            if len({report["observer_id"] for report in reports}) != 2 or len(
                {report["observer_trust_domain"] for report in reports}
            ) != 2:
                blocker = "requirement_observer_independence_invalid"
                break
            if any(report["declared_outcome"] != OUTCOME_PASS for report in reports):
                blocker = "requirement_outcome_not_pass"
                break
            if len(
                {report["scenario_preregistration_hash"] for report in reports}
            ) != 1:
                blocker = "requirement_scenario_consensus_invalid"
                break
            if len({report["observed_artifact_hash"] for report in reports}) != 1:
                blocker = "requirement_artifact_consensus_invalid"
                break

    if blocker:
        return _build_evaluation(
            storage_preregistration_document,
            status=STATUS_BLOCK,
            gate_status=GATE_STATUS_BLOCK,
            blocker_codes=(blocker,),
            expected_requirement_count=expected_count,
            covered_requirement_count=len(groups),
            observed_signed_report_count=len(signed_report_documents),
            used_observer_count=len(used_observers),
            signed_report_hashes=signed_hashes,
            verified=False,
        )
    return _build_evaluation(
        storage_preregistration_document,
        status=STATUS_SIGNED_STRUCTURAL_COVERAGE,
        gate_status=GATE_STATUS_UNKNOWN,
        blocker_codes=(),
        expected_requirement_count=expected_count,
        covered_requirement_count=len(groups),
        observed_signed_report_count=len(signed_report_documents),
        used_observer_count=len(used_observers),
        signed_report_hashes=signed_hashes,
        verified=True,
    )


def verify_witness_ownership_snapshot_storage_evidence_quorum_v1(
    document: Any,
    signed_report_documents: Any,
    storage_preregistration_document: Any,
    observer_registration_documents: Any,
    *,
    expected_quorum_evaluation_hash: Any,
    storage_preregistration_kwargs: Any,
) -> bool:
    if not _is_sha256(expected_quorum_evaluation_hash):
        return False
    expected = evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1(
        signed_report_documents,
        storage_preregistration_document,
        observer_registration_documents,
        storage_preregistration_kwargs=storage_preregistration_kwargs,
    )
    return (
        bool(expected)
        and expected.get("quorum_evaluation_hash")
        == expected_quorum_evaluation_hash
        and strict_json_contract_equal(document, expected)
    )


__all__ = [
    "ALLOWED_OUTCOMES",
    "GATE_STATUS_BLOCK",
    "GATE_STATUS_UNKNOWN",
    "OBSERVER_REGISTRATION_SCHEMA_VERSION",
    "OBSERVER_REPORT_SCHEMA_VERSION",
    "OBSERVER_ROLE",
    "OUTCOME_BLOCK",
    "OUTCOME_PASS",
    "OUTCOME_UNKNOWN",
    "PERMISSION_STATE",
    "QUORUM_EVALUATION_SCHEMA_VERSION",
    "REGISTERED_OBSERVER_COUNT",
    "REQUIRED_OBSERVER_QUORUM",
    "SIGNATURE_DOMAIN",
    "SIGNED_REPORT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "STATUS_BLOCK",
    "STATUS_SIGNED_STRUCTURAL_COVERAGE",
    "STORAGE_PREREGISTRATION_IMPLEMENTATION_SHA256",
    "build_signed_witness_ownership_snapshot_storage_observer_report_v1",
    "build_witness_ownership_snapshot_storage_observer_registration_v1",
    "build_witness_ownership_snapshot_storage_observer_report_v1",
    "build_witness_ownership_snapshot_storage_observer_signature_message_hash_v1",
    "evaluate_witness_ownership_snapshot_storage_evidence_quorum_v1",
    "verify_witness_ownership_snapshot_storage_evidence_quorum_v1",
]
