from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.trusted_clock import (
    build_trusted_clock_attestation,
    verify_trusted_clock_attestation,
)


def canonical_hash(payload: object) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def source(name: str, *, local_midpoint: int = 1_000_000, offset: int = 0, round_trip: int = 20) -> dict[str, object]:
    payload = {
        "source": name,
        "endpoint": f"https://{name.lower()}.test/time",
        "status": "PASS",
        "error": "",
        "requested_at_ms": local_midpoint - round_trip // 2,
        "received_at_ms": local_midpoint + round_trip // 2,
        "round_trip_ms": round_trip,
        "midpoint_local_ms": local_midpoint,
        "server_time_ms": local_midpoint + offset,
        "offset_ms": offset,
    }
    payload["evidence_hash"] = canonical_hash(payload)
    return payload


class TrustedClockTests(unittest.TestCase):
    def test_two_consistent_sources_form_a_quorum(self) -> None:
        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[source("ONE", offset=100), source("TWO", offset=200)],
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["quality"], "EXTERNAL_QUORUM")
        self.assertEqual(result["attested_now_ms"], 1_000_150)
        self.assertEqual(verify_trusted_clock_attestation(result)["status"], "PASS")

    def test_one_source_is_accepted_but_explicitly_degraded(self) -> None:
        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[source("ONE")],
        )

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["quality"], "EXTERNAL_SINGLE_SOURCE")
        self.assertIn("single_external_clock_source", result["warnings"])

    def test_large_local_clock_skew_blocks_attestation(self) -> None:
        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[source("ONE", offset=31_000)],
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any(item.startswith("local_clock_skew_exceeds_limit") for item in result["blockers"]))

    def test_disagreeing_external_sources_block_attestation(self) -> None:
        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[source("ONE", offset=-3_000), source("TWO", offset=3_000)],
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertTrue(any(item.startswith("external_clock_sources_disagree") for item in result["blockers"]))

    def test_tampering_is_detected(self) -> None:
        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[source("ONE")],
        )
        result["attested_now_ms"] = 2_000_000

        verification = verify_trusted_clock_attestation(result)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("clock_attestation_hash_mismatch", verification["blockers"])

    def test_resealed_semantic_forgery_is_detected(self) -> None:
        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[source("ONE", offset=100)],
        )
        clock_source = result["sources"][0]
        clock_source["status"] = "ERROR"
        clock_source["error"] = "TimeoutError"
        clock_source["server_time_ms"] = 0
        clock_source["offset_ms"] = 0
        clock_source.pop("evidence_hash")
        clock_source["evidence_hash"] = canonical_hash(clock_source)
        result["attested_now_ms"] = 1_999_999
        result.pop("attestation_hash")
        result["attestation_hash"] = canonical_hash(result)

        verification = verify_trusted_clock_attestation(result)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("clock_attestation_semantic_mismatch:status", verification["blockers"])
        self.assertIn("clock_attestation_semantic_mismatch:attested_now_ms", verification["blockers"])
        self.assertIn("clock_attestation_semantic_mismatch:external_source_count", verification["blockers"])

    def test_source_time_arithmetic_must_be_internally_consistent(self) -> None:
        inconsistent = source("ONE", offset=100)
        inconsistent["offset_ms"] = 99
        inconsistent.pop("evidence_hash")
        inconsistent["evidence_hash"] = canonical_hash(inconsistent)

        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[inconsistent],
        )

        self.assertEqual(result["status"], "BLOCK")
        self.assertIn("clock_source_invalid:ONE:offset_mismatch", result["blockers"])
        self.assertEqual(verify_trusted_clock_attestation(result)["status"], "BLOCK")

    def test_legacy_schema_is_rechecked_with_v2_semantics(self) -> None:
        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[source("ONE", offset=100)],
        )
        result["schema_version"] = "trusted-clock-attestation-v1"
        result.pop("attestation_hash")
        result["attestation_hash"] = canonical_hash(result)

        verification = verify_trusted_clock_attestation(result)

        self.assertEqual(verification["status"], "PASS")
        self.assertIn("legacy_clock_schema_verified_with_v2_semantics", verification["warnings"])

        result["external_source_count"] = 0
        result.pop("attestation_hash")
        result["attestation_hash"] = canonical_hash(result)
        self.assertEqual(verify_trusted_clock_attestation(result)["status"], "BLOCK")

    def test_execution_authority_fields_must_be_explicit_json_false(self) -> None:
        result = build_trusted_clock_attestation(
            local_now_ms=1_000_000,
            provider_evidence=[source("ONE")],
        )
        result["paper_authorized"] = 0
        result.pop("attestation_hash")
        result["attestation_hash"] = canonical_hash(result)

        verification = verify_trusted_clock_attestation(result)

        self.assertEqual(verification["status"], "BLOCK")
        self.assertIn("clock_attestation_execution_authority_invalid", verification["blockers"])


if __name__ == "__main__":
    unittest.main()
