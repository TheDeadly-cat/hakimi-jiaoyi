from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path
import sys
import unittest

from exchange_terminal.application import (
    portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1 as adapter,
)
from exchange_terminal.application import (
    portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1 as identity,
)
from exchange_terminal.application.ports import (
    portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 as canonical,
)
from exchange_terminal.interfaces import http as http_package
from exchange_terminal.interfaces.http import (
    portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1 as legacy,
)


ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROOT = ROOT / "exchange_terminal" / "application"
CANONICAL_PATH = (
    ROOT
    / "exchange_terminal/application/ports/"
    "portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1.py"
)
LEGACY_PATH = (
    ROOT
    / "exchange_terminal/interfaces/http/"
    "portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1.py"
)
ALIAS_REGISTRAR_PATH = ROOT / "exchange_terminal/interfaces/http/__init__.py"
IDENTITY_PATH = (
    ROOT
    / "exchange_terminal/application/"
    "portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1.py"
)
ADAPTER_PATH = (
    ROOT
    / "exchange_terminal/application/"
    "portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1.py"
)
LEGACY_MODULE_BASENAME = (
    "portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1"
)
LEGACY_MODULE_NAME = (
    f"exchange_terminal.interfaces.http.{LEGACY_MODULE_BASENAME}"
)

FILE_HASHES = {
    CANONICAL_PATH: "14f1e0f63668e9ddde716d4915d595182ae615be880a9b515542a58ef57ab1cc",
    LEGACY_PATH: "14f1e0f63668e9ddde716d4915d595182ae615be880a9b515542a58ef57ab1cc",
    ALIAS_REGISTRAR_PATH: "cfc20c1605c2f6edd5acd8fcdc24ee0fca90df82ff7bdd1bbf536b1aeabf81c8",
    IDENTITY_PATH: "94001aa9af6cb7f8283ee3ab398b360ee76cb0fc9bf45cc4ff405a5755fba73d",
    ADAPTER_PATH: "c8210e1bdd91fb7e34f538054cb7727f3a432beae00da09cb939469e7aa56bcf",
}
IDENTITY_HASH = "aeaa931f01a2aa1f67643ff59b5f2927a418bd6576d6586244dc46abab95781f"
ADAPTER_CONTRACT_HASH = (
    "c6e04132f9e773dfdf77fdbd4ef3255d102b6c0000918b6b3631f204f485215b"
)
PRIOR_ADAPTER_CONTRACT_HASH = (
    "ff4de40e1323657a1df6213616c9fd2c92e194f7545bee54bfe4108132e1333f"
)
HISTORICAL_MOUNT_CLOSURE = {
    (
        "exchange_terminal/services/"
        "portfolio_correlation_admission_effective_budget_readonly_http_"
        "projection_mount_preregistration_v1.py"
    ): "460cc552d650a8615191da4a40c8afac16b6c5700e552bdcdc000a9b5f2b10ae",
    (
        "tests/test_portfolio_correlation_admission_effective_budget_readonly_"
        "http_projection_mount_preregistration_v1.py"
    ): "ba5d0dc605f8b9003eed0e48064bfc18017cc34cfdc0833dfe9e02d4f5382241",
}
MIGRATION_CLOSURE = {
    (
        "exchange_terminal/application/"
        "portfolio_correlation_admission_effective_budget_readonly_projection_"
        "adapter_candidate_v1.py"
    ): "c8210e1bdd91fb7e34f538054cb7727f3a432beae00da09cb939469e7aa56bcf",
    (
        "tests/test_portfolio_correlation_admission_effective_budget_readonly_"
        "projection_adapter_candidate_v1.py"
    ): "a4f512b85f3108aa38fca014fc5a412a46230cced42a36e3c8f30b75bfeb281e",
    "tests/test_exchange_terminal_layer_dependency_audit_v2.py": (
        "1c18895e504491e33139c2be7a85be80eac1f92c18eedff2c14a71b23db0cbbc"
    ),
    (
        "tests/test_challenge_consumption_provider_genesis_replay_reservation_"
        "application_port_migration_v1.py"
    ): "21893372d2b85ddc84e8b9b96608eb583303d0c51efe8e7b82632b4903639742",
    "tests/test_anti_replay_registry_v2_application_port_migration_v1.py": (
        "6618d47eb17f06fd9be94f683220fa598d2354cd35c8efd6630c2265a4da051c"
    ),
    (
        "tests/test_challenge_consumption_provider_application_port_migration_v1.py"
    ): "3ccb73e9822e43d2d81cd009cd7e995f68c6a85c4a15de50148c836cab779692",
    "tests/test_replay_cursor_provider_application_port_migration_v1.py": (
        "37288834b46d79eb38fe4c729ea231f87784b3271e98479a1776a8ae58181acc"
    ),
    "tests/test_witness_ownership_ports_application_port_migration_v1.py": (
        "3f855a92aac3398591daeabb3fcd65810413e78fc39a36286ec8d3f8167e27b6"
    ),
}
EXPORTS = (
    "BLOCKED_STATE",
    "INTERFACE_STATUS",
    "KNOWN_STATE",
    "PROJECTION_ID",
    "REQUEST_SCHEMA_VERSION",
    "RESPONSE_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "UNKNOWN_STATE",
    (
        "build_portfolio_correlation_admission_effective_budget_readonly_"
        "http_projection_candidate_v1"
    ),
    (
        "verify_portfolio_correlation_admission_effective_budget_readonly_"
        "http_projection_candidate_v1"
    ),
)


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    values: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            values.add(node.module)
        elif isinstance(node, ast.Import):
            values.update(alias.name for alias in node.names)
    return values


