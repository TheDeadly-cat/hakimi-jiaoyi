from __future__ import annotations

from copy import deepcopy
import unittest

from exchange_terminal.services.execution_authority import (
    EXECUTION_AUTHORITY_FIELDS,
    EXECUTION_AUTHORITY_FIELD_KEYS,
    authority_violations,
    canonical_authority_key,
    sanitize_authority_claims,
)
from exchange_terminal.services.platform_control_center import (
    build_market_data_health_projection,
)


class LiveAuthorizedAliasFailClosedV1Tests(unittest.TestCase):
    def test_live_authorized_is_registered_and_all_canonical_aliases_violate(self) -> None:
        payload = {
            "live_authorized": True,
            "nested": [
                {"live-authorized": "yes"},
                (
                    {"LIVE AUTHORIZED": 0},
                    {"Ｌｉｖｅ＿Ａｕｔｈｏｒｉｚｅｄ": None},
                ),
            ],
        }

        self.assertIn("live_authorized", EXECUTION_AUTHORITY_FIELDS)
        self.assertIn(
            canonical_authority_key("live_authorized"),
            EXECUTION_AUTHORITY_FIELD_KEYS,
        )
        self.assertEqual(
            authority_violations(payload),
            [
                "$.live_authorized",
                "$.nested[0].live-authorized",
                "$.nested[1][0].LIVE AUTHORIZED",
                "$.nested[1][1].Ｌｉｖｅ＿Ａｕｔｈｏｒｉｚｅｄ",
            ],
        )

    def test_default_sanitizer_clears_aliases_without_mutating_input(self) -> None:
        payload = {
            "live_authorized": True,
            "nested": [
                {"live-authorized": "yes"},
                {"LIVE AUTHORIZED": 1},
            ],
        }
        before = deepcopy(payload)

        projected, paths = sanitize_authority_claims(payload, path="payload")

        self.assertEqual(payload, before)
        self.assertIs(projected["live_authorized"], False)
        self.assertIs(projected["nested"][0]["live-authorized"], False)
        self.assertIs(projected["nested"][1]["LIVE AUTHORIZED"], False)
        self.assertEqual(
            paths,
            [
                "payload.live_authorized",
                "payload.nested[0].live-authorized",
                "payload.nested[1].LIVE AUTHORIZED",
            ],
        )

    def test_live_authorized_remains_mandatory_under_narrow_field_sets(self) -> None:
        narrow_keys = frozenset({canonical_authority_key("paper_authorized")})

        projected, paths = sanitize_authority_claims(
            {
                "paperAuthorized": True,
                "liveAuthorized": True,
                "canTrade": True,
            },
            authority_field_keys=narrow_keys,
        )

        self.assertIs(projected["paperAuthorized"], False)
        self.assertIs(projected["liveAuthorized"], False)
        self.assertIs(projected["canTrade"], True)
        self.assertEqual(paths, ["$.paperAuthorized", "$.liveAuthorized"])

    def test_platform_narrow_projection_inherits_mandatory_live_alias(self) -> None:
        source = {
            "nested": {"live_authorized": True},
            "source_authority": "OFFICIAL",
        }

        projected = build_market_data_health_projection(
            source,
            runtime_read_only=True,
            live_trading_hard_block=True,
        )

        self.assertTrue(source["nested"]["live_authorized"])
        self.assertIs(projected["nested"]["live_authorized"], False)
        self.assertEqual(projected["source_authority"], "OFFICIAL")
        self.assertIn(
            "health.nested.live_authorized",
            projected["authority_sanitized_paths"],
        )

    def test_native_false_and_descriptive_prefixed_fields_remain_compatible(self) -> None:
        payload = {
            "live_authorized": False,
            "raw_live_authorized": "descriptive-only",
            "source_authority": "OFFICIAL",
        }

        projected, paths = sanitize_authority_claims(payload)

        self.assertEqual(authority_violations(payload), [])
        self.assertEqual(paths, [])
        self.assertIs(projected["live_authorized"], False)
        self.assertEqual(projected["raw_live_authorized"], "descriptive-only")
        self.assertEqual(projected["source_authority"], "OFFICIAL")


if __name__ == "__main__":
    unittest.main()
