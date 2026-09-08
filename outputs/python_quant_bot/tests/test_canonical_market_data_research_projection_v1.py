from __future__ import annotations

from pathlib import Path
import sys
import unittest
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
BOT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for candidate in (str(SRC_ROOT), str(BOT_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from hakimi_research.market_data_research_projection import (  # noqa: E402
    SCHEMA_VERSION,
    build_market_data_research_projection,
)
from exchange_terminal.services.market_data_service import (  # noqa: E402
    _with_market_data_research_projection,
)


class HostileStr(str):
    calls = 0

    def _fail(self, *_args: Any, **_kwargs: Any) -> Any:
        type(self).calls += 1
        raise AssertionError("subclass-controlled text method invoked")

    strip = _fail
    upper = _fail
    lower = _fail
    encode = _fail
    __str__ = _fail


class HostileDict(dict):
    calls = 0

    def _fail(self, *_args: Any, **_kwargs: Any) -> Any:
        type(self).calls += 1
        raise AssertionError("subclass-controlled mapping method invoked")

    get = _fail
    items = _fail
    keys = _fail
    values = _fail
    __iter__ = _fail


class HostileList(list):
    calls = 0

    def __iter__(self):  # type: ignore[override]
        type(self).calls += 1
        raise AssertionError("subclass-controlled sequence method invoked")


def raw_truth(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "market-data-truth-v1",
        "status": "READY",
        "mode": "REALTIME_READY",
        "snapshot_available": True,
        "observation_current": True,
        "realtime_ready": True,
        "quote": {"source": "primary-test-source"},
        "candles": {
            "source": "primary-test-source",
            "last_completed_ts": 1_700_000_000_000,
        },
        "analysis_usable": True,
        "realtime_usable": True,
        "research_usable": True,
        "execution_usable": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload.update(overrides)
    return payload


def assert_no_ready(test: unittest.TestCase, value: Any) -> None:
    if type(value) is dict:
        for key, item in value.items():
            test.assertNotIn("READY", key)
            assert_no_ready(test, item)
    elif type(value) is list:
        for item in value:
            assert_no_ready(test, item)
    elif type(value) is str:
        test.assertNotIn("READY", value)


class CanonicalMarketDataResearchProjectionV1Tests(unittest.TestCase):
    def test_canonical_source_is_outside_outputs_and_versioned(self) -> None:
        module_path = SRC_ROOT / "hakimi_research" / "market_data_research_projection.py"
        self.assertTrue(module_path.is_file())
        self.assertNotIn("outputs", module_path.relative_to(REPO_ROOT).parts)
        self.assertEqual(SCHEMA_VERSION, "market-data-research-projection-v1")

    def test_current_raw_truth_projects_to_neutral_research_observation(self) -> None:
        projection = build_market_data_research_projection(raw_truth())
        self.assertEqual(projection["sequence"], ["SOURCE", "GAP", "MATURITY", "PERMISSION"])
        self.assertEqual(projection["source"]["status"], "BOUND")
        self.assertEqual(projection["gap"]["status"], "NONE")
        self.assertEqual(projection["maturity"]["status"], "CURRENT_OBSERVATION")
        self.assertEqual(projection["permission"]["status"], "RESEARCH_ONLY")
        governed = {
            "paper_authorized",
            "live_order_allowed",
            "order_allowed",
            "ranking_allowed",
            "parameter_selection_allowed",
            "profitability_proven",
        }
        self.assertTrue(all(projection["permission"][key] is False for key in governed))
        assert_no_ready(self, projection)

    def test_historical_observation_is_not_promoted_to_current(self) -> None:
        projection = build_market_data_research_projection(
            raw_truth(mode="HISTORICAL_ONLY", realtime_usable=False)
        )
        self.assertEqual(projection["maturity"]["status"], "HISTORICAL_OBSERVATION")
        self.assertFalse(projection["maturity"]["current_observation"])

    def test_raw_ready_without_quote_or_candle_evidence_is_degraded(self) -> None:
        projection = build_market_data_research_projection(raw_truth(quote={}, candles={}))
        self.assertEqual(projection["source"]["status"], "PARTIAL")
        self.assertIn("QUOTE_SOURCE_MISSING", projection["gap"]["codes"])
        self.assertIn("CANDLE_SOURCE_MISSING", projection["gap"]["codes"])
        self.assertIn("CANDLE_FRESHNESS_UNCONFIRMED", projection["gap"]["codes"])
        self.assertEqual(projection["maturity"]["status"], "DEGRADED_OBSERVATION")

    def test_unobserved_snapshot_keeps_gap_open(self) -> None:
        projection = build_market_data_research_projection(
            raw_truth(
                status="UNKNOWN",
                mode="UNOBSERVED",
                snapshot_available=False,
                observation_current=False,
                realtime_ready=False,
                quote={},
                candles={},
                analysis_usable=False,
                realtime_usable=False,
                research_usable=False,
            )
        )
        self.assertEqual(projection["source"]["status"], "UNOBSERVED")
        self.assertEqual(projection["gap"]["status"], "OPEN")
        self.assertIn("SNAPSHOT_UNOBSERVED", projection["gap"]["codes"])
        self.assertEqual(projection["maturity"]["status"], "UNOBSERVED")

    def test_stale_fallback_and_quarantine_are_degraded(self) -> None:
        projection = build_market_data_research_projection(
            raw_truth(
                status="STALE",
                mode="FALLBACK",
                quote={"status": "QUARANTINED", "source": "SYNTHETIC"},
            )
        )
        self.assertEqual(projection["maturity"]["status"], "DEGRADED_OBSERVATION")
        self.assertEqual(
            projection["gap"]["codes"],
            ["OBSERVATION_STALE", "FALLBACK_SOURCE", "QUOTE_QUARANTINED"],
        )

    def test_revision_and_freshness_blocks_are_exposed_as_gaps(self) -> None:
        projection = build_market_data_research_projection(
            raw_truth(candles={"revision_status": "BLOCKED", "freshness_confirmed": False})
        )
        self.assertEqual(projection["gap"]["status"], "OPEN")
        self.assertIn("REVISION_BLOCKED", projection["gap"]["codes"])
        self.assertIn("CANDLE_FRESHNESS_UNCONFIRMED", projection["gap"]["codes"])
        self.assertEqual(projection["maturity"]["status"], "DEGRADED_OBSERVATION")

    def test_authority_alias_fails_closed_without_changing_permission(self) -> None:
        projection = build_market_data_research_projection(raw_truth(paper_authorized=1))
        self.assertIn("AUTHORITY_CONTRADICTION", projection["gap"]["codes"])
        self.assertEqual(projection["maturity"]["status"], "BLOCKED")
        self.assertFalse(projection["permission"]["paper_authorized"])
        self.assertFalse(projection["permission"]["live_order_allowed"])

    def test_non_native_values_do_not_invoke_subclass_methods(self) -> None:
        HostileStr.calls = HostileDict.calls = HostileList.calls = 0
        projection = build_market_data_research_projection(
            {
                "schema_version": "market-data-truth-v1",
                "status": HostileStr("READY"),
                "mode": HostileStr("REALTIME_READY"),
                "quote": HostileDict({"status": "QUARANTINED"}),
                "warnings": HostileList(["warning"]),
                "execution_usable": False,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        )
        self.assertEqual(projection["maturity"]["status"], "BLOCKED")
        self.assertEqual((HostileStr.calls, HostileDict.calls, HostileList.calls), (0, 0, 0))
        assert_no_ready(self, projection)

    def test_non_native_mode_alone_cannot_alias_current_observation(self) -> None:
        HostileStr.calls = 0
        projection = build_market_data_research_projection(
            raw_truth(mode=HostileStr("REALTIME_READY"))
        )
        self.assertIn("CONTRACT_MISMATCH", projection["gap"]["codes"])
        self.assertEqual(projection["maturity"]["status"], "BLOCKED")
        self.assertEqual(HostileStr.calls, 0)

    def test_non_native_top_level_mapping_is_rejected_without_method_calls(self) -> None:
        HostileDict.calls = 0
        projection = build_market_data_research_projection(HostileDict(raw_truth()))
        self.assertEqual(projection["maturity"]["status"], "BLOCKED")
        self.assertEqual(HostileDict.calls, 0)

    def test_service_finalizer_attaches_projection_and_preserves_raw_contract(self) -> None:
        @_with_market_data_research_projection
        def producer() -> dict[str, Any]:
            return raw_truth()

        payload = producer()
        self.assertEqual(payload["status"], "READY")
        self.assertEqual(payload["mode"], "REALTIME_READY")
        self.assertFalse(payload["execution_usable"])
        self.assertEqual(
            payload["research_projection"]["maturity"]["status"],
            "CURRENT_OBSERVATION",
        )

    def test_service_source_uses_single_finalizer_boundary(self) -> None:
        service_source = (
            BOT_ROOT / "exchange_terminal" / "services" / "market_data_service.py"
        ).read_text(encoding="utf-8")
        self.assertIn("@_with_market_data_research_projection\n    def data_truth(", service_source)
        self.assertEqual(service_source.count("@_with_market_data_research_projection"), 1)


if __name__ == "__main__":
    unittest.main()
