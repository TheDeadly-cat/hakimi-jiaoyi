from __future__ import annotations

from pathlib import Path
import sys
from types import MappingProxyType
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.execution_authority import (
    EXECUTION_AUTHORITY_FIELDS,
    EXECUTION_AUTHORITY_FIELD_KEYS,
    authority_violations,
    canonical_authority_key,
    sanitize_authority_claims,
)
from exchange_terminal.services import portfolio_backtest_pack
from exchange_terminal.services import portfolio_backtest_replay_driver


class ExecutionAuthorityTests(unittest.TestCase):
    def test_sanitizer_canonicalizes_aliases_without_mutating_input(self) -> None:
        mapping_claim = MappingProxyType({"Paper_Authorized": True})
        payload = {
            "safe": {"Paper_Authorized": False},
            "mapping": mapping_claim,
            "nested": [
                {"CAN_TRADE": "false"},
                (
                    {"paperAuthorized": 0},
                    {"live-order-allowed": None},
                ),
            ],
            "source_authority": "OFFICIAL",
        }

        projected, paths = sanitize_authority_claims(payload, path="payload")

        self.assertTrue(mapping_claim["Paper_Authorized"])
        self.assertEqual(payload["nested"][0]["CAN_TRADE"], "false")
        self.assertEqual(payload["nested"][1][0]["paperAuthorized"], 0)
        self.assertIsNone(payload["nested"][1][1]["live-order-allowed"])
        self.assertIs(projected["safe"]["Paper_Authorized"], False)
        self.assertIs(projected["mapping"]["Paper_Authorized"], False)
        self.assertIs(projected["nested"][0]["CAN_TRADE"], False)
        self.assertIs(projected["nested"][1][0]["paperAuthorized"], False)
        self.assertIs(projected["nested"][1][1]["live-order-allowed"], False)
        self.assertEqual(projected["source_authority"], "OFFICIAL")
        self.assertEqual(
            paths,
            [
                "payload.mapping.Paper_Authorized",
                "payload.nested[0].CAN_TRADE",
                "payload.nested[1][0].paperAuthorized",
                "payload.nested[1][1].live-order-allowed",
            ],
        )

        local_keys = frozenset({canonical_authority_key("paper_authorized")})
        local_projection, local_paths = sanitize_authority_claims(
            {"paperAuthorized": True, "canTrade": True, "已授权": "yes"},
            authority_field_keys=local_keys,
        )
        self.assertIs(local_projection["paperAuthorized"], False)
        self.assertIs(local_projection["canTrade"], True)
        self.assertIs(local_projection["已授权"], False)
        self.assertEqual(local_paths, ["$.paperAuthorized", "$.已授权"])

    def test_localized_and_nfkc_authority_keys_are_always_fail_closed(self) -> None:
        payload = {
            "nested": [
                {"可下单": True, "授权来源": "研究治理"},
                (
                    {"已授权": 0},
                    {"实盘授权": None},
                    {"实盘-授权": True},
                    {"实盘－授权": "false"},
                    {"Ｐａｐｅｒ＿Ａｕｔｈｏｒｉｚｅｄ": True},
                ),
            ],
            "source_authority": "OFFICIAL",
            "raw_can_trade": "descriptive-only",
        }

        projected, paths = sanitize_authority_claims(payload, path="payload")

        self.assertEqual(
            authority_violations(payload, path="payload"),
            [
                "payload.nested[0].可下单",
                "payload.nested[1][0].已授权",
                "payload.nested[1][1].实盘授权",
                "payload.nested[1][2].实盘-授权",
                "payload.nested[1][3].实盘－授权",
                "payload.nested[1][4].Ｐａｐｅｒ＿Ａｕｔｈｏｒｉｚｅｄ",
            ],
        )
        self.assertTrue(payload["nested"][0]["可下单"])
        self.assertEqual(payload["nested"][1][0]["已授权"], 0)
        self.assertIsNone(payload["nested"][1][1]["实盘授权"])
        self.assertIs(projected["nested"][0]["可下单"], False)
        self.assertIs(projected["nested"][1][0]["已授权"], False)
        self.assertIs(projected["nested"][1][1]["实盘授权"], False)
        self.assertIs(projected["nested"][1][2]["实盘-授权"], False)
        self.assertIs(projected["nested"][1][3]["实盘－授权"], False)
        self.assertIs(
            projected["nested"][1][4]["Ｐａｐｅｒ＿Ａｕｔｈｏｒｉｚｅｄ"],
            False,
        )
        self.assertEqual(projected["nested"][0]["授权来源"], "研究治理")
        self.assertEqual(projected["source_authority"], "OFFICIAL")
        self.assertEqual(projected["raw_can_trade"], "descriptive-only")
        self.assertEqual(
            paths,
            [
                "payload.nested[0].可下单",
                "payload.nested[1][0].已授权",
                "payload.nested[1][1].实盘授权",
                "payload.nested[1][2].实盘-授权",
                "payload.nested[1][3].实盘－授权",
                "payload.nested[1][4].Ｐａｐｅｒ＿Ａｕｔｈｏｒｉｚｅｄ",
            ],
        )
        self.assertEqual(
            canonical_authority_key("Ｐａｐｅｒ＿Ａｕｔｈｏｒｉｚｅｄ"),
            canonical_authority_key("paper_authorized"),
        )
        self.assertEqual(
            canonical_authority_key("实盘－授权"),
            canonical_authority_key("实盘-授权"),
        )

    def test_aliases_nested_containers_and_non_native_false_fail_closed(self) -> None:
        payload = MappingProxyType({
            "safe": {"Paper_Authorized": False},
            "nested": [
                {"Paper_Authorized": True},
                (
                    {"CAN_TRADE": "false"},
                    {"paperAuthorized": 0},
                    {"live-order-allowed": None},
                ),
            ],
        })

        self.assertEqual(
            authority_violations(payload),
            [
                "$.nested[0].Paper_Authorized",
                "$.nested[1][0].CAN_TRADE",
                "$.nested[1][1].paperAuthorized",
                "$.nested[1][2].live-order-allowed",
            ],
        )

    def test_native_false_is_the_only_allowed_authority_value(self) -> None:
        for value in (True, "false", 0, None, [], {}):
            with self.subTest(value=value):
                self.assertEqual(authority_violations({"canTrade": value}), ["$.canTrade"])
        self.assertEqual(
            authority_violations({"canTrade": False, "Paper_Authorized": False}),
            [],
        )

    def test_pack_reexports_shared_contract(self) -> None:
        self.assertIs(portfolio_backtest_pack.authority_violations, authority_violations)
        self.assertIs(
            portfolio_backtest_pack.EXECUTION_AUTHORITY_FIELDS,
            EXECUTION_AUTHORITY_FIELDS,
        )
        self.assertIs(
            portfolio_backtest_pack.EXECUTION_AUTHORITY_FIELD_KEYS,
            EXECUTION_AUTHORITY_FIELD_KEYS,
        )

    def test_standalone_replay_driver_scanner_matches_shared_contract(self) -> None:
        self.assertEqual(
            portfolio_backtest_replay_driver.EXECUTION_AUTHORITY_FIELDS,
            EXECUTION_AUTHORITY_FIELDS,
        )
        self.assertEqual(
            portfolio_backtest_replay_driver.EXECUTION_AUTHORITY_FIELD_KEYS,
            EXECUTION_AUTHORITY_FIELD_KEYS,
        )
        samples = [
            MappingProxyType({"Paper_Authorized": True}),
            {"nested": [({"CAN_TRADE": "false"}, {"paperAuthorized": False})]},
            {"parameter-selection-allowed": 0, "source_authority": "OFFICIAL"},
            {"nested": [{"parameterSelectionAuthority": True}]},
            {"nested": [{"可下单": True}, {"已授权": 0}, {"实盘-授权": None}]},
            {"nested": [{"实盘－授权": "false"}, {"ＣＡＮ＿ＴＲＡＤＥ": True}]},
        ]
        for payload in samples:
            with self.subTest(payload=payload):
                self.assertEqual(
                    portfolio_backtest_replay_driver.authority_violations(payload),
                    authority_violations(payload),
                )


if __name__ == "__main__":
    unittest.main()
