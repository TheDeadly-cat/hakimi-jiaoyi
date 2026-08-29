from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import unittest

from exchange_terminal.application.ports import (
    challenge_consumption_provider_genesis_replay_reservation_provider_v1 as canonical_v1,
)
from exchange_terminal.interfaces import (
    challenge_consumption_provider_genesis_replay_reservation_provider as legacy_v1,
)


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "exchange_terminal" / "application"
CANONICAL_PATH = ROOT / "exchange_terminal" / "application" / "ports" / "challenge_consumption_provider_genesis_replay_reservation_provider_v1.py"
LEGACY_PATH = ROOT / "exchange_terminal" / "interfaces" / "challenge_consumption_provider_genesis_replay_reservation_provider.py"
CONSUMER_PATH = ROOT / "exchange_terminal" / "application" / "challenge_consumption_provider_genesis_replay_reservation_preregistration_v1.py"
PREDECESSOR_TEST_PATH = ROOT / "tests" / "test_anti_replay_registry_application_port_migration_v1.py"
ARCHITECTURE_TEST_PATH = ROOT / "tests" / "test_exchange_terminal_layer_dependency_audit_v2.py"
CANONICAL_MODULE = "exchange_terminal.application.ports.challenge_consumption_provider_genesis_replay_reservation_provider_v1"
LEGACY_MODULE = "exchange_terminal.interfaces.challenge_consumption_provider_genesis_replay_reservation_provider"
CANONICAL_SHA256 = "1d8ddf5cbe28481e9b5f911cdd776891d1692c6a2e8183f9bf17e01473924512"
LEGACY_SHIM_SHA256 = "5e5fc36bee30958af90bcff36ba73098d90eea9b599ded7ea9d1ded0ed180694"
PREDECESSOR_TEST_SHA256 = "f96d05ea8e9e7ed5093739531704c40f1675dacff685629ce376f1bba87aa58c"
ARCHITECTURE_TEST_SHA256 = "1c18895e504491e33139c2be7a85be80eac1f92c18eedff2c14a71b23db0cbbc"
CURRENT_PROVENANCE_CLOSURE_SHA256 = {
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
    '194c2789abaf9193344cd12417cf8e813d28217894bca5376501465cbe12f478',
    '2150157d9435e62ff3e15a7bb5f0cf660158d7596e83d7c075ae93e8ebb8c82e',
    '3f79afd364555e251ce20a6de8f248de2376e1dfa36bb2603966d41ae1a174a5',
    '615747e8b18c1e077d9d8e28274e5f7a68f797b18ec323c9808fe5c1e4a66bd1',
    '741d4b44ac374fcf05e4daddfb142e5e4efb510ffec8eefdbb60e62487307313',
    '8e64081ab6d26e5678f4b86b80a28be1e2bbc7ba0d035840f4f1e4fec12e3b8b',
    '97a1c605c68bb52904288d24da5989ee3211361f555fc8bb3c64cea8b79cc2fb',
    '9b40558a4fae4adc6d0c7f4e246e5a7fa8efbf4b49ab2480eda9dd000f787425',
    '9fe6eed5ad92a44f1b31af0c6d3c68c3277ceccec79d28c512170d96bf48682e',
    'aa4214626329c225f13755b7e468d71b0101dcfd8a7ce96d63eaadb408269544',
    'd82746844cd9835668fbb51a7fe3844a2a22692e8365afc67a148eff8c6a0ae1',
    'dfc9055ef1dcd8c9b567f94f1e3c0d01c8e201930bdfed95f89dc15330c9aefb',
    'f19f029daeb77435fdc72b4bd4f1b0f9c72f7578751d4b69525aa9ac09ca251f',
    'f47f7ab7f6f6ede94dc0009bf478a28e8bad31030f55251560ae5e31a26d6c99',
    'fe1e720af4fac5d45aa2a774597b9e8b364341bef139ee7107e24bd99ab6ce2c',
    'ff9f045f83e4f3ba5e3f20a5f057e72f3d01800d09754c24ddbd2110e5a89075',
)
PUBLIC_SYMBOLS = (
    'GenesisAdmissionReplayReservationOutcomeV1',
    'GenesisAdmissionReplayReservationPortV1',
    'GenesisAdmissionReplayReserveOnceCommandV1',
    'GenesisAdmissionReplayReserveOnceResultV1',
    'RESERVATION_NAMESPACE',
    'RESERVE_ONCE_COMMAND_SCHEMA_VERSION',
    'RESERVE_ONCE_RESULT_SCHEMA_VERSION',
    'STATIC_FINGERPRINT',
    'build_genesis_admission_replay_reserve_once_command_v1',
    'build_genesis_admission_replay_reserve_once_result_v1',
    'verify_genesis_admission_replay_reserve_once_result_v1',
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


class GenesisReplayReservationApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_canonical_port_preserves_pre_migration_bytes(self):
        self.assertEqual(_sha256(CANONICAL_PATH), CANONICAL_SHA256)

    def test_canonical_port_has_no_interfaces_dependency(self):
        self.assertFalse(
            [
                target
                for target in _import_targets(CANONICAL_PATH)
                if target.startswith("exchange_terminal.interfaces")
            ]
        )

    def test_legacy_shim_is_exact_and_reexports_identical_objects(self):
        self.assertEqual(_sha256(LEGACY_PATH), LEGACY_SHIM_SHA256)
        self.assertEqual(legacy_v1.__all__, PUBLIC_SYMBOLS)
        for symbol in PUBLIC_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertIs(getattr(legacy_v1, symbol), getattr(canonical_v1, symbol))

    def test_application_consumer_uses_canonical_port(self):
        targets = _import_targets(CONSUMER_PATH)
        self.assertIn(CANONICAL_MODULE, targets)
        self.assertNotIn(LEGACY_MODULE, targets)

    def test_direct_application_to_interfaces_submodule_imports_remain_at_most_five(self):
        edges: list[tuple[str, str]] = []
        for path in sorted(APPLICATION_ROOT.rglob("*.py")):
            for target in _import_targets(path):
                if target.startswith("exchange_terminal.interfaces."):
                    edges.append((path.relative_to(APPLICATION_ROOT).as_posix(), target))
        self.assertLessEqual(len(edges), 5)
        self.assertFalse([edge for edge in edges if edge[1] == LEGACY_MODULE])

    def test_schema_namespace_and_fingerprint_are_unchanged(self):
        self.assertEqual(
            canonical_v1.RESERVATION_NAMESPACE,
            "strategy-correlation-challenge-consumption-provider-genesis-admission-replay-reservation-v1",
        )
        self.assertEqual(
            canonical_v1.RESERVE_ONCE_COMMAND_SCHEMA_VERSION,
            "challenge-consumption-provider-genesis-replay-reserve-once-command-v1",
        )
        self.assertEqual(
            canonical_v1.RESERVE_ONCE_RESULT_SCHEMA_VERSION,
            "challenge-consumption-provider-genesis-replay-reserve-once-result-v1",
        )
        self.assertEqual(
            canonical_v1.STATIC_FINGERPRINT,
            "20260824-challenge-consumption-provider-genesis-replay-reservation-port-v1-lock-1",
        )

    def test_provenance_closure_matches_current_files_and_rejects_predecessors(self):
        for relative, expected_hash in CURRENT_PROVENANCE_CLOSURE_SHA256.items():
            path = ROOT / relative
            with self.subTest(relative=relative):
                self.assertEqual(_sha256(path), expected_hash)
                source = path.read_text(encoding="utf-8")
                for stale_hash in STALE_PROVENANCE_SHA256:
                    self.assertNotIn(stale_hash, source)

    def test_predecessor_and_architecture_contracts_are_current(self):
        self.assertEqual(_sha256(PREDECESSOR_TEST_PATH), PREDECESSOR_TEST_SHA256)
        self.assertEqual(_sha256(ARCHITECTURE_TEST_PATH), ARCHITECTURE_TEST_SHA256)

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
