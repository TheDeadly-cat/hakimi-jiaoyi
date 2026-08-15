from __future__ import annotations

import base64
from copy import deepcopy
from datetime import date, timedelta
import hashlib
import json
import unittest
import zlib

from exchange_terminal.services.market_data_revision_ledger import (
    build_cross_source_evidence,
    build_market_data_snapshot,
)
from exchange_terminal.services.portfolio_evidence_bundle import (
    PortfolioEvidenceBundleError,
    expand_portfolio_evidence_bundle,
    pack_portfolio_evidence_bundle,
    verify_portfolio_evidence_bundle,
)


def _rows(multiplier: float) -> list[dict[str, object]]:
    start = date(2025, 1, 1)
    rows: list[dict[str, object]] = []
    for index in range(40):
        close = (100.0 + index) * multiplier
        rows.append({
            "date": (start + timedelta(days=index)).isoformat(),
            "open": close - 0.5,
            "high": close + 1.0,
            "low": close - 1.0,
            "close": close,
            "volume": 1_000_000 + index,
            "complete": True,
        })
    return rows


def _evidence() -> dict[str, object]:
    primary = build_market_data_snapshot(
        symbol="AAPL",
        provider="futu",
        rows=_rows(1.0),
        adjustment_basis="FORWARD_ADJUSTED",
    )
    secondary = build_market_data_snapshot(
        symbol="AAPL",
        provider="yahoo",
        rows=_rows(1.0),
        adjustment_basis="FORWARD_ADJUSTED",
    )
    return build_cross_source_evidence(primary, secondary, required_overlap=30)


