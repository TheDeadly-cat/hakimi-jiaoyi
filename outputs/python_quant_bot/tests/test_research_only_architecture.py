from __future__ import annotations

import unittest

from exchange_terminal.application.health_contract import build_runtime_health_payload
from exchange_terminal.domain.contracts import build_research_only_capability


class ResearchOnlyArchitectureTests(unittest.TestCase):
    def runtime_build(self) -> dict[str, object]:
        return {
            "schema_version": "hakimi-runtime-build-v1",
            "status": "PASS",
            "restart_required": False,
            "time": 1,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def test_health_uses_exact_nested_and_endpoint_capability(self) -> None:
        payload = build_runtime_health_payload(
            self.runtime_build(),
            {"armed": True},
            read_only=True,
            runtime_mutations_allowed=False,
            live_trading_hard_block=True,
            guardian_worker_running=False,
        )
        expected = build_research_only_capability().to_dict()
        self.assertEqual(payload["capability"], expected)
        self.assertEqual(payload["runtime_build"]["capability"], expected)
        self.assertEqual(payload["runtime_build"]["schema_version"], "hakimi-runtime-build-v1")
        self.assertNotIn("product_mode", payload["runtime_build"])
        self.assertNotIn("runtime_build_signature", payload)
        self.assertFalse(payload["paper_authorized"])
        self.assertFalse(payload["live_order_allowed"])

    def test_health_is_not_ok_without_the_live_hard_wall(self) -> None:
        payload = build_runtime_health_payload(
            self.runtime_build(),
            {"armed": False},
            read_only=True,
            runtime_mutations_allowed=False,
            live_trading_hard_block=False,
            guardian_worker_running=False,
        )
        self.assertFalse(payload["ok"])
        self.assertFalse(payload["live_order_allowed"])

    def test_capability_contract_is_versioned_and_fail_closed(self) -> None:
        capability = build_research_only_capability().to_dict()
        self.assertEqual(capability["schema_version"], "capability-v1")
        self.assertEqual(capability["product_mode"], "research_only")
        self.assertTrue(capability["research_only"])
        self.assertFalse(capability["paper_allowed"])
        self.assertFalse(capability["live_allowed"])


if __name__ == "__main__":
    unittest.main()
