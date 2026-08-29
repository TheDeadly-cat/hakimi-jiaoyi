from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest

from exchange_terminal.application.ports import anti_replay_registry_v1 as canonical_v1
from exchange_terminal.application.ports import anti_replay_registry_v2 as canonical_v2
from exchange_terminal.interfaces import anti_replay_registry_v2 as legacy_v2


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "exchange_terminal" / "application"
CANONICAL_V1_PATH = APPLICATION_ROOT / "ports" / "anti_replay_registry_v1.py"
CANONICAL_V2_PATH = APPLICATION_ROOT / "ports" / "anti_replay_registry_v2.py"
LEGACY_V2_PATH = ROOT / "exchange_terminal" / "interfaces" / "anti_replay_registry_v2.py"
NAMESPACE_PATH = APPLICATION_ROOT / "source_baseline_nonce_anti_replay_namespace_preregistration_v1.py"
PLAN_PATH = APPLICATION_ROOT / "source_baseline_nonce_anti_replay_provider_conformance_plan_v2.py"
ADR0435_TEST_PATH = ROOT / "tests" / "test_anti_replay_registry_application_port_migration_v1.py"
ADR0436_TEST_PATH = ROOT / "tests" / "test_challenge_consumption_provider_genesis_replay_reservation_application_port_migration_v1.py"
ARCHITECTURE_TEST_PATH = ROOT / "tests" / "test_exchange_terminal_layer_dependency_audit_v2.py"
CANONICAL_V1_MODULE = "exchange_terminal.application.ports.anti_replay_registry_v1"
CANONICAL_V2_MODULE = "exchange_terminal.application.ports.anti_replay_registry_v2"
LEGACY_V2_MODULE = "exchange_terminal.interfaces.anti_replay_registry_v2"
CANONICAL_V1_SHA256 = "5eed523c3665e687c6d2f202afcea5cc93bcdee3ef4ee942a7d4f76364f380a0"
CANONICAL_V2_SHA256 = "ff5d027d7b8352455be7792b495076070347de67534b736ff46cc1872f927f21"
LEGACY_V2_SHIM_SHA256 = "5b4656f4a06509491ae69f008fb57865d1a1acf7b93f20a4dd0f89f121f1cc38"
ADR0435_TEST_SHA256 = "f96d05ea8e9e7ed5093739531704c40f1675dacff685629ce376f1bba87aa58c"
ADR0436_TEST_SHA256 = "21893372d2b85ddc84e8b9b96608eb583303d0c51efe8e7b82632b4903639742"
ARCHITECTURE_TEST_SHA256 = "1c18895e504491e33139c2be7a85be80eac1f92c18eedff2c14a71b23db0cbbc"
CURRENT_PROVENANCE_CLOSURE_SHA256 = {
    'exchange_terminal/application/source_baseline_nonce_anti_replay_namespace_preregistration_v1.py': 'c716d91765aba195bb4f65be0d2fd6b9cc6e768ddcb544a2f0633eb894dc2e29',
    'exchange_terminal/application/source_baseline_nonce_anti_replay_provider_conformance_plan_v2.py': 'cb48118f7791f7eb466d8fdc8da3235d568fe2a1a61def7c14df7709c8ad5792',
}
STALE_PROVENANCE_SHA256 = (
    '0884422240ad68c6a3c472dece18ebfe7deb0976309c7747900e6141e5f2b105',
    '6b579fbd4569dbfab397c4411fa23bc4adaf535c1fd5913052017e21fe5f2104',
    '57a4ca1e3c4b7bd9145dd1e86820671f85f99f1548097e1522827b46a1ea1c31',
)
PUBLIC_SYMBOLS = (
    'AntiReplayCompareAndConsumeCommandV2',
    'AntiReplayCompareAndConsumeResultV2',
    'AntiReplayRegistryOutcomeV1',
    'AntiReplayRegistryPortV2',
    'COMMAND_SCHEMA_VERSION',
    'REQUEST_SCHEMA_VERSION',
    'RESULT_SCHEMA_VERSION',
    'STATIC_FINGERPRINT',
    'build_anti_replay_compare_and_consume_request_v2',
    'build_anti_replay_consumption_key_v2',
    'verify_anti_replay_compare_and_consume_request_v2',
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _import_targets(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return tuple(targets)


class AntiReplayRegistryV2ApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_canonical_v2_uses_canonical_v1_without_interfaces_dependency(self):
        self.assertEqual(_sha256(CANONICAL_V1_PATH), CANONICAL_V1_SHA256)
        self.assertEqual(_sha256(CANONICAL_V2_PATH), CANONICAL_V2_SHA256)
        targets = _import_targets(CANONICAL_V2_PATH)
        self.assertIn(CANONICAL_V1_MODULE, targets)
        self.assertFalse([target for target in targets if target.startswith("exchange_terminal.interfaces")])

    def test_legacy_v2_shim_is_exact_and_reexports_identical_objects(self):
        self.assertEqual(_sha256(LEGACY_V2_PATH), LEGACY_V2_SHIM_SHA256)
        self.assertEqual(legacy_v2.__all__, PUBLIC_SYMBOLS)
        for symbol in PUBLIC_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(legacy_v2, symbol), getattr(canonical_v2, symbol))

    def test_v2_preserves_canonical_v1_outcome_identity(self):
        self.assertIs(canonical_v2.AntiReplayRegistryOutcomeV1, canonical_v1.AntiReplayRegistryOutcomeV1)
        self.assertIs(legacy_v2.AntiReplayRegistryOutcomeV1, canonical_v1.AntiReplayRegistryOutcomeV1)

    def test_application_consumers_use_canonical_v2(self):
        for path in (NAMESPACE_PATH, PLAN_PATH):
            targets = _import_targets(path)
            with self.subTest(path=path.name):
                self.assertIn(CANONICAL_V2_MODULE, targets)
                self.assertNotIn(LEGACY_V2_MODULE, targets)

    def test_direct_application_to_interfaces_submodule_imports_remain_at_most_three(self):
        edges: list[tuple[str, str]] = []
        for path in sorted(APPLICATION_ROOT.rglob("*.py")):
            for target in _import_targets(path):
                if target.startswith("exchange_terminal.interfaces."):
                    edges.append((path.relative_to(APPLICATION_ROOT).as_posix(), target))
        self.assertLessEqual(len(edges), 3)
        self.assertFalse([edge for edge in edges if edge[1] == LEGACY_V2_MODULE])

    def test_v2_schema_and_fingerprint_are_unchanged(self):
        self.assertEqual(canonical_v2.COMMAND_SCHEMA_VERSION, "anti-replay-compare-and-consume-command-v2")
        self.assertEqual(canonical_v2.REQUEST_SCHEMA_VERSION, "anti-replay-compare-and-consume-request-v2")
        self.assertEqual(canonical_v2.RESULT_SCHEMA_VERSION, "anti-replay-compare-and-consume-result-v2")
        self.assertEqual(canonical_v2.STATIC_FINGERPRINT, "20260823-anti-replay-registry-port-v2-lock-1")

    def test_provenance_closure_is_current_and_rejects_predecessors(self):
        for relative, expected_hash in CURRENT_PROVENANCE_CLOSURE_SHA256.items():
            path = ROOT / relative
            with self.subTest(relative=relative):
                self.assertEqual(_sha256(path), expected_hash)
                source = path.read_text(encoding="utf-8")
                for stale_hash in STALE_PROVENANCE_SHA256:
                    self.assertNotIn(stale_hash, source)

    def test_predecessor_and_architecture_contracts_are_current(self):
        self.assertEqual(_sha256(ADR0435_TEST_PATH), ADR0435_TEST_SHA256)
        self.assertEqual(_sha256(ADR0436_TEST_PATH), ADR0436_TEST_SHA256)
        self.assertEqual(_sha256(ARCHITECTURE_TEST_PATH), ARCHITECTURE_TEST_SHA256)

    def test_migration_grants_no_execution_authority(self):
        source = CANONICAL_V2_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "live_order_allowed",
            "paper_authorized",
            "runtime_gate_activation_allowed",
            "publication_allowed",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
