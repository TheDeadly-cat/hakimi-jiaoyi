from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from portfolio_reference_data import (
    CORPORATE_ACTION_SOURCE_SCHEMA_VERSION,
    MEMBERSHIP_SOURCE_SCHEMA_VERSION,
    REFERENCE_DATA_IMPORT_SCHEMA_VERSION,
    ReferenceDataStore,
    build_reference_data_pack_from_manifest,
    canonical_hash,
    verify_reference_data_pack,
)


def write_json(path: Path, payload: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_fixture(root: Path) -> Path:
    membership_path = root / "sources" / "membership.json"
    membership_hash = write_json(membership_path, {
        "schema_version": MEMBERSHIP_SOURCE_SCHEMA_VERSION,
        "records": [
            {"symbol": "AAA", "effective_from": "2024-01-02", "effective_to": "2024-06-30"},
            {"symbol": "BBB", "effective_from": "2024-04-01", "effective_to": ""},
        ],
    })
    corporate_path = root / "sources" / "corporate-actions.json"
    corporate_hash = write_json(corporate_path, {
        "schema_version": CORPORATE_ACTION_SOURCE_SCHEMA_VERSION,
        "coverage_start": "2024-01-02",
        "coverage_end": "2024-12-31",
        "covered_symbols": ["SPY", "AAA", "BBB"],
        "coverage_types": ["SPLIT", "DIVIDEND", "SUSPENSION", "DELISTING"],
        "records": [
            {
                "symbol": "AAA",
                "action_type": "SPLIT",
                "event_date": "2024-05-01",
                "ratio": 2,
                "provider_event_id": "split-1",
            },
            {
                "symbol": "BBB",
                "action_type": "DIVIDEND",
                "event_date": "2024-06-03",
                "cash_amount": 0.5,
                "currency": "USD",
                "pay_date": "2024-06-14",
                "provider_event_id": "dividend-1",
            },
            {
                "symbol": "AAA",
                "action_type": "SUSPENSION",
                "start_date": "2024-05-15",
                "end_date": "2024-05-16",
                "provider_event_id": "suspension-1",
            },
        ],
    })
    manifest_path = root / "manifest.json"
    write_json(manifest_path, {
        "schema_version": REFERENCE_DATA_IMPORT_SCHEMA_VERSION,
        "package_id": "fixture-reference-pack",
        "prepared_at": "2025-01-05T00:00:00Z",
        "universe": {
            "benchmark_symbol": "SPY",
            "tradable_symbols": ["AAA", "BBB"],
            "selection_basis": "OFFICIAL_TEST_INDEX_MEMBERSHIP",
            "selection_rule_id": "official-test-index-v1",
            "coverage_start": "2024-01-02",
            "coverage_end": "2024-12-31",
            "sources": [{
                "source_authority": "OFFICIAL_INDEX_PROVIDER",
                "source_name": "Official Test Index",
                "evidence_ref": "https://example.test/index/history",
                "document_path": "sources/membership.json",
                "document_sha256": membership_hash,
                "evidence_published_at": "2023-12-01T00:00:00Z",
                "retrieved_at": "2025-01-02T00:00:00Z",
            }],
        },
        "corporate_action_sources": [{
            "provider_id": "official_test_exchange",
            "source_authority": "OFFICIAL_EXCHANGE_FEED",
            "source_name": "Official Test Exchange Corporate Action Master",
            "evidence_ref": "https://example.test/corporate-actions/history",
            "document_path": "sources/corporate-actions.json",
            "document_sha256": corporate_hash,
            "observed_at": "2025-01-02T00:00:00Z",
        }],
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    })
    return manifest_path


class PortfolioReferenceDataTests(unittest.TestCase):
    def test_valid_package_builds_verified_point_in_time_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest = build_fixture(Path(temporary))

            pack = build_reference_data_pack_from_manifest(manifest)
            audit = verify_reference_data_pack(pack, source_root=Path(temporary))

            self.assertEqual(pack["status"], "PASS")
            self.assertEqual(audit["status"], "PASS")
            self.assertTrue(pack["universe_contract"]["historical_membership_verified"])
            self.assertEqual(pack["coverage_summary"]["fully_covered_symbol_count"], 3)
            self.assertEqual(len(pack["corporate_actions_by_symbol"]["AAA"]), 1)
            self.assertEqual(len(pack["corporate_actions_by_symbol"]["BBB"]), 1)
            self.assertEqual(len(pack["security_lifecycle_by_symbol"]["AAA"]), 1)
            self.assertTrue(pack["manual_source_identity_review_required"])
            self.assertFalse(pack["paper_authorized"])
            self.assertFalse(pack["live_order_allowed"])

    def test_store_is_idempotent_and_does_not_copy_source_documents(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = build_reference_data_pack_from_manifest(build_fixture(root))
            store = ReferenceDataStore(root / "reference.sqlite", now_ms=lambda: 1234)

            first = store.import_pack(pack, source_root=root)
            second = store.import_pack(pack, source_root=root)
            summary = store.summary()

            self.assertTrue(first["ok"])
            self.assertTrue(second["ok"])
            self.assertEqual(summary["pack_count"], 1)
            self.assertEqual(summary["source_document_count"], 2)
            self.assertEqual(summary["corporate_action_count"], 2)
            self.assertEqual(summary["security_lifecycle_count"], 1)
            self.assertFalse(summary["paper_authorized"])

    def test_document_hash_mismatch_blocks_import(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path = build_fixture(Path(temporary))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["universe"]["sources"][0]["document_sha256"] = "0" * 64
            write_json(manifest_path, manifest)

            pack = build_reference_data_pack_from_manifest(manifest_path)

            self.assertEqual(pack["status"], "BLOCK")
            self.assertTrue(any("document_hash_mismatch" in item for item in pack["blockers"]))

    def test_source_document_path_cannot_escape_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = root / "package"
            manifest_path = build_fixture(package)
            outside = root / "outside.json"
            outside_hash = write_json(outside, {"schema_version": MEMBERSHIP_SOURCE_SCHEMA_VERSION, "records": []})
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["universe"]["sources"][0]["document_path"] = "../../outside.json"
            manifest["universe"]["sources"][0]["document_sha256"] = outside_hash
            write_json(manifest_path, manifest)

            pack = build_reference_data_pack_from_manifest(manifest_path)

            self.assertEqual(pack["status"], "BLOCK")
            self.assertTrue(any("document_path_escape" in item for item in pack["blockers"]))

    def test_non_authoritative_membership_source_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            manifest_path = build_fixture(Path(temporary))
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["universe"]["sources"][0]["source_authority"] = "USER_EDITED_CSV"
            write_json(manifest_path, manifest)

            pack = build_reference_data_pack_from_manifest(manifest_path)

            self.assertEqual(pack["status"], "BLOCK")
            self.assertTrue(any("membership_source_not_authoritative" in item for item in pack["blockers"]))

    def test_future_observation_and_incomplete_symbol_coverage_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = build_fixture(root)
            corporate_path = root / "sources" / "corporate-actions.json"
            corporate = json.loads(corporate_path.read_text(encoding="utf-8"))
            corporate["covered_symbols"] = ["AAA"]
            corporate_hash = write_json(corporate_path, corporate)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            source = manifest["corporate_action_sources"][0]
            source["document_sha256"] = corporate_hash
            source["observed_at"] = "2025-02-01T00:00:00Z"
            write_json(manifest_path, manifest)

            pack = build_reference_data_pack_from_manifest(manifest_path)

            self.assertEqual(pack["status"], "BLOCK")
            self.assertTrue(any("observed_after_package_prepared" in item for item in pack["blockers"]))
            self.assertEqual(pack["coverage_summary"]["missing_symbols"], ["AAA", "BBB", "SPY"])

    def test_resealed_pack_tampering_is_detected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pack = build_reference_data_pack_from_manifest(build_fixture(Path(temporary)))
            pack["coverage_summary"]["fully_covered_symbol_count"] = 99
            pack.pop("pack_hash")
            pack["pack_hash"] = hashlib.sha256(
                json.dumps(pack, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
            ).hexdigest()

            audit = verify_reference_data_pack(pack, source_root=Path(temporary))

            self.assertEqual(audit["status"], "BLOCK")
            self.assertIn("reference_data_coverage_summary_mismatch", audit["blockers"])

    def test_resealed_action_substitution_is_rebuilt_from_original_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pack = build_reference_data_pack_from_manifest(build_fixture(root))
            source = pack["corporate_action_sources"][0]
            source["actions_by_symbol"]["AAA"][0]["ratio"] = 3.0
            source.pop("source_hash")
            source["source_hash"] = canonical_hash(source)
            pack["corporate_actions_by_symbol"]["AAA"][0]["ratio"] = 3.0
            pack.pop("pack_hash")
            pack["pack_hash"] = canonical_hash(pack)

            audit = verify_reference_data_pack(pack, source_root=root)

            self.assertEqual(audit["status"], "BLOCK")
            self.assertIn("reference_data_corporate_source_content_mismatch:0", audit["blockers"])

    def test_pack_cannot_be_verified_without_original_source_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pack = build_reference_data_pack_from_manifest(build_fixture(Path(temporary)))

            audit = verify_reference_data_pack(pack)

            self.assertEqual(audit["status"], "BLOCK")
            self.assertIn("reference_data_source_root_unavailable", audit["blockers"])

    def test_store_rejects_blocked_pack(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = build_fixture(root)
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            payload["corporate_action_sources"] = []
            write_json(manifest, payload)
            pack = build_reference_data_pack_from_manifest(manifest)

            result = ReferenceDataStore(root / "reference.sqlite").import_pack(pack, source_root=root)

            self.assertFalse(result["ok"])
            self.assertEqual(ReferenceDataStore(root / "reference.sqlite").summary()["pack_count"], 0)


if __name__ == "__main__":
    unittest.main()
