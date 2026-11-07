"""Synthetic offline contract tests; no Studio, market, Provider or engine calls."""
import copy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest

from hakimi_research.collaboration_schedule_adapter import (
    CONFIRMATION_VERSION, assess_schedule_import,
)
from hakimi_research.equity_event_context import build_event_context
from hakimi_research.equity_events import build_equity_event


FIXTURE = Path(__file__).with_name("fixtures") / "collaboration_schedule_result_synthetic.json"
SECURITY = "SYNTHETIC:EXAMPLE:COMMON"


def _studio_hash(value):
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True,
                     separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _event(previous=None, *, cancelled=False, synthetic_source=False):
    raw_text = "Fictional Example issuer: Q3 results on 2026-10-27 before the market opens."
    if cancelled:
        raw_text = "Fictional Example issuer: the Q3 result date is cancelled."
    raw = raw_text.encode("utf-8")
    version = 1 if previous is None else previous["version"] + 1
    public = "2026-09-29T14:00:00Z" if version == 1 else "2026-10-02T14:00:00Z"
    meta = {
        "event_id": "SYNTHETIC:EXAMPLE:2026Q3:SCHEDULE",
        "security_id": SECURITY,
        "event_kind": "EARNINGS_SCHEDULE",
        "version": version,
        "prior_version_hash": None if previous is None else previous["event_hash"],
        "source": {"url": "https://example.com/investors/earnings-schedule",
                   "kind": "SYNTHETIC_FIXTURE" if synthetic_source else "COMPANY_IR",
                   "document_type": "PRESS_RELEASE", "disclosure_items": [],
                   "official_source_status": "DECLARED_UNVERIFIED"},
        "first_public_at": "2026-09-29T14:00:00Z",
        "version_public_at": public,
        "publication_clock": {"status": "ATTESTED", "verification_method": "SYNTHETIC_TEST_DECLARATION",
                              "evidence": "This clock is fictional and used only in this isolated unit test."},
        "retrieved_at": "2026-10-03T00:00:00Z",
        "timing": {"mode": "HISTORICAL_RECONSTRUCTION", "received_at": None,
                   "extraction_completed_at": "2026-10-03T00:01:00Z",
                   "collection_delay_seconds": 1, "processing_delay_seconds": 1},
        "scheduled_release_at": None,
        "facts": [], "uncertainties": ["This is a fictional unit-test event."],
        "schedule": {"status": "CANCELLED" if cancelled else "ANNOUNCED",
                     "date": None if cancelled else "2026-10-27",
                     "time_precision": None if cancelled else "BEFORE_MARKET_OPEN",
                     "timezone": "America/New_York",
                     "evidence": [{"quote": raw_text}],
                     "reason": "Fictional cancellation" if cancelled else None},
    }
    return build_equity_event(raw, meta)


def _context(*, cancelled=False, synthetic_source=False):
    first = _event(synthetic_source=synthetic_source)
    events = [first]
    if cancelled:
        events.append(_event(first, cancelled=True))
    return _encoded(build_event_context(events, SECURITY))


def _result(context_raw):
    result = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload_sha = hashlib.sha256(context_raw).hexdigest()
    result["domain_context"]["payload_sha256"] = payload_sha
    domain = [row for row in result["source_manifest"] if row["source_kind"] == "domain_context"]
    assert len(domain) == 1
    domain[0]["record_sha256"] = payload_sha
    body = {k: v for k, v in result.items() if k not in {"result_id", "result_sha256"}}
    result["result_id"] = "result_" + _studio_hash(body)[:32]
    result["result_sha256"] = _studio_hash({k: v for k, v in result.items() if k != "result_sha256"})
    return _encoded(result)


def _confirmation(result_raw, context_raw, *, decision="ACCEPT_FOR_INPUT_CHECK", reason="I checked this exact input"):
    result = json.loads(result_raw)
    return _encoded({
        "version": CONFIRMATION_VERSION, "decision": decision, "actor": "synthetic-test-operator",
        "confirmed_at": "2026-10-22T00:00:00Z", "reason": reason,
        "result_sha256": result["result_sha256"],
        "context_file_sha256": hashlib.sha256(context_raw).hexdigest(), "security_id": SECURITY,
    })


