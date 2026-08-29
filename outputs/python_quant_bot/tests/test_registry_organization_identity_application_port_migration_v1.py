from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest

from exchange_terminal.application import (
    anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1 as verification_v1,
)
from exchange_terminal.application import (
    anti_replay_registry_signer_source_trust_preregistration_v1 as signer_trust_v1,
)
from exchange_terminal.application.ports import (
    registry_organization_identity_v1 as canonical_v1,
)
from exchange_terminal.interfaces import registry_organization_identity as legacy_v1
from exchange_terminal.interfaces import registry_signer_source_trust as source_trust_v1


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "exchange_terminal" / "application"
CANONICAL_PATH = (
    APPLICATION_ROOT / "ports" / "registry_organization_identity_v1.py"
)
LEGACY_PATH = (
    ROOT / "exchange_terminal" / "interfaces" / "registry_organization_identity.py"
)
CANONICAL_MODULE = (
    "exchange_terminal.application.ports.registry_organization_identity_v1"
)
LEGACY_MODULE = "exchange_terminal.interfaces.registry_organization_identity"
CANONICAL_SHA256 = (
    "df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f"
)
CONSUMER_PATHS = (
    APPLICATION_ROOT
    / "anti_replay_registry_organization_identity_evidence_bundle_evaluation_v1.py",
    APPLICATION_ROOT
    / "anti_replay_registry_organization_identity_evidence_bundle_verification_envelope_v1.py",
    APPLICATION_ROOT
    / "anti_replay_registry_organization_identity_intake_preregistration_v1.py",
    APPLICATION_ROOT
    / "anti_replay_registry_signer_source_trust_preregistration_v1.py",
)
PUBLIC_NAMES = (
    "EVIDENCE_REFERENCE_SCHEMA_VERSION",
    "SIGNATURE_ALGORITHM",
    "RegistryOrganizationIdentityEvidenceKindV1",
    "RegistryOrganizationIdentityEvidenceReferenceV1",
    "RegistryOrganizationIdentityEvidenceSourceV1",
    "expected_evidence_schema_v1",
    "expected_signer_role_v1",
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


class RegistryOrganizationIdentityApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_canonical_port_preserves_the_pre_migration_implementation_bytes(self):
        self.assertEqual(_sha256(CANONICAL_PATH), CANONICAL_SHA256)

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

    def test_legacy_constructed_reference_is_a_canonical_reference(self):
        kind = (
            legacy_v1.RegistryOrganizationIdentityEvidenceKindV1
            .ORGANIZATION_REGISTRY_ATTESTATION
        )
        reference = legacy_v1.RegistryOrganizationIdentityEvidenceReferenceV1(
            kind=kind,
            evidence_schema_version=legacy_v1.expected_evidence_schema_v1(kind),
            artifact_sha256="a" * 64,
            signer_role=legacy_v1.expected_signer_role_v1(kind),
            signer_public_key_spki_sha256="b" * 64,
            subject_registry_id="registry.example",
            subject_public_key_spki_sha256="c" * 64,
            issued_at_ms=1_000,
            expires_at_ms=2_000,
        )
        self.assertIsInstance(
            reference,
            canonical_v1.RegistryOrganizationIdentityEvidenceReferenceV1,
        )

    def test_reference_validation_remains_fail_closed_through_legacy_path(self):
        kind = (
            legacy_v1.RegistryOrganizationIdentityEvidenceKindV1
            .DOMAIN_CONTROL_ATTESTATION
        )
        with self.assertRaisesRegex(ValueError, "issued_at_ms"):
            legacy_v1.RegistryOrganizationIdentityEvidenceReferenceV1(
                kind=kind,
                evidence_schema_version=legacy_v1.expected_evidence_schema_v1(kind),
                artifact_sha256="a" * 64,
                signer_role=legacy_v1.expected_signer_role_v1(kind),
                signer_public_key_spki_sha256="b" * 64,
                subject_registry_id="registry.example",
                subject_public_key_spki_sha256="c" * 64,
                issued_at_ms=True,
                expires_at_ms=2_000,
            )

    def test_canonical_port_has_no_exchange_terminal_layer_dependency(self):
        targets = _import_targets(CANONICAL_PATH)
        self.assertFalse(
            [target for target in targets if target.startswith("exchange_terminal.")]
        )

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

    def test_all_four_application_consumers_use_the_canonical_port(self):
        for path in CONSUMER_PATHS:
            targets = _import_targets(path)
            with self.subTest(path=path.name):
                self.assertIn(CANONICAL_MODULE, targets)
                self.assertNotIn(LEGACY_MODULE, targets)

    def test_application_to_interfaces_import_statements_do_not_regress_above_eight(self):
        edges: list[tuple[str, str]] = []
        for path in sorted(APPLICATION_ROOT.rglob("*.py")):
            for target in _import_targets(path):
                if target.startswith("exchange_terminal.interfaces."):
                    edges.append((path.relative_to(APPLICATION_ROOT).as_posix(), target))
        self.assertLessEqual(len(edges), 8)
        self.assertFalse([edge for edge in edges if edge[1] == LEGACY_MODULE])

    def test_downstream_hash_pins_now_describe_the_canonical_port_bytes(self):
        self.assertEqual(
            verification_v1.EVIDENCE_REFERENCE_IMPLEMENTATION_SHA256,
            CANONICAL_SHA256,
        )
        self.assertEqual(
            signer_trust_v1.ORGANIZATION_IDENTITY_REFERENCE_IMPLEMENTATION_SHA256,
            CANONICAL_SHA256,
        )

    def test_existing_interface_consumer_receives_the_canonical_enum_identity(self):
        self.assertIs(
            source_trust_v1.RegistryOrganizationIdentityEvidenceKindV1,
            canonical_v1.RegistryOrganizationIdentityEvidenceKindV1,
        )


if __name__ == "__main__":
    unittest.main()