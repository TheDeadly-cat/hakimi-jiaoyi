from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.application.ports import anti_replay_registry_v2 as anti_replay_v2
from exchange_terminal.application.ports import witness_ownership_key_revocation_snapshot_publication_provider_v1 as publication_v1
from exchange_terminal.application.ports import witness_ownership_snapshot_storage_harness_driver_v1 as harness_v1
from exchange_terminal.application.ports import witness_ownership_state_store_v1 as state_v1
from exchange_terminal.interfaces import witness_ownership_key_revocation_snapshot_publication_provider_v1 as publication_legacy
from exchange_terminal.interfaces import witness_ownership_snapshot_storage_harness_driver_v1 as harness_legacy
from exchange_terminal.interfaces import witness_ownership_state_store as state_legacy

ROOT=Path(__file__).resolve().parents[1]
APPLICATION_ROOT=ROOT / "exchange_terminal" / "application"
STATE_CANONICAL=ROOT / "exchange_terminal/application/ports/witness_ownership_state_store_v1.py"
PUBLICATION_CANONICAL=ROOT / "exchange_terminal/application/ports/witness_ownership_key_revocation_snapshot_publication_provider_v1.py"
HARNESS_CANONICAL=ROOT / "exchange_terminal/application/ports/witness_ownership_snapshot_storage_harness_driver_v1.py"
STATE_LEGACY=ROOT / "exchange_terminal/interfaces/witness_ownership_state_store.py"
PUBLICATION_LEGACY=ROOT / "exchange_terminal/interfaces/witness_ownership_key_revocation_snapshot_publication_provider_v1.py"
HARNESS_LEGACY=ROOT / "exchange_terminal/interfaces/witness_ownership_snapshot_storage_harness_driver_v1.py"
CONSUMER_PATHS=(
    ROOT / "exchange_terminal/application/witness_ownership_state_service.py",
    ROOT / "exchange_terminal/application/witness_ownership_state_provider_preregistration_v1.py",
    ROOT / "exchange_terminal/application/witness_ownership_state_signed_receipt_v1.py",
    ROOT / "exchange_terminal/application/witness_ownership_key_revocation_snapshot_publication_consumer_v1.py",
    ROOT / "exchange_terminal/application/witness_ownership_key_revocation_snapshot_isolated_storage_harness_v1.py",
)
CANONICAL_HASHES={
    STATE_CANONICAL: "36a43ef91efcc472664c5b4bdc8519046532eb5a2d7c36fe398e9ac6262f72e8",
    PUBLICATION_CANONICAL: "433404433d04a7c5733084a253eaf1394433618e13eaf51fff2914c86e9617dd",
    HARNESS_CANONICAL: "d4500c42991d7f5a6529782a7d234cb12012c2995215df772383005f873f7e69",
}
LEGACY_HASHES={
    STATE_LEGACY: "3fbdd877dc7f41786e9b1c4539803b2cd39ea7db4f1732b180b2aaa6a5664029",
    PUBLICATION_LEGACY: "03e50abcc00dd899845f28210da7bcc1b29d02ac2898ddc765379fe52c6e2f0d",
    HARNESS_LEGACY: "7e77abedfa9380e6fc3360ed0374b2200e544d95305c25f4effdf37bcff43b9e",
}
HASH_CLOSURE={
    "exchange_terminal/application/witness_ownership_state_service.py": "4b3c711e614416ce78bb62bd9cc28dce077f3b6e99fb20891be295557d40178c",
    "exchange_terminal/application/witness_ownership_state_provider_preregistration_v1.py": "081cf9dfae66918f6e5e1cf4fd8f9d7e7c438aff01e1b465726a86d8aee47b2d",
    "exchange_terminal/application/witness_ownership_state_signed_receipt_v1.py": "d0236dafac1f5c81170e97b1e58b4459c0b673814205242deb9adeada12d072d",
    "exchange_terminal/application/witness_ownership_key_revocation_snapshot_publication_consumer_v1.py": "b94371a927983588aecd678ba40ee5ca4c2d5e9678ea8f5f6c4420808dd77d13",
    "exchange_terminal/application/witness_ownership_state_provider_identity_source_adapter_preregistration_v1.py": "d087684a6a7e64bd2acf6e213144083ad30e5b88bf091f9f56edb942465f4374",
    "exchange_terminal/application/witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1.py": "04afd17f55c4a287852f727aadf771772d6770e0f1f9db8ebd98040bb95bb52f",
    "exchange_terminal/application/witness_ownership_key_revocation_snapshot_storage_evidence_quorum_v1.py": "7111362ca0c1fa914bf6ea65a358347e6889e2f63184a520f5cdf0cdc37665a3",
    "exchange_terminal/application/witness_ownership_snapshot_storage_observer_identity_admission_v1.py": "a285225bc97cc61a5405d7472e0439295b04ca1442e0a9bcf8039a3e0c648578",
    "exchange_terminal/application/witness_ownership_key_revocation_snapshot_isolated_storage_harness_v1.py": "a0212ece7ffe67b9f2dc5515e3effbbdebc8e5512dd1e9b32eadaae41ef80811",
    "exchange_terminal/application/witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1.py": "4c47934b9945626b1665c6e61f873123a45ddc935064e2084897ece7eb48d639",
    "exchange_terminal/application/witness_ownership_snapshot_storage_persistence_admission_decision_v1.py": "eb366b03855fc37b11fa77615aee90c4ef3a1e1ec38357f2bf152ba4409f2467",
    "exchange_terminal/application/witness_ownership_state_provider_conformance_plan_v1.py": "410a2d54f0677bf1e382341afbeac95ecb980fcd3370bc7344d7d923aaa05f0e",
    "tests/test_exchange_terminal_layer_dependency_audit_v2.py": "1c18895e504491e33139c2be7a85be80eac1f92c18eedff2c14a71b23db0cbbc",
    "tests/test_challenge_consumption_provider_genesis_replay_reservation_application_port_migration_v1.py": "21893372d2b85ddc84e8b9b96608eb583303d0c51efe8e7b82632b4903639742",
    "tests/test_anti_replay_registry_v2_application_port_migration_v1.py": "6618d47eb17f06fd9be94f683220fa598d2354cd35c8efd6630c2265a4da051c",
    "tests/test_challenge_consumption_provider_application_port_migration_v1.py": "3ccb73e9822e43d2d81cd009cd7e995f68c6a85c4a15de50148c836cab779692",
    "tests/test_replay_cursor_provider_application_port_migration_v1.py": "37288834b46d79eb38fe4c729ea231f87784b3271e98479a1776a8ae58181acc",
}
STATE_EXPORTS=(
    "COMMAND_SCHEMA_VERSION",
    "RECEIPT_CLAIM_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "WITNESS_OWNERSHIP_NAMESPACE",
    "WitnessOwnershipCompareConsumeAndAdvanceCommandV1",
    "WitnessOwnershipCompareConsumeAndAdvanceResultV1",
    "WitnessOwnershipProviderOutcomeV1",
    "WitnessOwnershipStateProviderPortV1",
    "build_witness_ownership_compare_consume_and_advance_command_v1",
    "build_witness_ownership_compare_consume_and_advance_result_v1",
    "build_witness_ownership_consumption_key_v1",
    "build_witness_ownership_state_provider_receipt_claim_v1",
    "verify_witness_ownership_compare_consume_and_advance_result_v1",
)
PUBLICATION_EXPORTS=(
    "WitnessOwnershipKeyRevocationSnapshotPublicationHeadV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationManifestV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationProviderV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationReceiptV1",
    "WitnessOwnershipKeyRevocationSnapshotPublicationRequestV1",
)
HARNESS_EXPORTS=(
    "WitnessOwnershipSnapshotStorageHarnessDriverV1",
    "WitnessOwnershipSnapshotStorageHarnessScenarioCommandV1",
    "WitnessOwnershipSnapshotStorageHarnessScenarioResultV1",
)


