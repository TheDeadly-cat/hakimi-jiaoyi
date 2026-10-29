"""Nine-rule diagnostics over fabricated, locally validated native QA bars.

No actual market data, provider, broker, report rewrite or economic run.
"""
from copy import deepcopy
from datetime import datetime, timezone
import math
import unittest
from unittest.mock import patch

from exchange_terminal.services import indicator_math, strategy_signals as signals
from exchange_terminal.services.backtest_engine import prepare_backtest_dataset
from exchange_terminal.services.market_calendar import _exchange_sessions
from exchange_terminal.services.terminal_research import _engine_source_identity, _seal, validate_terminal_strategy_params
from exchange_terminal.services.terminal_strategy_candidates import CATALOG_ORDER, diagnose_strategy, recommend_candidates


OBSERVED = "2024-08-11T00:00:00Z"
SOURCE = "QA simulated ordinary import provider"
SESSIONS = _exchange_sessions("XNYS", "2024-01-02", "2024-07-31")[0][-130:]


def native(prices=None, *, count=130, last_volume=1000):
    sessions = deepcopy(SESSIONS[-count:])
    prices = list(prices) if prices is not None else [100.0 + index * .1 for index in range(count)]
    rows = []
    for index, (session, close) in enumerate(zip(sessions, prices)):
        opened = datetime.fromisoformat(session["open_utc"].replace("Z", "+00:00"))
        rows.append({"date":session["date"],"ts_ms":int(opened.timestamp()*1000),"open":close,"high":close+1,"low":close-1,
                     "close":close,"volume":last_volume if index == len(sessions)-1 else 1000,
                     "source":SOURCE,"complete":True,"provisional":False})
    prepared = prepare_backtest_dataset(rows, symbol="QADEMO", source=SOURCE, timeframe="1D", minimum_rows=1, market="stock")
    if prepared["manifest"]["status"] != "PASS":
        raise AssertionError(prepared["manifest"]["blockers"])
    return _seal({"schema_version":"hakimi-terminal-input-v1","symbol":"QADEMO","bar":"1D","source_id":"qa:ordinary-import",
        "source":SOURCE,"source_digest":"a"*64,"rows":rows,"quality":{"status":"REVIEW","blockers":[],"source_authenticated":False},
        "meta":{"asset_class":"US_EQUITY","currency":"USD","timezone":"America/New_York","session":"REGULAR",
                "source_lineage":[SOURCE],"sessions":sessions,"bar_availability_lag_seconds":60,
                "price_basis":"RAW_UNADJUSTED","as_of":"2024-08-09T00:00:00Z","retrieved_at":"2024-08-10T00:00:00Z",
                "evidence_kind":"IMPORTED_UNVERIFIED"},"permissions":{"research_only":True,"paper_allowed":False,"live_allowed":False,"order_allowed":False}})


def spec(identity, overrides=None):
    # volume_trend uses current catalog declarations rather than its fallback
    # fast20/breakout40/exit20; remaining effective parameters use the validator.
    declared = {"trend_window":100,"fast_window":50,"breakout_window":20,"exit_window":10,"volume_window":20,"volume_ratio":1.1} if identity == "volume_trend" else {}
    params = validate_terminal_strategy_params({"id":identity,"params":declared}, overrides or {})
    return {"id":identity,"name":identity,"params":params,"engine_id":"terminal."+signals.SIGNAL_ENGINE_VERSION,
            "fingerprint":signals.strategy_signal_fingerprint(identity,params),"engine_source_identity":_engine_source_identity()}


def diagnose(identity, record=None, *, holding=False, overrides=None, cutoff=None, position=None):
    record = record or native()
    return diagnose_strategy(record, spec(identity,overrides), cutoff_session=cutoff or record["rows"][-1]["date"],
                             observed_at=OBSERVED, position_context=position or {"has_position":holding})


def reseal(record):
    return _seal({key:value for key,value in record.items() if key != "id"})