class CollaborationScheduleAdapterTests(unittest.TestCase):
    def test_explicit_confirmation_yields_input_check_only_and_retains_lineage(self):
        context = _context(cancelled=True)
        result = _result(context)
        receipt = assess_schedule_import(result, context, _confirmation(result, context), expected_security_id=SECURITY)
        self.assertEqual(receipt["status"], "READY_FOR_EXPLICIT_INPUT_CHECK")
        self.assertEqual(receipt["reasons"], [])
        self.assertFalse(receipt["task_bound"])
        self.assertFalse(receipt["parameters_changed"])
        self.assertFalse(receipt["order_allowed"])
        self.assertEqual(receipt["new_economic_runs"], 0)
        self.assertEqual([v["schedule_status"] for v in receipt["event_versions"]], ["ANNOUNCED", "CANCELLED"])
        self.assertEqual(receipt["event_versions"][1]["prior_version_hash"], receipt["event_versions"][0]["event_hash"])
        self.assertEqual(receipt["event_versions"][0]["time_precision"], "BEFORE_MARKET_OPEN")
        self.assertEqual(receipt["event_versions"][0]["available_at_kind"], "ASSUMED")
        self.assertEqual(receipt["source_authentication"], "NOT_INDEPENDENTLY_VERIFIED")
        self.assertFalse(receipt["human_identity_authenticated"])

    def test_result_success_or_pending_user_boundary_is_not_confirmation(self):
        context = _context()
        result = _result(context)
        receipt = assess_schedule_import(result, context, None, expected_security_id=SECURITY)
        self.assertEqual(receipt["status"], "REJECTED")
        self.assertIn("MANUAL_CONFIRMATION_REQUIRED", receipt["reasons"])
        self.assertEqual(receipt["research_user_boundary"]["status"], "pending")

    def test_exact_context_bytes_and_explicit_decision_are_bound(self):
        context = _context()
        result = _result(context)
        confirmation = _confirmation(result, context)
        changed_context = context + b" "
        receipt = assess_schedule_import(result, changed_context, confirmation, expected_security_id=SECURITY)
        self.assertIn("EVENT_CONTEXT_BYTES_NOT_BOUND_TO_RESULT", receipt["reasons"])
        self.assertIn("MANUAL_CONFIRMATION_BINDING_MISMATCH", receipt["reasons"])
        rejected = assess_schedule_import(result, context, _confirmation(result, context, decision="REJECT", reason="Source clock unresolved"), expected_security_id=SECURITY)
        self.assertIn("MANUAL_REJECTION", rejected["reasons"])
        self.assertEqual(rejected["confirmation_declaration"]["reason"], "Source clock unresolved")

    def test_tampered_result_and_execution_claim_fail_closed(self):
        context = _context()
        result = json.loads(_result(context))
        result["profile"]["status"] = "invented"
        raw = _encoded(result)
        receipt = assess_schedule_import(raw, context, _confirmation(raw, context), expected_security_id=SECURITY)
        self.assertIn("RESULT_PROFILE_HASH_MISMATCH", receipt["reasons"])
        self.assertIn("RESULT_HASH_MISMATCH", receipt["reasons"])
        result = json.loads(_result(context))
        result["safety"]["live_trading_allowed"] = True
        raw = _encoded(result)
        receipt = assess_schedule_import(raw, context, _confirmation(raw, context), expected_security_id=SECURITY)
        self.assertIn("RESULT_EXECUTION_SAFETY_INVALID", receipt["reasons"])

    def test_wrong_security_and_synthetic_source_are_rejected(self):
        context = _context()
        result = _result(context)
        receipt = assess_schedule_import(result, context, _confirmation(result, context), expected_security_id="US.OTHER")
        self.assertIn("EVENT_SECURITY_MISMATCH", receipt["reasons"])
        context = _context(synthetic_source=True)
        result = _result(context)
        receipt = assess_schedule_import(result, context, _confirmation(result, context), expected_security_id=SECURITY)
        self.assertIn("SYNTHETIC_EVENT_NOT_ADMISSIBLE", receipt["reasons"])

    def test_missing_raw_context_and_review_concern_are_rejected(self):
        context = _context()
        result = _result(context)
        receipt = assess_schedule_import(result, None, None, expected_security_id=SECURITY)
        self.assertIn("EVENT_CONTEXT_INVALID_OR_MISSING", receipt["reasons"])
        changed = json.loads(result)
        changed["independent_review"]["status"] = "blocked"
        body = {k: v for k, v in changed.items() if k not in {"result_id", "result_sha256"}}
        changed["result_id"] = "result_" + _studio_hash(body)[:32]
        changed["result_sha256"] = _studio_hash({k: v for k, v in changed.items() if k != "result_sha256"})
        raw = _encoded(changed)
        receipt = assess_schedule_import(raw, context, _confirmation(raw, context), expected_security_id=SECURITY)
        self.assertIn("RESEARCH_REVIEW_CONCERN_OR_INVALID", receipt["reasons"])


if __name__ == "__main__":
    unittest.main()