def _sha(path:Path)->str:
    return sha256(path.read_bytes()).hexdigest()


def _imports(path:Path)->list[tuple[str,str]]:
    tree=ast.parse(path.read_text(encoding="utf-8"),filename=str(path))
    values=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.ImportFrom) and node.module:
            for alias in node.names:
                values.append((node.module,alias.name))
        elif isinstance(node,ast.Import):
            for alias in node.names:
                values.append((alias.name,alias.name))
    return values


class WitnessOwnershipPortsApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_canonical_hashes_and_anti_replay_binding_are_exact(self)->None:
        for path,expected in CANONICAL_HASHES.items():
            with self.subTest(path=str(path)):
                self.assertEqual(_sha(path),expected)
                self.assertFalse([m for m,_ in _imports(path) if m.startswith("exchange_terminal.interfaces")])
        self.assertIn(("exchange_terminal.application.ports.anti_replay_registry_v2","build_anti_replay_consumption_key_v2"),_imports(STATE_CANONICAL))
        self.assertIs(state_v1.build_anti_replay_consumption_key_v2,anti_replay_v2.build_anti_replay_consumption_key_v2)

    def test_legacy_modules_are_identity_only_shims(self)->None:
        cases=(
            (state_v1,state_legacy,STATE_EXPORTS),
            (publication_v1,publication_legacy,PUBLICATION_EXPORTS),
            (harness_v1,harness_legacy,HARNESS_EXPORTS),
        )
        for canonical,legacy,exports in cases:
            with self.subTest(module=legacy.__name__):
                self.assertEqual(tuple(canonical.__all__),exports)
                self.assertEqual(tuple(legacy.__all__),exports)
                for name in exports:
                    self.assertIs(getattr(legacy,name),getattr(canonical,name))
                tree=ast.parse(Path(legacy.__file__).read_text(encoding="utf-8"))
                self.assertFalse([n for n in ast.walk(tree) if isinstance(n,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef))])
        for path,expected in LEGACY_HASHES.items():
            self.assertEqual(_sha(path),expected)

    def test_all_five_consumers_use_application_ports(self)->None:
        for path in CONSUMER_PATHS:
            imports=_imports(path)
            with self.subTest(path=str(path)):
                self.assertTrue(any(module=="exchange_terminal.application.ports" for module,_ in imports))
                self.assertFalse([module for module,_ in imports if module.startswith("exchange_terminal.interfaces")])

    def test_application_interfaces_edges_are_zero(self)->None:
        edges=set()
        for path in sorted(APPLICATION_ROOT.rglob("*.py")):
            for module,name in _imports(path):
                if module=="exchange_terminal.interfaces":target=f"{module}.{name}"
                elif module.startswith("exchange_terminal.interfaces."):target=module
                else:continue
                edges.add((path.relative_to(APPLICATION_ROOT).as_posix(),target))
        self.assertEqual(edges,set())

    def test_static_provenance_closure_is_exact(self)->None:
        for rel,expected in HASH_CLOSURE.items():
            with self.subTest(path=rel): self.assertEqual(_sha(ROOT/rel),expected)

    def test_canonical_ports_have_no_runtime_or_authority_side_effects(self)->None:
        forbidden=("open(","sqlite3","requests.","urllib.","socket.","subprocess","threading","register_route(","write_current_pointer(","paper_authorized = True","live_order_allowed = True")
        for path in CANONICAL_HASHES:
            source=path.read_text(encoding="utf-8")
            with self.subTest(path=str(path)):
                for token in forbidden: self.assertNotIn(token,source)


if __name__=="__main__":
    unittest.main()
