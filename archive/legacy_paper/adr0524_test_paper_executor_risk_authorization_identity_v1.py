from __future__ import annotations

import unittest

from exchange_terminal.services.paper_executor import PaperExecutor


class PaperExecutorRiskAuthorizationIdentityV1Tests(unittest.TestCase):
    NOW = 1_780_000_000_000

    @classmethod
    def _authorization(cls, request_id: str, idempotency_key: str) -> dict[str, object]:
        return {
            "request_id": request_id,
            "allowed": True,
            "paper_order_allowed": True,
            "live_order_allowed": False,
            "mode": "PAPER",
            "symbol": "AAPL",
            "side": "BUY",
            "checked_at": cls.NOW,
            "requested_price": 100.0,
            "notional": 100.0,
            "context": {
                "order_type": "MARKET",
                "limit_price": 0.0,
                "reduce_only": False,
                "idempotency_key": idempotency_key,
                "risk_audit_status": "PASS",
            },
        }

    @classmethod
    def _executor(cls) -> PaperExecutor:
        return PaperExecutor(
            now_ms=lambda: cls.NOW,
            book_reader=lambda *_: [],
            funding_rate_reader=lambda *_: 0.0,
            instance_nonce="identity01",
        )

    @classmethod
    def _submit(
        cls,
        executor: PaperExecutor,
        *,
        request_id: str,
        idempotency_key: str,
    ) -> dict[str, object]:
        return executor.submit(
            symbol="AAPL",
            side="BUY",
            order_type="MARKET",
            mark_price=100.0,
            notional=100.0,
            risk_result=cls._authorization(request_id, idempotency_key),
            context={
                "idempotency_key": idempotency_key,
                "source": "synthetic-contract",
            },
        )

    def test_noncanonical_request_ids_fail_before_lifecycle_creation(self) -> None:
        executor = self._executor()

        for index, request_id in enumerate((" risk-auth", "risk-auth ", "\trisk-auth")):
            with self.subTest(request_id=repr(request_id)):
                report = self._submit(
                    executor,
                    request_id=request_id,
                    idempotency_key=f"noncanonical-{index}",
                )
                self.assertEqual(report["status"], "REJECTED")
                self.assertTrue(report["risk_authorization_invalid"])
                self.assertIn(
                    "risk_request_id_noncanonical",
                    report["risk_authorization_blockers"],
                )

        self.assertEqual(executor.snapshot()["order_count"], 0)

    def test_canonical_request_id_is_preserved_exactly(self) -> None:
        executor = self._executor()

        report = self._submit(
            executor,
            request_id="risk-auth-canonical",
            idempotency_key="canonical-request",
        )

        self.assertEqual(report["status"], "FILLED")
        self.assertEqual(report["risk_request_id"], "risk-auth-canonical")
        self.assertIsNone(report["replay_authorization_request_id"])
        self.assertFalse(report["risk_authorization_rotated"])
        self.assertEqual(executor.snapshot()["order_count"], 1)

    def test_idempotent_replay_attributes_rotated_risk_request_id(self) -> None:
        executor = self._executor()
        original = self._submit(
            executor,
            request_id="risk-auth-original",
            idempotency_key="bound-replay",
        )

        replay = self._submit(
            executor,
            request_id="risk-auth-different",
            idempotency_key="bound-replay",
        )

        self.assertEqual(original["status"], "FILLED")
        self.assertEqual(replay["status"], "FILLED")
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(replay["order_id"], original["order_id"])
        self.assertEqual(replay["risk_request_id"], "risk-auth-original")
        self.assertEqual(
            replay["replay_authorization_request_id"],
            "risk-auth-different",
        )
        self.assertTrue(replay["risk_authorization_rotated"])
        self.assertEqual(executor.snapshot()["order_count"], 1)

    def test_idempotent_replay_preserves_matching_authorization(self) -> None:
        executor = self._executor()
        original = self._submit(
            executor,
            request_id="risk-auth-matching",
            idempotency_key="matching-replay",
        )

        replay = self._submit(
            executor,
            request_id="risk-auth-matching",
            idempotency_key="matching-replay",
        )

        self.assertEqual(replay["status"], "FILLED")
        self.assertTrue(replay["idempotent_replay"])
        self.assertEqual(replay["order_id"], original["order_id"])
        self.assertEqual(replay["risk_request_id"], "risk-auth-matching")
        self.assertEqual(
            replay["replay_authorization_request_id"],
            "risk-auth-matching",
        )
        self.assertFalse(replay["risk_authorization_rotated"])
        self.assertEqual(executor.snapshot()["order_count"], 1)


if __name__ == "__main__":
    unittest.main()