def _payload() -> dict[str, object]:
    evidence = _evidence()
    return {
        "first": {"cross_source": [deepcopy(evidence)]},
        "second": {"cross_source": [deepcopy(evidence)]},
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def _canonical_bytes(payload: object) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _canonical_hash(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


class PortfolioEvidenceBundleTests(unittest.TestCase):
    def test_bundle_deduplicates_and_round_trips_exactly(self) -> None:
        original = _payload()
        compact = pack_portfolio_evidence_bundle(original)
        expanded, audit = expand_portfolio_evidence_bundle(compact, require_bundle=True)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["entry_count"], 2)
        self.assertEqual(audit["reference_count"], 4)
        self.assertEqual(expanded, original)
        original_size = len(json.dumps(original, ensure_ascii=False, indent=2).encode("utf-8"))
        compact_size = len(json.dumps(compact, ensure_ascii=False, indent=2).encode("utf-8"))
        self.assertLess(compact_size, original_size * 0.65)

    def test_packing_is_deterministic_and_idempotent(self) -> None:
        first = pack_portfolio_evidence_bundle(_payload())
        second = pack_portfolio_evidence_bundle(_payload())
        third = pack_portfolio_evidence_bundle(first)

        self.assertEqual(first, second)
        self.assertEqual(first, third)

    def test_bundle_supports_shared_cross_source_object_aliases(self) -> None:
        evidence = _evidence()
        original = {
            "first": {"cross_source": [evidence]},
            "second": {"cross_source": [evidence]},
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

        compact = pack_portfolio_evidence_bundle(original)
        expanded, audit = expand_portfolio_evidence_bundle(compact, require_bundle=True)

        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["entry_count"], 2)
        self.assertEqual(audit["reference_count"], 4)
        self.assertEqual(expanded, original)

    def test_packer_rejects_preexisting_snapshot_refs_without_bundle(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        compact.pop("evidence_bundle")

        with self.assertRaisesRegex(PortfolioEvidenceBundleError, "must_be_embedded_snapshot"):
            pack_portfolio_evidence_bundle(compact)

    def test_legacy_embedded_payload_is_allowed_only_when_bundle_not_required(self) -> None:
        payload = _payload()
        self.assertEqual(verify_portfolio_evidence_bundle(payload)["status"], "PASS")
        audit = verify_portfolio_evidence_bundle(payload, require_bundle=True)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("portfolio_evidence_bundle_missing", audit["blockers"])

    def test_missing_bundle_for_snapshot_refs_is_blocked(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        compact.pop("evidence_bundle")
        audit = verify_portfolio_evidence_bundle(compact)

        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("portfolio_evidence_bundle_missing_for_refs", audit["blockers"])

    def test_tampered_compressed_payload_is_blocked(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        bundle = compact["evidence_bundle"]
        content_hash = next(iter(bundle["entries"]))
        entry = bundle["entries"][content_hash]
        encoded = entry["payload"]
        entry["payload"] = encoded[:-1] + ("A" if encoded[-1] != "A" else "B")

        audit = verify_portfolio_evidence_bundle(compact, require_bundle=True)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(
            any("evidence_bundle" in blocker for blocker in audit["blockers"]),
            audit["blockers"],
        )

    def test_missing_referenced_entry_is_blocked_even_when_counts_are_resealed(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        bundle = compact["evidence_bundle"]
        content_hash = next(iter(bundle["entries"]))
        bundle["entries"].pop(content_hash)
        bundle["entry_count"] -= 1

        audit = verify_portfolio_evidence_bundle(compact, require_bundle=True)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(
            any("snapshot_ref_unresolved" in blocker for blocker in audit["blockers"]),
            audit["blockers"],
        )

    def test_unreferenced_entry_is_blocked(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        bundle = compact["evidence_bundle"]
        content_hash, entry = next(iter(bundle["entries"].items()))
        bundle["entries"]["f" * 64] = deepcopy(entry)
        bundle["entry_count"] += 1

        audit = verify_portfolio_evidence_bundle(compact, require_bundle=True)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertIn("portfolio_evidence_bundle_reference_inventory_mismatch", audit["blockers"])

    def test_declared_uncompressed_size_cannot_hide_larger_content(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        bundle = compact["evidence_bundle"]
        content_hash = next(iter(bundle["entries"]))
        entry = bundle["entries"][content_hash]
        entry["uncompressed_size"] = 1

        audit = verify_portfolio_evidence_bundle(compact, require_bundle=True)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(
            any("decompression_limit" in blocker for blocker in audit["blockers"]),
            audit["blockers"],
        )

    def test_referenced_snapshot_metadata_mismatch_is_blocked(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        ref = compact["first"]["cross_source"][0]["primary_snapshot"]
        ref["row_count"] += 1

        audit = verify_portfolio_evidence_bundle(compact, require_bundle=True)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(
            any("ref_row_count_mismatch" in blocker for blocker in audit["blockers"]),
            audit["blockers"],
        )

    def test_fully_resealed_bundle_cannot_change_cross_source_semantics(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        bundle = compact["evidence_bundle"]
        first_ref = compact["first"]["cross_source"][0]["primary_snapshot"]
        old_hash = first_ref["content_hash"]
        old_entry = bundle["entries"].pop(old_hash)
        snapshot = json.loads(
            zlib.decompress(base64.b64decode(old_entry["payload"])).decode("utf-8")
        )
        changed_rows = deepcopy(snapshot["rows"])
        changed_rows[10]["close"] *= 1.25
        changed_snapshot = build_market_data_snapshot(
            symbol=snapshot["symbol"],
            provider=snapshot["provider"],
            rows=changed_rows,
            interval=snapshot["interval"],
            session=snapshot["session"],
            role=snapshot["role"],
            adjustment_basis=snapshot["adjustment_basis"],
            corporate_actions_hash=snapshot["corporate_actions_hash"],
            completed_only=snapshot["completed_only"],
            through_date=snapshot["through_date"],
        )
        raw = _canonical_bytes(changed_snapshot)
        compressed = zlib.compress(raw, level=9)
        new_hash = hashlib.sha256(raw).hexdigest()
        new_entry = {
            **old_entry,
            "content_hash": new_hash,
            "snapshot_hash": changed_snapshot["snapshot_hash"],
            "rows_hash": changed_snapshot["rows_hash"],
            "row_count": changed_snapshot["row_count"],
            "uncompressed_size": len(raw),
            "compressed_size": len(compressed),
            "payload": base64.b64encode(compressed).decode("ascii"),
        }
        bundle["entries"][new_hash] = new_entry
        for section in ("first", "second"):
            ref = compact[section]["cross_source"][0]["primary_snapshot"]
            ref.update({
                "content_hash": new_hash,
                "snapshot_hash": changed_snapshot["snapshot_hash"],
                "rows_hash": changed_snapshot["rows_hash"],
                "row_count": changed_snapshot["row_count"],
            })
        bundle["entries"] = {
            key: bundle["entries"][key]
            for key in sorted(bundle["entries"])
        }
        bundle["total_uncompressed_bytes"] = sum(
            entry["uncompressed_size"] for entry in bundle["entries"].values()
        )
        bundle["total_compressed_bytes"] = sum(
            entry["compressed_size"] for entry in bundle["entries"].values()
        )
        bundle["entries_hash"] = _canonical_hash(bundle["entries"])
        bundle_without_hash = dict(bundle)
        bundle_without_hash.pop("bundle_hash")
        bundle["bundle_hash"] = _canonical_hash(bundle_without_hash)

        audit = verify_portfolio_evidence_bundle(compact, require_bundle=True)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(
            any("portfolio_evidence_cross_source" in blocker for blocker in audit["blockers"]),
            audit["blockers"],
        )

    def test_packer_refuses_semantically_invalid_snapshot(self) -> None:
        payload = _payload()
        payload["first"]["cross_source"][0]["primary_snapshot"]["rows"][0]["close"] *= 10

        with self.assertRaisesRegex(PortfolioEvidenceBundleError, "market_data_snapshot_invalid"):
            pack_portfolio_evidence_bundle(payload)

    def test_valid_base64_with_non_zlib_content_is_blocked(self) -> None:
        compact = pack_portfolio_evidence_bundle(_payload())
        bundle = compact["evidence_bundle"]
        content_hash = next(iter(bundle["entries"]))
        entry = bundle["entries"][content_hash]
        invalid = b"not-zlib"
        entry["payload"] = base64.b64encode(invalid).decode("ascii")
        entry["compressed_size"] = len(invalid)

        audit = verify_portfolio_evidence_bundle(compact, require_bundle=True)
        self.assertEqual(audit["status"], "BLOCK")
        self.assertTrue(
            any("zlib_invalid" in blocker for blocker in audit["blockers"]),
            audit["blockers"],
        )


if __name__ == "__main__":
    unittest.main()
