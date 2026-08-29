from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path
import unittest

from exchange_terminal.application.ports import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1 as canonical_v1,
)
from exchange_terminal.interfaces import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider as legacy_v1,
)


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "exchange_terminal" / "application"
CANONICAL_PATH = ROOT / "exchange_terminal/application/ports/strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1.py"
LEGACY_PATH = ROOT / "exchange_terminal/interfaces/strategy_correlation_incumbent_snapshot_replay_cursor_provider.py"
PREREGISTRATION_PATH = ROOT / "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1.py"
CANONICAL_MODULE = "exchange_terminal.application.ports.strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1"
LEGACY_MODULE = "exchange_terminal.interfaces.strategy_correlation_incumbent_snapshot_replay_cursor_provider"
CANONICAL_SHA256 = "210f897078503e2a0e7a95d1f3c3a531d8331fe59b82684fb6f2fc14f01c09c5"
LEGACY_SHIM_SHA256 = "a855a29f27fa4c163037726575c55302b59398d63a5c41970bc99e322da25721"
HASH_CLOSURE = {
    "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1.py": "42e1e2a88839b616ac2ebc9f7851ae8266172ade6b1a5a26320635ec90111212",
    "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_registration_v1.py": "c83f9f06cdd60ff28021664699d486e86fc5e4881b45d8899375a7a76c4d4950",
    "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_signed_source_v1.py": "154152491e419f4f41d273b83b44be6d51994c58bdfe2c7d4727b48d4c521d94",
    "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_clock_attestation_binding_v1.py": "620ed3ec9805cf3c73f87bbc9da5b672cb4ceff65e7e9b0ed8ae7f43be7e0f05",
    "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_command_binding_v1.py": "b2cefebf21b415beef5a67127f25efbcfc22d941fa92df4ee9928376c566f513",
    "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1.py": "867dd73a4cbb8219654265f21f3fff70d3031f18f23057fb3b69ebd6afc71bbb",
    "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_signed_registration_v1.py": "64cdf02d9249088dd917ae935b3ef17c4c84d412bef1d1dafced58d8601bb73b",
    "exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_registration_challenge_signed_source_v1.py": "3eb90909dffe275053048743f7ad5e9567df7fc590b5040d0ebb214fbc16e1ca",
    "exchange_terminal/application/challenge_consumption_provider_registration_handoff_v1.py": "593eb672b93823f1b6d859577758b6040656b65e000b3736fea33297a0a73ab1",
    "exchange_terminal/application/challenge_consumption_provider_registration_clock_binding_v1.py": "f57ee0863658e80a751d29884c77672441d82149109e488975e756314b3361b9",
    "exchange_terminal/application/challenge_consumption_provider_bootstrap_topology_v1.py": "ac39291a0f0e62bb47b42163cbf78ddd712f290ca1061b6ef9784700eb0c7e1d",
    "exchange_terminal/application/challenge_consumption_provider_threshold_genesis_admission_v1.py": "9dba83afda64034335a37e704d000fb1d083c6f617f6bea4211222e45afc553d",
    "exchange_terminal/application/challenge_consumption_provider_genesis_replay_reservation_preregistration_v1.py": "dfdedb55e1e0d89e25436d64a9597fbf09c359db63101efe457425698075d15e",
    "exchange_terminal/application/challenge_consumption_provider_genesis_replay_reservation_signed_registration_v1.py": "d60e69e27cd0c746f82e368420c617e2683cb31fd4a36a701ef366705563471c",
    "exchange_terminal/application/genesis_replay_reservation_provider_registration_challenge_signed_source_v1.py": "d01e45afd996d4c32e0f4267d649378dfba310902c39f5f0bf67092ee773b8b4",
    "exchange_terminal/application/genesis_replay_reservation_provider_registration_handoff_v1.py": "e64301444c6e6dede1d6948a5aeaac1326a5c97749d6f8ebe744e4c7f8a3a1c6",
    "exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_binding_v1.py": "60f01be568b0ef978819c75dbb39146c5b0b06cd2e351f2de2fac9ab3c54b94b",
    "exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_trust_bootstrap_topology_v1.py": "948ddd4c9889376fd7262cc51fb952aa9230944f51959ede081f10d7426f1bde",
    "exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_trust_threshold_genesis_admission_v1.py": "693966381aec8b79d03ee13a9f0e6070dbf7657802e93b650cae61eabf2a098f",
    "exchange_terminal/application/genesis_replay_reservation_commitment_semantic_profile_quarantine_v1.py": "8585f343c43586faf6dd26eabd1a1f8925e2506579ca640f1164c5881a13a1cd",
    "tests/test_exchange_terminal_layer_dependency_audit_v2.py": "1c18895e504491e33139c2be7a85be80eac1f92c18eedff2c14a71b23db0cbbc",
    "tests/test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1.py": "2e23aa9360bbdc00a519254a6a82b08a441eb8cd10a2211f20f78ccd473c9949",
    "tests/test_challenge_consumption_provider_genesis_replay_reservation_application_port_migration_v1.py": "21893372d2b85ddc84e8b9b96608eb583303d0c51efe8e7b82632b4903639742",
    "tests/test_anti_replay_registry_v2_application_port_migration_v1.py": "6618d47eb17f06fd9be94f683220fa598d2354cd35c8efd6630c2265a4da051c",
    "tests/test_challenge_consumption_provider_application_port_migration_v1.py": "3ccb73e9822e43d2d81cd009cd7e995f68c6a85c4a15de50148c836cab779692",
}
EXPORTED_SYMBOLS = (
    "COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION",
    "COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION",
    "ReplayCursorCompareAndAdvanceCommandV1",
    "ReplayCursorCompareAndAdvanceResultV1",
    "ReplayCursorProviderOutcomeV1",
    "ReplayCursorProviderPortV1",
    "build_replay_cursor_compare_and_advance_command_v1",
)


