from __future__ import annotations

import unittest

from run_market_data_revision_repair import resolve_if_blocked


class MarketDataRevisionRepairTests(unittest.TestCase):
    def test_unblocked_scope_supports_idempotent_verification(self) -> None:
        result = resolve_if_blocked(
            {
                "status": "PASS",
                "scope_key": "PROVIDER_OBSERVATION|AAPL|futu|1d|regular||",
                "blocking_event_hash": "",
            },
            event_hash="",
            reason="verify restored scope",
            source_label="primary",
        )

        self.assertEqual(result["status"], "NOT_REQUIRED")
        self.assertEqual(result["resolution_hash"], "")
        self.assertFalse(result["paper_authorized"])
        self.assertFalse(result["live_order_allowed"])

    def test_blocked_scope_requires_explicit_event_hash(self) -> None:
        with self.assertRaisesRegex(ValueError, "primary_blocking_event_required"):
            resolve_if_blocked(
                {
                    "status": "BLOCK",
                    "scope_key": "PROVIDER_OBSERVATION|AAPL|futu|1d|regular||",
                    "blocking_event_hash": "a" * 64,
                },
                event_hash="",
                reason="missing event should fail closed",
                source_label="primary",
            )


if __name__ == "__main__":
    unittest.main()