class ReadonlyProjectionApplicationPortMigrationV1Tests(unittest.TestCase):
    def test_module_alias_preserves_runtime_identity_and_historical_bytes(self) -> None:
        for path, expected_hash in FILE_HASHES.items():
            self.assertEqual(file_sha256(path), expected_hash, path)

        self.assertIs(legacy, canonical)
        self.assertIs(sys.modules[LEGACY_MODULE_NAME], canonical)
        self.assertIs(getattr(http_package, LEGACY_MODULE_BASENAME), canonical)
        self.assertEqual(Path(legacy.__file__).resolve(), CANONICAL_PATH.resolve())
        self.assertNotEqual(Path(legacy.__file__).resolve(), LEGACY_PATH.resolve())
        self.assertEqual(tuple(canonical.__all__), EXPORTS)
        self.assertEqual(tuple(legacy.__all__), EXPORTS)
        for name in EXPORTS:
            self.assertIs(getattr(canonical, name), getattr(legacy, name))

    def test_historical_mount_chain_remains_byte_exact(self) -> None:
        for relative_path, expected_hash in HISTORICAL_MOUNT_CLOSURE.items():
            self.assertEqual(file_sha256(ROOT / relative_path), expected_hash)

    def test_callable_identity_is_rebuildable(self) -> None:
        document = (
            identity.build_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1()
        )
        self.assertEqual(document["identity_hash"], IDENTITY_HASH)
        self.assertTrue(
            identity.verify_portfolio_correlation_admission_effective_budget_readonly_projection_callable_identity_v1(
                document,
                canonical.build_portfolio_correlation_admission_effective_budget_readonly_http_projection_candidate_v1,
            )
        )

    def test_adapter_manifest_is_rebuildable(self) -> None:
        document = (
            adapter.build_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1()
        )
        self.assertTrue(
            adapter.verify_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_contract_manifest_v1(document)
        )
        self.assertEqual(document["adapter_contract_hash"], ADAPTER_CONTRACT_HASH)
        self.assertEqual(
            document["prior_adapter_contract_hash"],
            PRIOR_ADAPTER_CONTRACT_HASH,
        )
        self.assertEqual(document["projection_callable_identity_hash"], IDENTITY_HASH)

    def test_application_has_zero_interfaces_import_edges(self) -> None:
        violations = [
            (path, imported)
            for path in APPLICATION_ROOT.rglob("*.py")
            for imported in imported_modules(path)
            if imported == "exchange_terminal.interfaces"
            or imported.startswith("exchange_terminal.interfaces.")
        ]
        self.assertEqual(violations, [])

    def test_migration_closure_hashes_are_exact(self) -> None:
        for relative_path, expected_hash in MIGRATION_CLOSURE.items():
            self.assertEqual(file_sha256(ROOT / relative_path), expected_hash)


if __name__ == "__main__":
    unittest.main()