def _sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _import_targets(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
        elif isinstance(node, ast.Import):
            targets.extend(alias.name for alias in node.names)
    return targets


class ReplayCursorProviderApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_canonical_port_preserves_exact_implementation_bytes(self) -> None:
        self.assertEqual(_sha256(CANONICAL_PATH), CANONICAL_SHA256)
        self.assertEqual(
            canonical_v1.COMPARE_AND_ADVANCE_COMMAND_SCHEMA_VERSION,
            "incumbent-snapshot-replay-cursor-compare-and-advance-command-v1",
        )
        self.assertEqual(
            canonical_v1.COMPARE_AND_ADVANCE_RESULT_SCHEMA_VERSION,
            "incumbent-snapshot-replay-cursor-compare-and-advance-result-v1",
        )
        self.assertFalse(
            [
                target
                for target in _import_targets(CANONICAL_PATH)
                if target.startswith("exchange_terminal.interfaces")
            ]
        )

    def test_legacy_module_is_an_identity_preserving_shim(self) -> None:
        self.assertEqual(_sha256(LEGACY_PATH), LEGACY_SHIM_SHA256)
        self.assertEqual(tuple(canonical_v1.__all__), EXPORTED_SYMBOLS)
        self.assertEqual(tuple(legacy_v1.__all__), EXPORTED_SYMBOLS)
        for name in EXPORTED_SYMBOLS:
            with self.subTest(name=name):
                self.assertIs(getattr(legacy_v1, name), getattr(canonical_v1, name))
        tree = ast.parse(LEGACY_PATH.read_text(encoding="utf-8"))
        self.assertFalse(
            [
                node
                for node in ast.walk(tree)
                if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            ]
        )

    def test_preregistration_consumer_uses_canonical_port(self) -> None:
        targets = _import_targets(PREREGISTRATION_PATH)
        self.assertIn(CANONICAL_MODULE, targets)
        self.assertNotIn(LEGACY_MODULE, targets)
        self.assertEqual(
            canonical_v1.__file__ and _sha256(Path(canonical_v1.__file__)),
            canonical_v1.__file__ and canonical_v1.__file__ and CANONICAL_SHA256,
        )

    def test_application_interfaces_submodule_edges_are_zero(self)->None:
        edges=[]
        for path in sorted(APPLICATION_ROOT.rglob("*.py")):
            for target in _import_targets(path):
                if target.startswith("exchange_terminal.interfaces."):edges.append((path.relative_to(APPLICATION_ROOT).as_posix(),target))
        self.assertEqual(edges,[])

    def test_hash_seal_closure_is_exact(self) -> None:
        for rel, expected_hash in HASH_CLOSURE.items():
            with self.subTest(path=rel):
                self.assertEqual(_sha256(ROOT / rel), expected_hash)

    def test_canonical_port_has_no_runtime_or_authority_side_effect(self) -> None:
        source = CANONICAL_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "threading",
            "sqlite3",
            "open(",
            "requests.",
            "urllib.",
            "socket.",
            "register_route(",
            "write_current_pointer(",
            "paper_authorized = True",
            "live_order_allowed = True",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
