from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.forward_artifact_io import (
    ForwardArtifactRead,
    MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
    read_forward_json_artifact,
)
from exchange_terminal.services.portfolio_backtest_pack import (
    MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
    MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES,
)
import run_portfolio_forward_performance as performance_runner


BATCH_HASH = "b" * 64
CANDIDATE_HASH = "c" * 64


def research_bytes() -> bytes:
    return json.dumps(
        {
            "batch_run_hash": BATCH_HASH,
            "frozen_candidate": {"candidate_hash": CANDIDATE_HASH},
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def active_contract(
    raw: bytes,
    *,
    report_file: str = "portfolio_research_bound.json",
    expected_sha256: str | None = None,
) -> dict[str, object]:
    return {
        "registry": {
            "experiment_completion_receipt": {
                "report_file": report_file,
                "report_file_sha256": (
                    expected_sha256
                    if expected_sha256 is not None
                    else hashlib.sha256(raw).hexdigest()
                ),
                "batch_run_hash": BATCH_HASH,
            },
        },
        "candidate": {
            "candidate_hash": CANDIDATE_HASH,
            "research_report_hash": BATCH_HASH,
        },
    }


class PortfolioForwardPerformanceRunnerIoTests(unittest.TestCase):
    def test_default_status_reader_is_strict_bounded_and_compatible(self) -> None:
        raw = b'{"status":"PASS","count":1}'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "performance.json"
            path.write_bytes(raw)
            with patch.object(
                performance_runner,
                "read_forward_json_artifact",
                wraps=read_forward_json_artifact,
            ) as reader:
                payload = performance_runner._read_json(path)

        self.assertEqual(payload, {"status": "PASS", "count": 1})
        reader.assert_called_once_with(
            path,
            byte_limit=MAX_PORTFOLIO_FORWARD_STATUS_ARTIFACT_BYTES,
            size_limit_blocker=(
                "portfolio_forward_performance_artifact_size_limit_exceeded"
            ),
        )

    def test_status_reader_rejects_duplicate_nonfinite_deep_and_oversize_json(self) -> None:
        deeply_nested = (b'{"nested":' * 140) + b"0" + (b"}" * 140)
        cases = {
            "duplicate": b'{"status":"PASS","status":"BLOCK"}',
            "nonfinite": b'{"value":NaN}',
            "deep": deeply_nested,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, raw in cases.items():
                with self.subTest(name=name):
                    path = root / f"{name}.json"
                    path.write_bytes(raw)
                    with self.assertRaises(ValueError) as raised:
                        performance_runner._read_json(path)
                    self.assertIn("strict_json_", str(raised.exception))
                    self.assertNotIn(str(path), str(raised.exception))

            oversized = root / "oversized.json"
            oversized.write_bytes(b'{"value":1}')
            with self.assertRaisesRegex(
                ValueError,
                "runner_test_size_limit_exceeded",
            ):
                performance_runner._read_json(
                    oversized,
                    byte_limit=2,
                    size_limit_blocker="runner_test_size_limit_exceeded",
                )

    def test_status_reader_contains_link_memory_and_os_errors_without_paths(self) -> None:
        private = "C:\\private\\forward-performance.json"
        path = Path(private)
        failures = (
            MemoryError(private),
            OSError(private),
            RecursionError(private),
        )
        for failure in failures:
            with self.subTest(error=type(failure).__name__), patch.object(
                performance_runner,
                "read_forward_json_artifact",
                side_effect=failure,
            ):
                with self.assertRaises(ValueError) as raised:
                    performance_runner._read_json(path)
                self.assertEqual(
                    str(raised.exception),
                    "portfolio_forward_performance_artifact_unreadable",
                )
                self.assertNotIn(private, str(raised.exception))

        with patch.object(
            performance_runner,
            "read_forward_json_artifact",
            return_value=ForwardArtifactRead(
                status="BLOCK",
                payload={},
                raw=b"",
                blocker="artifact_bundle_member_link_or_reparse_forbidden",
            ),
        ):
            with self.assertRaises(ValueError) as raised:
                performance_runner._read_json(path)
        self.assertEqual(
            str(raised.exception),
            "artifact_bundle_member_link_or_reparse_forbidden",
        )
        self.assertNotIn(private, str(raised.exception))

    def test_active_report_preserves_exact_identity_hash_and_research_budget(self) -> None:
        raw = research_bytes()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            path = root / "portfolio_research_bound.json"
            path.write_bytes(raw)
            with patch.object(
                performance_runner,
                "read_forward_json_artifact",
                wraps=read_forward_json_artifact,
            ) as reader:
                loaded_path, payload, file_sha256 = (
                    performance_runner._active_research_report(
                        root,
                        active_contract(raw),
                    )
                )

        self.assertEqual(loaded_path, path)
        self.assertEqual(payload, json.loads(raw))
        self.assertEqual(file_sha256, hashlib.sha256(raw).hexdigest())
        reader.assert_called_once_with(
            path,
            byte_limit=MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES,
            size_limit_blocker="active_research_report_size_limit_exceeded",
        )

    def test_active_report_keeps_hash_mismatch_priority_over_invalid_json(self) -> None:
        raw = b'{"batch_run_hash":"first","batch_run_hash":"second"}'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "portfolio_research_bound.json").write_bytes(raw)

            with self.assertRaisesRegex(
                ValueError,
                "file hash does not match its completion receipt",
            ):
                performance_runner._active_research_report(
                    root,
                    active_contract(raw, expected_sha256="0" * 64),
                )

    def test_active_report_rejects_strict_json_and_oversize_after_exact_hash(self) -> None:
        deeply_nested = (b'{"nested":' * 140) + b"0" + (b"}" * 140)
        cases = {
            "duplicate": b'{"value":1,"value":2}',
            "nonfinite": b'{"value":Infinity}',
            "deep": deeply_nested,
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            path = root / "portfolio_research_bound.json"
            for name, raw in cases.items():
                with self.subTest(name=name):
                    path.write_bytes(raw)
                    with self.assertRaisesRegex(
                        ValueError,
                        "Active research report JSON is invalid",
                    ) as raised:
                        performance_runner._active_research_report(
                            root,
                            active_contract(raw),
                        )
                    self.assertNotIn(str(path), str(raised.exception))

            raw = research_bytes()
            path.write_bytes(raw)
            with patch.object(
                performance_runner,
                "MAX_PORTFOLIO_RESEARCH_SOURCE_DOCUMENT_BYTES",
                8,
            ), self.assertRaisesRegex(
                ValueError,
                "active_research_report_size_limit_exceeded",
            ):
                performance_runner._active_research_report(
                    root,
                    active_contract(raw),
                )

    def test_active_report_rejects_windows_alias_link_and_redacts_exceptions(self) -> None:
        raw = research_bytes()
        unsafe_names = (
            "CON.json",
            "report.json:stream",
            "report.json.",
            "report.json ",
            "nested\\report.json",
            "ｒｅｐｏｒｔ.json",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for unsafe in unsafe_names:
                with self.subTest(filename=unsafe), patch.object(
                    performance_runner,
                    "read_forward_json_artifact",
                ) as reader:
                    with self.assertRaisesRegex(ValueError, "filename is invalid"):
                        performance_runner._active_research_report(
                            root,
                            active_contract(raw, report_file=unsafe),
                        )
                    reader.assert_not_called()

            private = "C:\\private\\portfolio-research.json"
            with patch.object(
                performance_runner,
                "read_forward_json_artifact",
                side_effect=MemoryError(private),
            ):
                with self.assertRaises(ValueError) as raised:
                    performance_runner._active_research_report(
                        root,
                        active_contract(raw),
                    )
            self.assertEqual(
                str(raised.exception),
                "Active research report is unavailable.",
            )
            self.assertNotIn(private, str(raised.exception))

            with patch.object(
                performance_runner,
                "read_forward_json_artifact",
                return_value=ForwardArtifactRead(
                    status="BLOCK",
                    payload={},
                    raw=b"",
                    blocker="artifact_bundle_member_link_or_reparse_forbidden",
                ),
            ):
                with self.assertRaises(ValueError) as linked:
                    performance_runner._active_research_report(
                        root,
                        active_contract(raw),
                    )
            self.assertIn("link_or_reparse_forbidden", str(linked.exception))
            self.assertNotIn(str(root), str(linked.exception))

    def test_historical_audit_uses_strict_statistical_budget_and_keeps_selection(self) -> None:
        research = json.loads(research_bytes())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            older = root / "portfolio_statistical_audit_older.json"
            newer = root / "portfolio_statistical_audit_newer.json"
            invalid = root / "portfolio_statistical_audit_invalid.json"
            older.write_text(json.dumps({
                "active_candidate_hash": CANDIDATE_HASH,
                "generated_at": 100,
                "status": "BLOCK",
                "audit_hash": "older",
            }), encoding="utf-8")
            newer.write_text(json.dumps({
                "active_candidate_hash": CANDIDATE_HASH,
                "generated_at": 200,
                "status": "PASS",
                "audit_hash": "newer",
            }), encoding="utf-8")
            invalid.write_bytes(b'{"status":"PASS","status":"BLOCK"}')
            with patch.object(
                performance_runner,
                "verify_statistical_audit_artifact",
                return_value={
                    "status": "PASS",
                    "semantic_verification": {
                        "recomputed_from_frozen_research": True,
                    },
                },
            ), patch.object(
                performance_runner,
                "read_forward_json_artifact",
                wraps=read_forward_json_artifact,
            ) as reader:
                selected = performance_runner._historical_statistical_audit(
                    root,
                    CANDIDATE_HASH,
                    research_report=research,
                    research_file_sha256="f" * 64,
                )

        self.assertEqual(selected["artifact_file"], newer.name)
        self.assertEqual(selected["audit_hash"], "newer")
        self.assertEqual(selected["verification_status"], "PASS")
        self.assertTrue(selected["semantic_recomputed"])
        self.assertEqual(reader.call_count, 3)
        self.assertTrue(all(
            call.kwargs["byte_limit"] == MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES
            and call.kwargs["size_limit_blocker"]
            == "portfolio_statistical_audit_size_limit_exceeded"
            for call in reader.call_args_list
        ))

    def test_historical_audit_skips_oversize_link_alias_and_redacted_failures(self) -> None:
        research = json.loads(research_bytes())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            oversized = root / "portfolio_statistical_audit_oversized.json"
            oversized.write_bytes(b'{"value":1}')
            with patch.object(
                performance_runner,
                "MAX_PORTFOLIO_STATISTICAL_AUDIT_BYTES",
                2,
            ):
                missing = performance_runner._historical_statistical_audit(
                    root,
                    CANDIDATE_HASH,
                    research_report=research,
                    research_file_sha256="f" * 64,
                )
            self.assertEqual(missing["status"], "MISSING")

            unsafe = root / "portfolio_statistical_audit_bad:stream.json"
            with patch.object(
                Path,
                "glob",
                return_value=[unsafe],
            ), patch.object(
                performance_runner,
                "read_forward_json_artifact",
            ) as reader:
                aliased = performance_runner._historical_statistical_audit(
                    root,
                    CANDIDATE_HASH,
                    research_report=research,
                    research_file_sha256="f" * 64,
                )
            self.assertEqual(aliased["status"], "MISSING")
            reader.assert_not_called()

            private = "C:\\private\\statistical-audit.json"
            with patch.object(
                Path,
                "glob",
                return_value=[root / "portfolio_statistical_audit_private.json"],
            ), patch.object(
                performance_runner,
                "read_forward_json_artifact",
                side_effect=OSError(private),
            ):
                redacted = performance_runner._historical_statistical_audit(
                    root,
                    CANDIDATE_HASH,
                    research_report=research,
                    research_file_sha256="f" * 64,
                )
            self.assertEqual(redacted["status"], "MISSING")
            self.assertNotIn(private, json.dumps(redacted))


if __name__ == "__main__":
    unittest.main()
