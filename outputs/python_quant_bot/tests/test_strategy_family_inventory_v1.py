from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import sys
from types import MappingProxyType
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _canonical_source import activate_canonical_source

activate_canonical_source()

from exchange_terminal.application.strategy_family_inventory_adapter_v1 import (
    StrategyFamilyInventoryAdapterError,
    build_current_strategy_family_inventory,
)
from hakimi_research.strategy_family_inventory import (
    EXPECTED_REGISTERED_STRATEGY_IDS,
    StrategyFamilyInventoryError,
    build_strategy_family_inventory,
    verify_strategy_family_inventory,
)


ADAPTER_MODULE = "hakimi_research.strategy_family_inventory"


class StrategyFamilyInventoryV1Tests(unittest.TestCase):
    def test_current_registry_is_exactly_projected_without_strategy_instantiation(self) -> None:
        inventory = build_current_strategy_family_inventory()
        self.assertEqual(
            inventory["registered_strategy_ids"],
            list(EXPECTED_REGISTERED_STRATEGY_IDS),
        )
        self.assertEqual(inventory["missing_registry_ids"], [])
        self.assertEqual(inventory["unexpected_registry_ids"], [])
        self.assertEqual(len(inventory["inventory_sha256"]), 64)

    def test_range_and_trend_are_mechanism_families_not_registered_aliases(self) -> None:
        inventory = build_current_strategy_family_inventory()
        families = {item["family_id"]: item for item in inventory["families"]}
        self.assertEqual(families["RANGE"]["status"], "OBSERVED")
        self.assertEqual(
            families["RANGE"]["registered_member_ids"],
            ["bollinger", "grid", "rsi"],
        )
        self.assertEqual(families["TREND"]["status"], "OBSERVED")
        self.assertEqual(
            families["TREND"]["registered_member_ids"],
            ["dual_ma", "macd", "momentum"],
        )
        self.assertNotIn("range", inventory["registered_strategy_ids"])
        self.assertNotIn("trend", inventory["registered_strategy_ids"])

    def test_missing_ensemble_is_explicit_and_blocks_three_family_fixture(self) -> None:
        inventory = build_current_strategy_family_inventory()
        ensemble = next(item for item in inventory["families"] if item["family_id"] == "ENSEMBLE")
        self.assertEqual(ensemble["status"], "GAP")
        self.assertEqual(ensemble["registered_member_ids"], [])
        self.assertEqual(ensemble["gap_code"], "NO_REGISTERED_ENSEMBLE_STRATEGY")
        self.assertEqual(inventory["report_fixture"]["status"], "BLOCK")
        self.assertIn("ENSEMBLE_STRATEGY_NOT_IMPLEMENTED", inventory["blockers"])

    def test_inventory_is_deterministic_replayable_and_non_authorizing(self) -> None:
        first = build_current_strategy_family_inventory()
        second = build_current_strategy_family_inventory()
        self.assertEqual(first, second)
        verification = verify_strategy_family_inventory(first)
        self.assertEqual(verification["status"], "GAP")
        self.assertEqual(verification["report_fixture_status"], "BLOCK")
        self.assertFalse(any(first["authority"].values()))

    def test_missing_and_unversioned_registry_entries_remain_visible(self) -> None:
        drifted = build_strategy_family_inventory([
            item for item in EXPECTED_REGISTERED_STRATEGY_IDS if item != "grid"
        ] + ["new_strategy"])
        self.assertEqual(drifted["missing_registry_ids"], ["grid"])
        self.assertEqual(drifted["unexpected_registry_ids"], ["new_strategy"])
        self.assertIn("EXPECTED_STRATEGY_MISSING:grid", drifted["blockers"])
        self.assertIn("UNVERSIONED_STRATEGY_REGISTERED:new_strategy", drifted["blockers"])

    def test_exact_string_and_list_subclasses_are_rejected(self) -> None:
        class EvilStr(str):
            pass

        class EvilList(list):
            pass

        with self.assertRaisesRegex(StrategyFamilyInventoryError, "exact list"):
            build_strategy_family_inventory(EvilList(EXPECTED_REGISTERED_STRATEGY_IDS))
        with self.assertRaisesRegex(StrategyFamilyInventoryError, "exact canonical strategy identifier"):
            build_strategy_family_inventory([EvilStr("grid")])

    def test_tamper_and_authority_escalation_are_rejected(self) -> None:
        tampered = build_current_strategy_family_inventory()
        tampered["families"][2]["status"] = "OBSERVED"
        with self.assertRaisesRegex(StrategyFamilyInventoryError, "canonical registry projection"):
            verify_strategy_family_inventory(tampered)

        escalated = build_current_strategy_family_inventory()
        escalated["authority"]["live_authorized"] = True
        with self.assertRaisesRegex(StrategyFamilyInventoryError, "must be exact false"):
            verify_strategy_family_inventory(escalated)

    def test_adapter_rejects_non_strategy_registry_values(self) -> None:
        with patch(
            f"{ADAPTER_MODULE}.STRATEGY_REGISTRY",
            MappingProxyType({"grid": object}),
        ):
            with self.assertRaisesRegex(
                StrategyFamilyInventoryAdapterError,
                "not a StrategyBase class",
            ):
                build_current_strategy_family_inventory()


if __name__ == "__main__":
    unittest.main()
