from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest

from exchange_terminal.application.ports import (
    registry_organization_identity_v1 as organization_v1,
)
from exchange_terminal.application.ports import (
    registry_signer_source_trust_v1 as canonical_v1,
)
from exchange_terminal.interfaces import registry_signer_source_trust as legacy_v1


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "exchange_terminal" / "application"
CANONICAL_PATH = (
    APPLICATION_ROOT / "ports" / "registry_signer_source_trust_v1.py"
)
LEGACY_PATH = (
    ROOT / "exchange_terminal" / "interfaces" / "registry_signer_source_trust.py"
)
CONSUMER_PATH = (
    APPLICATION_ROOT
    / "anti_replay_registry_signer_source_trust_preregistration_v1.py"
)
CANONICAL_MODULE = (
    "exchange_terminal.application.ports.registry_signer_source_trust_v1"
)
ORGANIZATION_MODULE = (
    "exchange_terminal.application.ports.registry_organization_identity_v1"
)
LEGACY_MODULE = "exchange_terminal.interfaces.registry_signer_source_trust"
CANONICAL_SHA256 = (
    "04e288bc11db85e21a775602d54a453d514474b9bf82133716ec4e63f72775ff"
)
PUBLIC_NAMES = (
    "SIGNATURE_ALGORITHM",
    "SOURCE_TRUST_RECORD_SCHEMA_VERSION",
    "SOURCE_TRUST_SOURCE_PORT_VERSION",
    "RegistryOrganizationIdentityEvidenceKindV1",
    "RegistrySignerSourceTrustRecordV1",
    "RegistrySignerSourceTrustSourceV1",
    "expected_signer_role_v1",
    "expected_source_trust_authority_role_v1",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _import_targets(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
        elif isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
    return targets


def _record_kwargs() -> dict[str, object]:
    kind = (
        organization_v1.RegistryOrganizationIdentityEvidenceKindV1
        .ORGANIZATION_REGISTRY_ATTESTATION
    )
    return {
        "evidence_kind": kind,
        "signer_role": organization_v1.expected_signer_role_v1(kind),
        "signer_public_key_spki_sha256": "a" * 64,
        "subject_registry_id": "subject.registry",
        "subject_public_key_spki_sha256": "b" * 64,
        "authority_registry_id": "authority.registry",
        "authority_role": canonical_v1.expected_source_trust_authority_role_v1(
            kind
        ),
        "authority_public_key_spki_sha256": "c" * 64,
        "authority_statement_sha256": "d" * 64,
        "trust_anchor_id": "anchor.registry",
        "trust_anchor_sha256": "e" * 64,
        "source_adapter_id": "adapter.registry",
        "source_adapter_implementation_sha256": "f" * 64,
        "policy_id": "policy.registry",
        "policy_version": "version.1",
        "revocation_source_id": "revocation.registry",
        "revocation_snapshot_sha256": "1" * 64,
        "issued_at_ms": 1_000,
        "expires_at_ms": 2_000,
    }


class RegistrySignerSourceTrustApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_canonical_port_hash_is_pinned(self):
        self.assertEqual(_sha256(CANONICAL_PATH), CANONICAL_SHA256)

    def test_canonical_port_depends_on_the_application_owned_organization_port(self):
        targets = _import_targets(CANONICAL_PATH)
        self.assertIn(ORGANIZATION_MODULE, targets)
        self.assertFalse(
            [target for target in targets if target.startswith("exchange_terminal.interfaces.")]
        )

    def test_legacy_shim_pins_the_canonical_module_and_hash(self):
        self.assertEqual(legacy_v1.CANONICAL_PORT_MODULE, CANONICAL_MODULE)
        self.assertEqual(
            legacy_v1.CANONICAL_PORT_IMPLEMENTATION_SHA256,
            CANONICAL_SHA256,
        )

    def test_legacy_public_contract_objects_are_exact_canonical_objects(self):
        for name in PUBLIC_NAMES:
            with self.subTest(name=name):
                self.assertIs(getattr(legacy_v1, name), getattr(canonical_v1, name))

    def test_legacy_shim_defines_no_duplicate_class_or_function(self):
        tree = ast.parse(
            LEGACY_PATH.read_text(encoding="utf-8"),
            filename=str(LEGACY_PATH),
        )
        definitions = [
            node.name
            for node in tree.body
            if isinstance(
                node,
                (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef),
            )
        ]
        self.assertEqual(definitions, [])
        self.assertIn(CANONICAL_MODULE, _import_targets(LEGACY_PATH))

    def test_legacy_constructed_record_is_a_canonical_record(self):
        record = legacy_v1.RegistrySignerSourceTrustRecordV1(**_record_kwargs())
        self.assertIsInstance(
            record,
            canonical_v1.RegistrySignerSourceTrustRecordV1,
        )

    def test_namespace_collision_remains_fail_closed_through_legacy_path(self):
        kwargs = _record_kwargs()
        kwargs["authority_registry_id"] = kwargs["subject_registry_id"]
        with self.assertRaisesRegex(ValueError, "namespaces must be distinct"):
            legacy_v1.RegistrySignerSourceTrustRecordV1(**kwargs)

    def test_application_consumer_uses_the_canonical_signer_trust_port(self):
        targets = _import_targets(CONSUMER_PATH)
        self.assertIn(CANONICAL_MODULE, targets)
        self.assertNotIn(LEGACY_MODULE, targets)

    def test_direct_application_to_interfaces_import_statements_do_not_regress_above_seven(self):
        edges: list[tuple[str, str]] = []
        for path in sorted(APPLICATION_ROOT.rglob("*.py")):
            for target in _import_targets(path):
                if target.startswith("exchange_terminal.interfaces."):
                    edges.append((path.relative_to(APPLICATION_ROOT).as_posix(), target))
        self.assertLessEqual(len(edges), 7)
        self.assertFalse([edge for edge in edges if edge[1] == LEGACY_MODULE])

    def test_schema_and_protocol_versions_are_unchanged(self):
        self.assertEqual(
            canonical_v1.SOURCE_TRUST_RECORD_SCHEMA_VERSION,
            "registry-signer-source-trust-record-v1",
        )
        self.assertEqual(
            canonical_v1.SOURCE_TRUST_SOURCE_PORT_VERSION,
            "registry-signer-source-trust-source-port-v1",
        )

    def test_runtime_checkable_protocol_identity_is_preserved(self):
        class Source:
            source_adapter_id = "adapter.registry"
            protocol_version = canonical_v1.SOURCE_TRUST_SOURCE_PORT_VERSION

            def fetch_source_trust_records(self, registry_id: str):
                return ()

        source = Source()
        self.assertIsInstance(
            source,
            canonical_v1.RegistrySignerSourceTrustSourceV1,
        )
        self.assertIsInstance(
            source,
            legacy_v1.RegistrySignerSourceTrustSourceV1,
        )

    def test_migration_introduces_no_authority_boolean(self):
        serialized = CANONICAL_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "current_admission_allowed",
            "live_order_allowed",
            "paper_authorized",
            "runtime_gate_activation_allowed",
            "writer_allowed",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()