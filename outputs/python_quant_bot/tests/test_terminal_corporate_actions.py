"""Pure synthetic split fixtures. No real event acceptance or economic runner."""
from copy import deepcopy
from datetime import datetime
from fractions import Fraction
from hashlib import sha256
import json
import unittest
from zoneinfo import ZoneInfo

from exchange_terminal.services.terminal_corporate_actions import (
    ACTION_SCHEMA, CorporateActionError, QUANTITY_POLICY, advance_action_session,
    indicator_history_as_of, inspect_action, new_action_state,
)


CALENDAR = {"timezone": "America/New_York", "sessions": ["2026-10-01", "2026-10-02", "2026-10-05", "2026-10-06", "2026-10-07"]}


def signature(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def action(identity="synthetic-split-1", session="2026-10-02", numerator=2, denominator=1, *, kind="SPLIT", raw_extra=None):
    stamp = int(datetime.fromisoformat(session + "T09:30:00").replace(tzinfo=ZoneInfo(CALENDAR["timezone"])).timestamp())
    raw = {"date": stamp, "numerator": numerator, "denominator": denominator} if kind == "SPLIT" else {"date": stamp, "amount": .31}
    raw.update(raw_extra or {})
    raw_json = json.dumps(raw, separators=(",", ":"), ensure_ascii=False)
    source = {"provider": "SYNTHETIC_TEST_SOURCE", "reference": "urn:synthetic:corporate-action:" + identity,
        "retrieved_at": "2026-10-07T22:00:00Z", "security_id": "QA:TEST", "currency": "USD",
        "raw_event_id": str(stamp), "raw_json": raw_json, "raw_sha256": sha256(raw_json.encode()).hexdigest()}
    document = {"schema_version": ACTION_SCHEMA, "action_id": identity, "action_type": kind,
        "security_id": "QA:TEST", "currency": "USD", "effective_session": session,
        "evidence_kind": "SYNTHETIC_TEST", "source": source}
    if kind == "SPLIT":
        document.update(numerator=numerator, denominator=denominator, distribution_conditions="NONE_DECLARED")
    return document


def state(**changes):
    history = [{"session": day, "open": price, "high": price, "low": price, "close": price, "volume": "1000"}
               for day, price in zip(CALENDAR["sessions"], ("100", "50", "50", "25", "9999"))]
    options = dict(owner_id="owner-a", security_id="QA:TEST", currency="USD", calendar=CALENDAR,
        as_of_session="2026-10-01", cash="1000.00", quantity="10", unit_cost="90", entry_fees="2",
        stop_price="80", target_price="110", indicator_history=history)
    options.update(changes)
    return new_action_state(**options)


class CorporateActionTests(unittest.TestCase):
    def test_source_bound_split_adjusts_position_cost_and_protection_without_cash_or_fee_change(self):
        original, split = state(), action()
        before = signature([original, split])
        reviewed = inspect_action(split, CALENDAR)
        self.assertEqual(reviewed["status"], "SUPPORTED")
        self.assertFalse(reviewed["source_authenticated"])
        self.assertEqual(reviewed["real_source_acceptance"], "PENDING")
        advanced = advance_action_session(original, [split], "2026-10-02")
        position = advanced["state"]["position"]
        self.assertEqual(position, {"owner_id": "owner-a", "security_id": "QA:TEST", "quantity": "20",
            "unit_cost": "45", "entry_fees": "2", "stop_price": "40", "target_price": "55"})
        self.assertEqual(advanced["state"]["cash"], "1000")
        self.assertEqual(advanced["receipt"]["cost_basis_before"], "900")
        self.assertEqual(advanced["receipt"]["cost_basis_after"], "900")
        self.assertEqual(advanced["state"]["quantity_policy"], QUANTITY_POLICY)
        self.assertEqual(signature([original, split]), before)
        self.assertEqual(advanced["state"]["raw_indicator_history"], original["raw_indicator_history"])
        self.assertFalse(advanced["state"]["permissions"]["old_runner_admission_allowed"])

    def test_reverse_and_three_for_one_splits_preserve_exact_fractions_and_cost(self):
        for numerator, denominator, quantity, unit, stop in ((1, 3, "10/3", "270", "240"), (3, 1, "30", "30", "80/3")):
            with self.subTest(ratio=(numerator, denominator)):
                out = advance_action_session(state(), [action(numerator=numerator, denominator=denominator)], "2026-10-02")
                p = out["state"]["position"]
                self.assertEqual((p["quantity"], p["unit_cost"], p["stop_price"]), (quantity, unit, stop))
                self.assertEqual(Fraction(p["quantity"]) * Fraction(p["unit_cost"]), 900)
                self.assertEqual(out["state"]["cash"], "1000")
                view = indicator_history_as_of(out["state"], "2026-10-02")
                self.assertEqual(Fraction(view["rows"][0]["close"]) * Fraction(p["quantity"]), 1000)

    def test_future_events_and_rows_cannot_change_earlier_indicator_view_or_holdings(self):
        initial = state()
        first = advance_action_session(initial, [action(session="2026-10-05")], "2026-10-02")["state"]
        self.assertEqual(first["position"], initial["position"])
        before_view = indicator_history_as_of(first, "2026-10-02")
        self.assertEqual(len(before_view["rows"]), 2)
        self.assertEqual(before_view["rows"][0]["close"], "100")
        second = advance_action_session(first, [], "2026-10-05")["state"]
        self.assertEqual(second["position"]["quantity"], "20")
        self.assertEqual(indicator_history_as_of(second, "2026-10-02"), before_view)
        current = indicator_history_as_of(second, "2026-10-05")
        self.assertEqual([row["close"] for row in current["rows"]], ["50", "25", "50"])
        self.assertEqual([row["volume"] for row in current["rows"]], ["2000", "2000", "1000"])
        with self.assertRaisesRegex(CorporateActionError, "already_processed"):
            indicator_history_as_of(second, "2026-10-07")

    def test_strict_next_session_and_unprocessed_historical_events_fail_without_mutation(self):
        original = state(); before = signature(original)
        for target in ("2026-10-01", "2026-09-30", "2026-10-05", "2026-10-03"):
            with self.subTest(target=target), self.assertRaisesRegex(CorporateActionError, "one_declared_trading_day"):
                advance_action_session(original, [], target)
        advanced = advance_action_session(original, [], "2026-10-02")["state"]
        with self.assertRaisesRegex(CorporateActionError, "unprocessed_historical_action"):
            advance_action_session(advanced, [action()], "2026-10-05")
        self.assertEqual(signature(original), before)
        weekend = action(session="2026-10-03")
        self.assertIn("action_effective_session_not_in_declared_calendar", inspect_action(weekend, CALENDAR)["reasons"])

    def test_replay_is_once_only_and_changed_or_aliased_source_events_are_rejected(self):
        split = action()
        advanced = advance_action_session(state(), [split, deepcopy(split)], "2026-10-02")["state"]
        repeated = advance_action_session(advanced, [split], "2026-10-05")
        self.assertEqual(repeated["state"]["position"]["quantity"], "20")
        self.assertEqual(repeated["receipt"]["applied"], [])
        self.assertEqual(repeated["receipt"]["replayed_action_ids"], [split["action_id"]])
        with self.assertRaisesRegex(CorporateActionError, "identity_content_conflict"):
            advance_action_session(advanced, [action(numerator=3)], "2026-10-05")
        alias = deepcopy(split); alias["action_id"] = "same-source-another-id"
        with self.assertRaisesRegex(CorporateActionError, "multiple_action_ids"):
            advance_action_session(advanced, [alias], "2026-10-05")
        other_provider = action("other-provider")
        other_provider["source"]["provider"] = "ANOTHER_SYNTHETIC_SOURCE"
        with self.assertRaisesRegex(CorporateActionError, "multiple_split_events_same_session"):
            advance_action_session(state(), [split, other_provider], "2026-10-02")

    def test_source_bytes_ratio_and_special_distribution_conditions_must_be_explicit(self):
        cases = []
        changed = action(); changed["source"]["raw_json"] += " "; cases.append((changed, "bytes_hash_mismatch"))
        changed = action(); changed["numerator"] = 3; cases.append((changed, "ratio_missing_or_conflicting"))
        cases.append((action(numerator=True), "positive_integer_ratio"))
        cases.append((action(denominator=0), "positive_integer_ratio"))
        cases.append((action(raw_extra={"splitRatio": "3:1"}), "ratio_text_conflict"))
        cases.append((action(raw_extra={"cashInLieu": True}), "special_or_unknown_fields"))
        changed = action(); changed["distribution_conditions"] = "CASH_IN_LIEU"; cases.append((changed, "cash_in_lieu_unsupported"))
        changed = action(); changed["source"]["currency"] = "EUR"; cases.append((changed, "security_or_currency_conflict"))
        for split, reason in cases:
            with self.subTest(reason=reason):
                result = inspect_action(split, CALENDAR)
                self.assertEqual(result["status"], "UNSUPPORTED")
                self.assertIn(reason, ";".join(result["reasons"]))
        valid = action(raw_extra={"splitRatio": "4:2"})
        self.assertEqual(inspect_action(valid, CALENDAR)["status"], "SUPPORTED")

    def test_cash_dividend_always_stays_diagnostic_without_entitlement_receivable_or_payment(self):
        dividend = action(kind="CASH_DIVIDEND")
        reviewed = inspect_action(dividend, CALENDAR)
        self.assertEqual(reviewed["status"], "UNSUPPORTED")
        for key in ("entitlement_rule", "ex_session", "payment_session", "payment_source", "amount_per_share"):
            self.assertIn("DIVIDEND_NOT_RECORDED:" + key, reviewed["reasons"])
        complete = {**dividend, "entitlement_rule": "DECLARED_FIXTURE_ONLY", "ex_session": "2026-10-02",
                    "payment_session": "2026-10-07", "payment_source": {"reference": "urn:synthetic:payment"}, "amount_per_share": "0.31"}
        self.assertEqual(inspect_action(complete, CALENDAR)["status"], "UNSUPPORTED")
        initial = state(); before = signature(initial)
        with self.assertRaisesRegex(CorporateActionError, "CASH_DIVIDEND_ACCOUNTING_UNSUPPORTED"):
            advance_action_session(initial, [complete], "2026-10-02")
        self.assertEqual(signature(initial), before)
        self.assertNotIn("receivables", initial)
        self.assertEqual(initial["cash"], "1000")
        incomplete = deepcopy(dividend); incomplete.pop("currency")
        self.assertIn("DIVIDEND_NOT_RECORDED:currency", inspect_action(incomplete, CALENDAR)["reasons"])

    def test_unsupported_same_day_batch_has_no_partial_split_and_future_dividend_has_no_effect(self):
        original = state(); before = signature(original)
        with self.assertRaisesRegex(CorporateActionError, "unsupported_due"):
            advance_action_session(original, [action(), action("dividend", kind="CASH_DIVIDEND")], "2026-10-02")
        self.assertEqual(signature(original), before)
        future = advance_action_session(original, [action("future-dividend", session="2026-10-07", kind="CASH_DIVIDEND")], "2026-10-02")["state"]
        self.assertEqual(future["cash"], original["cash"])
        self.assertEqual(future["position"], original["position"])
        self.assertNotIn("receivables", future)

    def test_old_state_tamper_wrong_security_and_nonexact_numbers_cannot_enter_adapter(self):
        with self.assertRaisesRegex(CorporateActionError, "old_runner_state_rejected"):
            advance_action_session({"cash": 10000, "position_qty": 10}, [], "2026-10-02")
        changed = state(); changed["cash"] = "2000"
        with self.assertRaisesRegex(CorporateActionError, "state_hash_mismatch"):
            advance_action_session(changed, [], "2026-10-02")
        foreign = action(); foreign["security_id"] = "QA:OTHER"
        with self.assertRaisesRegex(CorporateActionError, "security_or_currency_conflict"):
            advance_action_session(state(), [foreign], "2026-10-02")
        for value in (10.0, "NaN", "-1", "1/0", True):
            with self.subTest(value=value), self.assertRaises(CorporateActionError):
                state(quantity=value)

    def test_flat_position_and_chain_of_distinct_session_splits_preserve_declared_policy(self):
        flat = state(quantity="0", unit_cost="0", entry_fees="0", stop_price=None, target_price=None)
        flat_after = advance_action_session(flat, [action()], "2026-10-02")["state"]
        self.assertEqual(flat_after["position"]["quantity"], "0")
        self.assertEqual(flat_after["cash"], "1000")
        first = advance_action_session(state(), [action(numerator=3)], "2026-10-02")["state"]
        second = advance_action_session(first, [action("reverse", session="2026-10-05", numerator=1, denominator=3)], "2026-10-05")["state"]
        self.assertEqual(second["position"], state()["position"])
        self.assertFalse(second["permissions"]["order_allowed"])
        self.assertFalse(second["permissions"]["old_runner_admission_allowed"])


if __name__ == "__main__":
    unittest.main()
