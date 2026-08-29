from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest

from exchange_terminal.application.ports import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_v1 as canonical_v1,
)
from exchange_terminal.interfaces import (
    strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider as legacy_v1,
)


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "exchange_terminal" / "application"
CANONICAL_PATH = APPLICATION_ROOT / "ports" / "strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_v1.py"
LEGACY_PATH = ROOT / "exchange_terminal" / "interfaces" / "strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider.py"
COMMAND_BINDING_PATH = APPLICATION_ROOT / "strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_command_binding_v1.py"
PREREGISTRATION_PATH = APPLICATION_ROOT / "strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1.py"
ADR0436_TEST_PATH = ROOT / "tests" / "test_challenge_consumption_provider_genesis_replay_reservation_application_port_migration_v1.py"
ADR0437_TEST_PATH = ROOT / "tests" / "test_anti_replay_registry_v2_application_port_migration_v1.py"
ARCHITECTURE_TEST_PATH = ROOT / "tests" / "test_exchange_terminal_layer_dependency_audit_v2.py"
COMPATIBILITY_TEST_PATH = ROOT / "tests" / "test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1.py"
CANONICAL_PACKAGE = "exchange_terminal.application.ports"
CANONICAL_MODULE = "exchange_terminal.application.ports.strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_v1"
LEGACY_PACKAGE = "exchange_terminal.interfaces"
LEGACY_MODULE = "exchange_terminal.interfaces.strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider"
CANONICAL_SHA256 = "01c3e4aa2684352764bfbd30cf9ab9c377d300fd652a5f96928eecaaa608fa48"
LEGACY_SHIM_SHA256 = "39df203f82f27cd16082efe19e9f15c48626b35d235ee941e9ed1a990a6b8160"
ADR0436_TEST_SHA256 = "21893372d2b85ddc84e8b9b96608eb583303d0c51efe8e7b82632b4903639742"
ADR0437_TEST_SHA256 = "6618d47eb17f06fd9be94f683220fa598d2354cd35c8efd6630c2265a4da051c"
ARCHITECTURE_TEST_SHA256 = "1c18895e504491e33139c2be7a85be80eac1f92c18eedff2c14a71b23db0cbbc"
COMPATIBILITY_TEST_SHA256 = "014463fd92f2251021f349424ea5b963bc1da40ea0bade55b61c120172989943"
CURRENT_PROVENANCE_CLOSURE_SHA256 = {
    'exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_command_binding_v1.py': 'b2cefebf21b415beef5a67127f25efbcfc22d941fa92df4ee9928376c566f513',
    'exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1.py': '867dd73a4cbb8219654265f21f3fff70d3031f18f23057fb3b69ebd6afc71bbb',
    'exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_signed_registration_v1.py': '64cdf02d9249088dd917ae935b3ef17c4c84d412bef1d1dafced58d8601bb73b',
    'exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_registration_challenge_signed_source_v1.py': '3eb90909dffe275053048743f7ad5e9567df7fc590b5040d0ebb214fbc16e1ca',
    'exchange_terminal/application/challenge_consumption_provider_registration_handoff_v1.py': '593eb672b93823f1b6d859577758b6040656b65e000b3736fea33297a0a73ab1',
    'exchange_terminal/application/challenge_consumption_provider_registration_clock_binding_v1.py': 'f57ee0863658e80a751d29884c77672441d82149109e488975e756314b3361b9',
    'exchange_terminal/application/challenge_consumption_provider_bootstrap_topology_v1.py': 'ac39291a0f0e62bb47b42163cbf78ddd712f290ca1061b6ef9784700eb0c7e1d',
    'exchange_terminal/application/challenge_consumption_provider_threshold_genesis_admission_v1.py': '9dba83afda64034335a37e704d000fb1d083c6f617f6bea4211222e45afc553d',
    'exchange_terminal/application/challenge_consumption_provider_genesis_replay_reservation_preregistration_v1.py': 'dfdedb55e1e0d89e25436d64a9597fbf09c359db63101efe457425698075d15e',
    'exchange_terminal/application/challenge_consumption_provider_genesis_replay_reservation_signed_registration_v1.py': 'd60e69e27cd0c746f82e368420c617e2683cb31fd4a36a701ef366705563471c',
    'exchange_terminal/application/genesis_replay_reservation_provider_registration_challenge_signed_source_v1.py': 'd01e45afd996d4c32e0f4267d649378dfba310902c39f5f0bf67092ee773b8b4',
    'exchange_terminal/application/genesis_replay_reservation_provider_registration_handoff_v1.py': 'e64301444c6e6dede1d6948a5aeaac1326a5c97749d6f8ebe744e4c7f8a3a1c6',
    'exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_binding_v1.py': '60f01be568b0ef978819c75dbb39146c5b0b06cd2e351f2de2fac9ab3c54b94b',
    'exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_trust_bootstrap_topology_v1.py': '948ddd4c9889376fd7262cc51fb952aa9230944f51959ede081f10d7426f1bde',
    'exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_trust_threshold_genesis_admission_v1.py': '693966381aec8b79d03ee13a9f0e6070dbf7657802e93b650cae61eabf2a098f',
    'exchange_terminal/application/genesis_replay_reservation_commitment_semantic_profile_quarantine_v1.py': '8585f343c43586faf6dd26eabd1a1f8925e2506579ca640f1164c5881a13a1cd',
}
STALE_PROVENANCE_SHA256 = (
    '172157ff1776e67704a3d91dca1398f2427fc0223a6fddc0506ba26cf180731e',
    '1b7f212e07f5813fdef4c14541a427ea1cebebb7c86841376d6d6215cc32da54',
    '3a9f34f8a9f59d708e5fd73da527489affb5560624c11a315d8291636269c0e2',
    '4e3ea7637734c9a7393ff1ab1ed668bd26710430511d72a1a5c54b702b43c145',
    '741d4b44ac374fcf05e4daddfb142e5e4efb510ffec8eefdbb60e62487307313',
    '84ae2964440b7e135d9b955d5151bfcb17348fb30f72b0accc7fe23e8bc13052',
    '8e64081ab6d26e5678f4b86b80a28be1e2bbc7ba0d035840f4f1e4fec12e3b8b',
    '8fd0fb56b2ef811cc0e739edc36200dc1613081875d6fca078f653ee19757c83',
    '97a1c605c68bb52904288d24da5989ee3211361f555fc8bb3c64cea8b79cc2fb',
    '9fe6eed5ad92a44f1b31af0c6d3c68c3277ceccec79d28c512170d96bf48682e',
    'a832b4f06b5482906c90890340b59007ef916cd5c363cebe63c6e5fc64800e20',
    'd82746844cd9835668fbb51a7fe3844a2a22692e8365afc67a148eff8c6a0ae1',
    'da3305cb3a4a8f24016c58d62aa87115ffea71fbb8b1a42407ec53625c13a5bf',
    'dfc9055ef1dcd8c9b567f94f1e3c0d01c8e201930bdfed95f89dc15330c9aefb',
    'f47f7ab7f6f6ede94dc0009bf478a28e8bad31030f55251560ae5e31a26d6c99',
    'fe1e720af4fac5d45aa2a774597b9e8b364341bef139ee7107e24bd99ab6ce2c',
)
PUBLIC_SYMBOLS = (
    'CHALLENGE_CONSUMPTION_NAMESPACE',
    'CONSUME_ONCE_COMMAND_SCHEMA_VERSION',
    'CONSUME_ONCE_RESULT_SCHEMA_VERSION',
    'STATIC_FINGERPRINT',
    'ChallengeConsumptionProviderOutcomeV1',
    'ReplayCursorProviderRegistrationChallengeConsumeOnceCommandV1',
    'ReplayCursorProviderRegistrationChallengeConsumeOnceResultV1',
    'ReplayCursorProviderRegistrationChallengeConsumptionPortV1',
    'build_replay_cursor_provider_registration_challenge_consume_once_command_v1',
    'build_replay_cursor_provider_registration_challenge_consume_once_result_v1',
    'derive_challenge_consumption_receipt_hash_v1',
    'derive_consumed_registry_head_v1',
    'verify_replay_cursor_provider_registration_challenge_consume_once_command_v1',
    'verify_replay_cursor_provider_registration_challenge_consume_once_result_v1',
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


class ChallengeConsumptionProviderApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_canonical_port_preserves_pre_migration_bytes_and_has_no_interfaces_dependency(self):
        self.assertEqual(_sha256(CANONICAL_PATH), CANONICAL_SHA256)
        self.assertFalse(
            [target for target in _import_targets(CANONICAL_PATH) if target.startswith("exchange_terminal.interfaces")]
        )

    def test_legacy_shim_is_exact_and_reexports_identical_objects(self):
        self.assertEqual(_sha256(LEGACY_PATH), LEGACY_SHIM_SHA256)
        self.assertEqual(legacy_v1.__all__, PUBLIC_SYMBOLS)
        for symbol in PUBLIC_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(legacy_v1, symbol), getattr(canonical_v1, symbol))

    def test_application_consumers_use_canonical_port(self):
        command_targets = _import_targets(COMMAND_BINDING_PATH)
        preregistration_targets = _import_targets(PREREGISTRATION_PATH)
        self.assertIn(CANONICAL_PACKAGE, command_targets)
        self.assertNotIn(LEGACY_PACKAGE, command_targets)
        self.assertIn(CANONICAL_MODULE, preregistration_targets)
        self.assertNotIn(LEGACY_MODULE, preregistration_targets)

    def test_direct_application_to_interfaces_submodule_imports_are_zero(self):
        edges=[]
        for path in sorted(APPLICATION_ROOT.rglob("*.py")):
            for target in _import_targets(path):
                if target.startswith("exchange_terminal.interfaces."):edges.append((path.relative_to(APPLICATION_ROOT).as_posix(),target))
        self.assertEqual(edges,[])

    def test_schema_namespace_and_fingerprint_are_unchanged(self):
        self.assertEqual(
            canonical_v1.CHALLENGE_CONSUMPTION_NAMESPACE,
            "strategy-correlation-incumbent-snapshot-replay-cursor-provider-registration-challenge-v1",
        )
        self.assertEqual(
            canonical_v1.CONSUME_ONCE_COMMAND_SCHEMA_VERSION,
            "incumbent-snapshot-replay-cursor-provider-registration-challenge-consume-once-command-v1",
        )
        self.assertEqual(
            canonical_v1.CONSUME_ONCE_RESULT_SCHEMA_VERSION,
            "incumbent-snapshot-replay-cursor-provider-registration-challenge-consume-once-result-v1",
        )
        self.assertEqual(
            canonical_v1.STATIC_FINGERPRINT,
            "20260824-replay-cursor-provider-registration-challenge-consumption-port-v1-lock-1",
        )

    def test_provenance_closure_is_current_and_rejects_predecessors(self):
        for relative, expected_hash in CURRENT_PROVENANCE_CLOSURE_SHA256.items():
            path = ROOT / relative
            with self.subTest(relative=relative):
                self.assertEqual(_sha256(path), expected_hash)
                source = path.read_text(encoding="utf-8")
                for stale_hash in STALE_PROVENANCE_SHA256:
                    self.assertNotIn(stale_hash, source)

    def test_predecessor_and_architecture_contracts_are_current(self):
        self.assertEqual(_sha256(ADR0436_TEST_PATH), ADR0436_TEST_SHA256)
        self.assertEqual(_sha256(ADR0437_TEST_PATH), ADR0437_TEST_SHA256)
        self.assertEqual(_sha256(ARCHITECTURE_TEST_PATH), ARCHITECTURE_TEST_SHA256)
        self.assertEqual(_sha256(COMPATIBILITY_TEST_PATH), COMPATIBILITY_TEST_SHA256)

    def test_migration_grants_no_execution_authority(self):
        source = CANONICAL_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "live_order_allowed",
            "paper_authorized",
            "runtime_gate_activation_allowed",
            "publication_allowed",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