class TerminalStrategyCandidatesTests(unittest.TestCase):
    def setUp(self):
        self.socket = patch("socket.socket.connect",side_effect=AssertionError("No network")).start()
        self.runner = patch("exchange_terminal.services.backtest_engine.run_causal_long_only_backtest",side_effect=AssertionError("No economic run")).start()
        self.addCleanup(patch.stopall)

    def test_all_nine_entry_and_held_exit_decisions_match_actual_engine(self):
        flat = [100.0]*130
        rising = [100+index*.2 for index in range(130)]
        falling = list(reversed(rising))
        volume = [100+index*.05 for index in range(130)]
        examples = {
            "dual_ma":(rising,falling),"bollinger":(flat[:-1]+[50],flat[:-1]+[110]),
            "macd":([100+index*index*.02 for index in range(130)],[250-index*index*.005 for index in range(130)]),
            "rsi":(falling,rising),"momentum":(flat[:-1]+[105],flat[:-1]+[95]),
            "livermore":(flat[:-1]+[101],flat[:-1]+[99]),"turtle":(flat[:-1]+[101],flat[:-1]+[99]),
            "darvas":(flat[:-1]+[101],flat[:-1]+[99]),"volume_trend":(volume[:-1]+[volume[-1]+3],volume[:-1]+[volume[-1]-5])}
        for identity in CATALOG_ORDER:
            for holding, prices, expected in ((False,examples[identity][0],"BUY"),(True,examples[identity][1],"EXIT")):
                with self.subTest(identity=identity,holding=holding):
                    record = native(prices,last_volume=1100)
                    result = diagnose(identity,record,holding=holding)
                    self.assertEqual(result["status"],"READY",result["blockers"])
                    self.assertEqual(result["signal"]["action"],expected,result["signal"])
                    self.assertTrue(result["decision_matches_factors"])
                    self.assertTrue(all(factor["passed"] for factor in result["factors"] if factor["applies_to_position"]))
                    self.assertEqual(result["group"],"EXIT_MATCH" if holding else "ENTRY_MATCH")
                    self.assertEqual(result["position_cost_status"],"UNRECORDED")
                    self.assertNotIn("entry_price",result["position_context"])
                    self.assertFalse(result["position_cost_used_by_rule"])
                    self.assertFalse(result["freshness"]["immediate_execution_eligible"])
                    self.assertFalse(result["freshness"]["live_quote_verified"])
        self.runner.assert_not_called()
        self.socket.assert_not_called()

    def test_strict_threshold_equality_holds_for_eight_close_rules(self):
        flat = [100.0]*130
        cases = [("dual_ma",flat,False,{}),("dual_ma",flat,True,{}),
            ("bollinger",flat,False,{}),("bollinger",flat,True,{}),("macd",flat,False,{}),("macd",flat,True,{}),
            ("rsi",flat,False,{"oversold":50}),("rsi",flat,True,{"overbought":50}),
            ("livermore",flat[:-1]+[100*(1+.006)],False,{}),("livermore",flat[:-1]+[100*.995],True,{}),
            ("turtle",flat,False,{}),("turtle",flat,True,{}),
            ("darvas",flat[:-1]+[100*(1+.004)],False,{}),("darvas",flat,True,{})]
        for holding,last in ((False,101.5),(True,98.5)):
            value = last/100-1
            cases.append(("momentum",flat[:-1]+[last],holding,{"threshold":abs(value)}))
        for identity,prices,holding,overrides in cases:
            with self.subTest(identity=identity,holding=holding):
                result = diagnose(identity,native(prices),holding=holding,overrides=overrides)
                self.assertEqual(result["signal"]["action"],"HOLD")
                self.assertTrue(result["decision_matches_factors"])

    def test_volume_inclusive_boundaries_use_unrounded_values_not_rounded_engine_evidence(self):
        prices = [100+index*.05 for index in range(130)]
        prices[-1] += 3
        record = native(prices,last_volume=1100)
        first = diagnose("volume_trend",record)
        values = {factor["key"]:factor["value"] for factor in first["factors"]}
        settings = {"volume_ratio":values["volume_confirmed"],"min_atr_pct":values["volatility_valid"],
                    "max_atr_pct":values["volatility_valid"],"max_extension_pct":values["not_overextended"]}
        edge = diagnose("volume_trend",record,overrides=settings)
        self.assertEqual(edge["signal"]["action"],"BUY")
        self.assertTrue(all(edge["signal"]["checks"].values()))
        below = diagnose("volume_trend",record,overrides={**settings,"max_extension_pct":math.nextafter(settings["max_extension_pct"],-math.inf)})
        self.assertEqual(below["signal"]["action"],"HOLD")
        self.assertFalse(next(row for row in below["factors"] if row["key"] == "not_overextended")["passed"])
        self.assertEqual(below["signal"]["evidence"]["extension_pct"],edge["signal"]["evidence"]["extension_pct"])
        self.assertTrue(below["decision_matches_factors"])

    def test_negative_momentum_threshold_and_current_ma_relation_are_not_cross_claims(self):
        record = native([100.0]*129+[99.5])
        result = diagnose("momentum",record,holding=True)
        self.assertEqual(result["signal"]["action"],"HOLD")
        exit_factor = next(row for row in result["factors"] if row["role"] == "EXIT")
        self.assertEqual(exit_factor["threshold"],-.015)
        self.assertGreater(exit_factor["value"],exit_factor["threshold"])
        result = diagnose("dual_ma",native())
        self.assertEqual(result["signal"]["reason"],"fast_ma_above_slow_ma")
        self.assertNotIn("cross",str(result["factors"]))

    def test_cutoff_prefix_and_position_changes_bind_diagnostics_without_future_leakage(self):
        record = native()
        cutoff = record["rows"][90]["date"]
        before = deepcopy(record)
        first = diagnose("dual_ma",record,cutoff=cutoff)
        changed = deepcopy(record)
        for row in changed["rows"][91:]:
            for key in ("open","high","low","close"):
                row[key] += 1000
        changed = reseal(changed)
        second = diagnose("dual_ma",changed,cutoff=cutoff)
        self.assertEqual(first["signal"],second["signal"])
        self.assertEqual(first["factors"],second["factors"])
        self.assertNotEqual(first["diagnostic_id"],second["diagnostic_id"])
        self.assertEqual(record,before)
        held = diagnose("dual_ma",record,cutoff=cutoff,holding=True)
        self.assertEqual(held["signal"]["action"],"HOLD")
        self.assertNotEqual(first["diagnostic_id"],held["diagnostic_id"])

    def test_short_history_has_actual_factors_but_never_becomes_entry_candidate(self):
        short = native(count=60)
        result = diagnose("dual_ma",short)
        self.assertEqual(result["group"],"INSUFFICIENT")
        self.assertEqual(result["missing_rows"],22)
        self.assertEqual(result["required_rows"],82)
        self.assertEqual(result["signal"]["action"],"BUY")
        self.assertEqual(result["factors"][0]["status"],"AVAILABLE")
        volume = diagnose("volume_trend",short)
        self.assertEqual(volume["required_rows"],107)
        self.assertEqual(volume["missing_rows"],47)
        self.assertTrue(any(row["passed"] is None for row in volume["factors"]))
        self.assertTrue(volume["decision_matches_factors"])
        minimal = diagnose("rsi",native(count=2))
        self.assertIsNone(minimal["factors"][0]["value"])
        self.assertEqual(minimal["factors"][0]["threshold"],30)
        self.assertIsNone(minimal["factors"][0]["passed"])
        one = diagnose("macd",native(count=1))
        self.assertTrue(all(row["value"] is None for row in one["factors"]))

    def test_fixed_groups_and_catalog_order_have_no_first_choice_or_performance_score(self):
        record = native([100.0]*129+[105],last_volume=1200)
        diagnostics = [diagnose(identity,record) for identity in reversed(CATALOG_ORDER)]
        groups = recommend_candidates(diagnostics)
        self.assertEqual([row["label"] for row in groups["groups"]],["满足开仓规则的候选","满足退出规则的候选","暂时等待","资料不足"])
        self.assertIsNone(groups["selected_strategy_id"])
        self.assertEqual(groups["historical_performance"]["status"],"NOT_ASSESSED")
        for group in groups["groups"]:
            indexes = [CATALOG_ORDER.index(row["strategy_id"]) for row in group["items"]]
            self.assertEqual(indexes,sorted(indexes))
            for item in group["items"]:
                self.assertNotIn("score",item)
                self.assertNotIn("win_rate",item)
        with self.assertRaisesRegex(ValueError,"mixed_data"):
            recommend_candidates([diagnostics[0],diagnose("dual_ma",native())])

    def test_partial_or_tampered_inputs_invalid_time_and_session_gaps_do_not_get_diagnosed(self):
        base = native()
        broken = deepcopy(base)
        broken["rows"][0]["close"] += .1
        with self.assertRaisesRegex(ValueError,"verified_raw_native"):
            diagnose("dual_ma",broken)
        changes = [lambda value:value["rows"].__setitem__(0,"malformed"),
            lambda value:value["rows"][0].update(complete=False),
            lambda value:value["rows"][0].update(provisional=True),
            lambda value:value["rows"][1].update(date=value["rows"][0]["date"]),
            lambda value:value["rows"][0].update(high=1),
            lambda value:value["rows"][0].update(source="other"),
            lambda value:value["rows"].pop(1)]
        for index,change in enumerate(changes):
            value = deepcopy(base)
            change(value)
            with self.subTest(index=index),self.assertRaises(ValueError):
                diagnose("dual_ma",reseal(value))
        with self.assertRaisesRegex(ValueError,"observed_before_retained"):
            diagnose_strategy(base,spec("dual_ma"),cutoff_session=base["rows"][-1]["date"],observed_at="2024-08-01T00:00:00Z",position_context={"has_position":False})
        with self.assertRaises(ValueError):
            diagnose_strategy(base,spec("dual_ma"),cutoff_session=base["rows"][-1]["date"],observed_at="2024-08-11T00:00:00",position_context={"has_position":False})

    def test_real_signal_mismatch_is_blocked_not_hidden_by_diagnostic_math(self):
        with patch.object(signals,"build_strategy_signal_fn",return_value=lambda *args:{"action":"BUY","reason":"changed_rule"}):
            result = diagnose("dual_ma",native([100.0]*130))
        self.assertEqual(result["status"],"DIAGNOSTIC_MISMATCH")
        self.assertEqual(result["group"],"INSUFFICIENT")
        self.assertFalse(result["decision_matches_factors"])

    def test_exit_group_requires_actual_position_exit_and_no_data_blocker(self):
        full = native([100.0]*129+[95])
        held = diagnose("momentum",full,holding=True)
        flat = diagnose("momentum",full,holding=False)
        short = diagnose("momentum",native([100.0]*59+[95],count=60),holding=True)
        self.assertEqual(held["group"],"EXIT_MATCH")
        self.assertEqual(flat["group"],"WAITING")
        self.assertEqual(short["signal"]["action"],"EXIT")
        self.assertEqual(short["group"],"INSUFFICIENT")
        groups = recommend_candidates([held])
        self.assertEqual(groups["groups"][1]["label"],"满足退出规则的候选")
        self.assertEqual(groups["groups"][1]["items"],[held])

    def test_completion_clock_cutoff_freshness_and_unavailable_metadata_stay_distinct(self):
        record = native()
        clocked = deepcopy(record)
        clocked["meta"]["as_of"] = "2024-07-31T18:00:00Z"
        clocked["meta"]["retrieved_at"] = "2024-07-31T18:00:00Z"
        with self.assertRaisesRegex(ValueError,"not_yet_available"):
            diagnose_strategy(reseal(clocked),spec("dual_ma"),cutoff_session=record["rows"][-1]["date"],
                              observed_at="2024-07-31T18:00:00Z",position_context={"has_position":False})
        missing = deepcopy(record)
        for key in ("sessions","bar_availability_lag_seconds","as_of","retrieved_at"):
            missing["meta"].pop(key)
        result = diagnose("dual_ma",reseal(missing))
        self.assertIsNone(result["freshness"]["last_bar_available_at"])
        self.assertIsNone(result["freshness"]["elapsed_seconds_since_bar_available"])
        self.assertFalse(result["freshness"]["live_quote_verified"])
        self.assertIsNone(result["freshness"]["trading_session_age"])
        today = diagnose_strategy(reseal(missing),spec("dual_ma"),cutoff_session=record["rows"][-1]["date"],
                                  observed_at="2024-07-31T22:00:00Z",position_context={"has_position":False})
        self.assertIn("CURRENT_DAY_COMPLETION_CLOCK_UNRECORDED",today["blockers"])
        self.assertEqual(today["group"],"INSUFFICIENT")

    def test_current_spec_and_explicit_position_are_required_and_defaults_are_not_silently_added(self):
        record = native()
        value = spec("dual_ma")
        for change in (lambda item:item.update(id="grid"),lambda item:item.update(engine_id="terminal.causal-long-only-signals-v6"),
                       lambda item:item.update(params={}),lambda item:item["engine_source_identity"].update(**{"indicator_math.py":"f"*64})):
            edited = deepcopy(value)
            change(edited)
            with self.assertRaises(ValueError):
                diagnose_strategy(record,edited,cutoff_session=record["rows"][-1]["date"],observed_at=OBSERVED,position_context={"has_position":False})
        for position in ({},{"has_position":0},{"has_position":True,"entry_price":0}):
            with self.assertRaisesRegex(ValueError,"position_context"):
                diagnose_strategy(record,value,cutoff_session=record["rows"][-1]["date"],observed_at=OBSERVED,position_context=position)
        result = diagnose("dual_ma",record,position={"has_position":True,"entry_price":110})
        self.assertEqual(result["position_cost_status"],"RECORDED")
        self.assertNotIn("stop_loss_price",result)
        self.assertEqual(result["freshness"]["context"],"SAVED_HISTORICAL_INPUT")
        self.assertIsNone(result["freshness"]["trading_session_age"])
        self.assertGreater(result["freshness"]["elapsed_seconds_since_bar_available"],0)


if __name__ == "__main__":
    unittest.main()
