"""Fictional integration checks: real session engine, event lineage and Decimal ledger."""
import copy
import hashlib
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from test_equity_research import stock_snapshot, spec_document
from hakimi_research.documents import canonical_bytes, digest
from hakimi_research.equity_events import select_event_versions
from scripts.reconcile_research_ledger import reconcile
from tools.equity_content_study import FIXED_RISK, decisions, event_context, replay_cell, run_cell


def fixture(guidance="6.7"):
    snapshot = stock_snapshot()
    text = "Revenue $5.8 billion; next quarter guidance $" + guidance + " billion."
    facts = []
    for name, value, period, basis in [("actual_revenue", "5.8", "2024Q3", "GAAP"),
            ("next_revenue_guidance_midpoint", guidance, "2024Q4", "REVENUE_OUTLOOK")]:
        start = text.index(value)
        facts.append({"name": name, "value": value, "scale": "1000000000", "currency": "USD", "unit": "CURRENCY",
            "fiscal_period": period, "basis": basis, "status": "UNCERTAIN", "reason": "PENDING_HUMAN_SEMANTIC_REVIEW",
            "evidence": {"plain_text_start": start, "plain_text_end": start + len(value), "quote": value}})
    candidate = {"event_id": "SYNTHETIC:EARNINGS:Q3", "security_id": "SYNTHETIC:RESEARCH:TEST", "fiscal_quarter": "2024Q3",
        "version": 1, "prior_version_hash": None, "first_public_at": "2024-11-01T20:15:00Z",
        "retrieved_at": "2026-09-22T20:00:00Z", "extraction_completed_at": "2026-09-22T20:01:00Z",
        "source_url": "https://example.test/fictional", "raw_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "plain_text_sha256": hashlib.sha256(text.encode()).hexdigest(), "facts": facts}
    candidate["candidate_hash"] = digest(candidate)
    packet = {"events": [candidate]}; packet["packet_hash"] = digest(packet)
    approval = {"schema_version": "human-field-review-v1", "packet_hash": packet["packet_hash"],
        "decision": "APPROVED_LISTED_FIELDS", "reviewer_kind": "HUMAN_ATTESTATION", "reviewer": "SYNTHETIC_FIXTURE_ONLY",
        "source_user_confirmation": "Fictional test attestation; not market approval", "reviewed_at": "2026-09-24T00:00:00Z",
        "approved_candidate_hashes": [candidate["candidate_hash"]], "approved_fields": ["actual_revenue", "diluted_eps",
        "non_gaap_diluted_eps", "next_revenue_guidance_midpoint", "next_revenue_guidance_half_range", "first_public_at"]}
    spec = spec_document(snapshot, fee=.0008, slip=.0005); spec["risk"] = dict(FIXED_RISK)
    texts = {candidate["plain_text_sha256"]: text}
    return snapshot, spec, packet, approval, texts


def run(args, variant="D"):
    return run_cell(*args, event_id="SYNTHETIC:EARNINGS:Q3", variant=variant)


def revision(args, *, at, approved=False):
    snapshot, spec, packet, approval, texts = copy.deepcopy(args)
    row = copy.deepcopy(packet["events"][0]); row.pop("candidate_hash")
    row.update(version=2, prior_version_hash=packet["events"][0]["candidate_hash"], version_public_at=at)
    row["candidate_hash"] = digest(row); packet["events"].append(row)
    packet["packet_hash"] = digest({k: v for k, v in packet.items() if k != "packet_hash"})
    approval["packet_hash"] = packet["packet_hash"]
    if approved: approval["approved_candidate_hashes"].append(row["candidate_hash"])
    return snapshot, spec, packet, approval, texts


class ContentStudyTests(unittest.TestCase):
    def test_shared_engine_next_open_single_entry_and_decimal_ledger(self):
        args = fixture(); report = run(args)
        buys = [f for f in report["result"]["fills"] if f["action"] == "BUY"]
        self.assertEqual(len(buys), 1)
        self.assertEqual(buys[0]["fill_time"], "2024-11-05 14:30:00+00:00")
        self.assertEqual(buys[0]["signal_time"], "2024-11-04 21:01:00+00:00")
        self.assertEqual(reconcile(report, args[0].document)["status"], "PASS")
        self.assertFalse(report["execution_permission"]["order_allowed"])

    def test_disabled_D_is_byte_identical_C_result_including_engine_identity(self):
        args = fixture(guidance="5.3")
        self.assertEqual(canonical_bytes(run(args, "C")["result"]), canonical_bytes(run(args, "D_DISABLED")["result"]))
        self.assertEqual(run(args, "D")["result"]["fill_count"], 0)

    def test_unapproved_latest_version_blocks_without_old_favourable_fallback(self):
        args = revision(fixture(), at="2024-11-04T18:00:00Z")
        self.assertEqual(run(args)["result"]["fill_count"], 0)
        self.assertEqual(len([f for f in run(args, "C")["result"]["fills"] if f["action"] == "BUY"]), 1)

    def test_future_revision_does_not_change_earlier_decisions_or_fills(self):
        args = fixture(); future = revision(args, at="2025-01-01T00:00:00Z", approved=True)
        self.assertEqual(canonical_bytes(run(args)["result"]), canonical_bytes(run(future)["result"]))

    def test_source_change_and_incomplete_lineage_fail_closed(self):
        args = fixture(); args[-1][next(iter(args[-1]))] += "tampered"
        with self.assertRaisesRegex(ValueError, "source_changed"): run(args)
        args = list(fixture()); args[2]["events"][0]["version"] = 2
        with self.assertRaises(ValueError): run(args)

    def test_approval_scope_and_packet_binding_cannot_be_reused_after_edit(self):
        args = fixture(); args[3]["approved_fields"].pop()
        with self.assertRaisesRegex(ValueError, "scope"): run(args)
        args = fixture(); args[2]["events"][0]["facts"][0]["value"] = "1"
        with self.assertRaisesRegex(ValueError, "packet_hash"): run(args)

    def test_canonical_event_retains_real_retrieval_and_assumed_availability(self):
        _, _, packet, approval, texts = fixture()
        context = event_context(packet, approval, texts, event_id="SYNTHETIC:EARNINGS:Q3")
        event = select_event_versions(context["events"], "2024-11-01T20:17:00Z")[0]
        self.assertEqual(event["retrieved_at"], "2026-09-22T20:00:00Z")
        self.assertEqual(event["availability"]["available_at"], "2024-11-01T20:17:00Z")
        self.assertEqual(event["availability"]["available_at_kind"], "ASSUMED")
        self.assertFalse(event["authority"]["extraction_semantics_independently_verified"])

    def test_entry_outside_score_is_skipped_not_shifted(self):
        args = fixture(); args[1]["score_start_session"] = "2024-11-06"
        self.assertEqual(run(args)["result"]["fill_count"], 0)

    def test_tampered_result_rejected_and_same_inputs_replay(self):
        args = fixture(); report = run(args)
        receipt = replay_cell(report, *args)
        self.assertTrue(receipt["replay_verified"], receipt)
        report["result"]["final_equity"] += 1
        with self.assertRaisesRegex(ValueError, "report_hash"): replay_cell(report, *args)

    def test_same_cost_risk_and_security_required(self):
        for key, value in [("fee_rate", 0), ("initial_cash", 20000)]:
            args = fixture(); args[1][key] = value
            with self.assertRaisesRegex(ValueError, "fixed_input"): run(args)


if __name__ == "__main__": unittest.main()
