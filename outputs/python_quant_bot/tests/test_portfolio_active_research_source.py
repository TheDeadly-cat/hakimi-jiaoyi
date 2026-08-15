from __future__ import annotations

from contextlib import redirect_stdout
import copy
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.portfolio_active_research_source import (
    load_active_portfolio_research_source,
)
from exchange_terminal.services.forward_artifact_io import read_forward_json_artifact
from exchange_terminal.services.portfolio_forward import activate_portfolio_candidate
import run_internal_execution_rehearsal
import run_internal_portfolio_statistical_audit
from tests.portfolio_governance_fixtures import experiment_completion_receipt
from tests.test_portfolio_forward import attested_clock, candidate, robustness


BATCH_HASH = "b" * 64
CANDIDATE_HASH = "c" * 64


def _report_bytes(
    *,
    batch_hash: str = BATCH_HASH,
    candidate_hash: str = CANDIDATE_HASH,
) -> bytes:
    return json.dumps(
        {
            "batch_run_hash": batch_hash,
            "frozen_candidate": {"candidate_hash": candidate_hash},
            "spec": {"evidence_bundle_required": False},
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        },
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _active_result(
    raw: bytes,
    *,
    report_file: str = "portfolio_research_bound.json",
) -> dict[str, object]:
    receipt = {
        "report_file": report_file,
        "report_file_sha256": hashlib.sha256(raw).hexdigest(),
        "batch_run_hash": BATCH_HASH,
        "candidate_hash": CANDIDATE_HASH,
    }
    return {
        "ok": True,
        "status": "PASS",
        "blockers": [],
        "experiment_completion_verification": {"status": "PASS", "blockers": []},
        "experiment_artifact_verification": {"status": "PASS", "blockers": []},
        "registry": {
            "candidate_hash": CANDIDATE_HASH,
            "experiment_completion_receipt": receipt,
        },
        "candidate": {
            "candidate_hash": CANDIDATE_HASH,
            "research_report_hash": BATCH_HASH,
        },
    }


class PortfolioActiveResearchSourceTests(unittest.TestCase):
    def test_real_active_candidate_loader_resolves_completion_receipt_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source_file = root / "engine.py"
            source_file.write_text("VALUE = 1\n", encoding="utf-8")
            frozen = candidate(source_file)
            candidate_path = root / "portfolio_candidate.json"
            candidate_path.write_text(json.dumps(frozen), encoding="utf-8")
            research_path = root / "portfolio_research_bound.json"
            research_path.write_bytes(_report_bytes(
                batch_hash=str(frozen["research_report_hash"]),
                candidate_hash=str(frozen["candidate_hash"]),
            ))
            robustness_path = root / "portfolio_robustness.json"
            robustness_path.write_text(
                json.dumps(robustness(str(frozen["candidate_hash"]))),
                encoding="utf-8",
            )
            activated = activate_portfolio_candidate(
                candidate_path=candidate_path,
                registry_path=root / "active_portfolio_candidate.json",
                robustness_path=robustness_path,
                activated_at=1_020_000,
                activation_clock_attestation=attested_clock(1_020_000),
                experiment_completion_receipt=experiment_completion_receipt(
                    frozen,
                    report_path=research_path,
                    candidate_path=candidate_path,
                ),
            )

            result = load_active_portfolio_research_source(root)

        self.assertEqual(activated["status"], "ACTIVATED")
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["report_file"], research_path.name)
        self.assertEqual(result["candidate"]["candidate_hash"], frozen["candidate_hash"])
        self.assertEqual(
            result["report"]["frozen_candidate"]["candidate_hash"],
            frozen["candidate_hash"],
        )

    def test_exact_receipt_report_is_read_once_without_globbing_same_batch_files(self) -> None:
        raw = _report_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bound = root / "portfolio_research_bound.json"
            bound.write_bytes(raw)
            (root / "portfolio_research_duplicate.json").write_text(
                "not the receipt-bound report",
                encoding="utf-8",
            )
            with patch(
                "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                return_value=_active_result(raw),
            ) as load_active, patch(
                "exchange_terminal.services.portfolio_active_research_source.read_forward_json_artifact",
                wraps=read_forward_json_artifact,
            ) as read_artifact:
                result = load_active_portfolio_research_source(root)

        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["report_file"], bound.name)
        self.assertEqual(result["report_file_sha256"], hashlib.sha256(raw).hexdigest())
        self.assertEqual(result["report"]["batch_run_hash"], BATCH_HASH)
        load_active.assert_called_once_with(root.resolve(), registry_path=None)
        read_artifact.assert_called_once()
        self.assertEqual(read_artifact.call_args.args[0], bound.resolve())

    def test_missing_bound_report_does_not_fall_back_to_matching_batch_file(self) -> None:
        raw = _report_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "portfolio_research_duplicate.json").write_bytes(raw)
            with patch(
                "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                return_value=_active_result(raw),
            ):
                result = load_active_portfolio_research_source(root)

        self.assertEqual(result, {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["research_report_unavailable"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        })

    def test_receipt_report_file_must_be_a_contained_basename(self) -> None:
        raw = _report_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outside = root.parent / "outside-research-source.json"
            with patch(
                "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                return_value=_active_result(raw, report_file=str(outside)),
            ), patch(
                "exchange_terminal.services.portfolio_active_research_source.read_forward_json_artifact",
            ) as read_artifact:
                result = load_active_portfolio_research_source(root)

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(result["blockers"], ["research_report_filename_invalid"])
        self.assertNotIn("report_path", result)
        read_artifact.assert_not_called()

    def test_file_hash_utf8_json_and_object_contracts_fail_closed(self) -> None:
        cases = (
            (b"tampered", _active_result(_report_bytes()), "research_report_file_sha256_mismatch"),
            (b"\xff\xfe", _active_result(b"\xff\xfe"), "research_report_utf8_invalid"),
            (b"{", _active_result(b"{"), "research_report_json_invalid"),
            (b"[]", _active_result(b"[]"), "research_report_payload_invalid"),
        )
        for raw, active, expected_blocker in cases:
            with self.subTest(blocker=expected_blocker), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "portfolio_research_bound.json").write_bytes(raw)
                with patch(
                    "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                    return_value=active,
                ):
                    result = load_active_portfolio_research_source(root)
            self.assertEqual(result["status"], "BLOCK")
            self.assertEqual(result["blockers"], [expected_blocker])
            self.assertNotIn("report_path", result)

    def test_duplicate_nonfinite_and_deep_reports_fail_strict_json(self) -> None:
        deeply_nested = (b'{"nested":' * 140) + b"0" + (b"}" * 140)
        cases = {
            "duplicate": b'{"value":1,"value":2}',
            "nonfinite": b'{"value":NaN}',
            "deep": deeply_nested,
        }
        for name, raw in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "portfolio_research_bound.json").write_bytes(raw)
                with patch(
                    "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                    return_value=_active_result(raw),
                ):
                    result = load_active_portfolio_research_source(root)

            self.assertEqual(result["status"], "BLOCK")
            self.assertEqual(result["blockers"], ["research_report_json_invalid"])

    def test_report_size_link_and_windows_basename_contracts_fail_closed(self) -> None:
        raw = _report_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "portfolio_research_bound.json"
            report.write_bytes(raw)
            with patch(
                "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                return_value=_active_result(raw),
            ), patch(
                "exchange_terminal.services.portfolio_active_research_source._research_report_byte_limit",
                return_value=8,
            ):
                oversized = load_active_portfolio_research_source(root)

            self.assertEqual(
                oversized["blockers"],
                ["research_report_size_limit_exceeded"],
            )

            target = root / "target.json"
            target.write_bytes(raw)
            link = root / "linked.json"
            try:
                link.symlink_to(target)
            except OSError:
                link = None
            if link is not None:
                with patch(
                    "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                    return_value=_active_result(raw, report_file=link.name),
                ):
                    linked = load_active_portfolio_research_source(root)
                self.assertEqual(
                    linked["blockers"],
                    ["research_report_link_or_reparse_forbidden"],
                )

            for unsafe in (
                "CON.json",
                "report.json:stream",
                "report.json.",
                "report.json ",
                "nested\\report.json",
                "ｒｅｐｏｒｔ.json",
            ):
                with self.subTest(filename=unsafe), patch(
                    "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                    return_value=_active_result(raw, report_file=unsafe),
                ), patch(
                    "exchange_terminal.services.portfolio_active_research_source.read_forward_json_artifact",
                ) as read_artifact:
                    rejected = load_active_portfolio_research_source(root)
                self.assertEqual(
                    rejected["blockers"],
                    ["research_report_filename_invalid"],
                )
                read_artifact.assert_not_called()

    def test_memory_failure_is_redacted_and_nested_authority_is_blocked(self) -> None:
        raw = _report_bytes()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            report = root / "portfolio_research_bound.json"
            report.write_bytes(raw)
            private = "C:\\private\\research-report.json"
            with patch(
                "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                return_value=_active_result(raw),
            ), patch(
                "exchange_terminal.services.forward_artifact_io.read_bounded_artifact",
                side_effect=MemoryError(private),
            ):
                exhausted = load_active_portfolio_research_source(root)

            self.assertEqual(
                exhausted["blockers"],
                ["research_report_memory_exhausted"],
            )
            self.assertNotIn(private, json.dumps(exhausted))

            authority_report = json.loads(raw.decode("utf-8"))
            authority_report["nested"] = {"Can-Trade": True}
            authority_raw = json.dumps(authority_report).encode("utf-8")
            report.write_bytes(authority_raw)
            with patch(
                "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                return_value=_active_result(authority_raw),
            ):
                authority = load_active_portfolio_research_source(root)

            self.assertEqual(
                authority["blockers"],
                ["research_report_contains_execution_authority"],
            )

    def test_receipt_candidate_report_batch_and_frozen_identities_are_exact(self) -> None:
        mutations = (
            ("receipt_batch", lambda active: active["registry"]["experiment_completion_receipt"].update(
                {"batch_run_hash": "x" * 64}
            )),
            ("candidate_batch", lambda active: active["candidate"].update(
                {"research_report_hash": "x" * 64}
            )),
            ("registry_candidate", lambda active: active["registry"].update(
                {"candidate_hash": "x" * 64}
            )),
            ("candidate_candidate", lambda active: active["candidate"].update(
                {"candidate_hash": "x" * 64}
            )),
            ("receipt_candidate", lambda active: active["registry"]["experiment_completion_receipt"].update(
                {"candidate_hash": "x" * 64}
            )),
        )
        raw = _report_bytes()
        for label, mutate in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "portfolio_research_bound.json").write_bytes(raw)
                active = copy.deepcopy(_active_result(raw))
                mutate(active)
                with patch(
                    "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                    return_value=active,
                ):
                    result = load_active_portfolio_research_source(root)
            self.assertEqual(result["status"], "BLOCK")
            self.assertNotIn("report_path", result)

        report_mutations = (
            ("report_batch", _report_bytes(batch_hash="x" * 64)),
            ("report_frozen_candidate", _report_bytes(candidate_hash="x" * 64)),
        )
        for label, changed_raw in report_mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / "portfolio_research_bound.json").write_bytes(changed_raw)
                active = _active_result(changed_raw)
                with patch(
                    "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
                    return_value=active,
                ):
                    result = load_active_portfolio_research_source(root)
            self.assertEqual(result["status"], "BLOCK")
            self.assertNotIn("report_path", result)

    def test_upstream_candidate_block_is_flat_and_does_not_republish_paths(self) -> None:
        leaked = "C:\\private\\active_portfolio_candidate.json"
        with tempfile.TemporaryDirectory() as directory, patch(
            "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
            return_value={
                "status": "BLOCK",
                "blockers": [f"unavailable:{leaked}"],
                "registry_path": leaked,
                "candidate": {"secret": leaked},
            },
        ):
            result = load_active_portfolio_research_source(Path(directory))

        self.assertEqual(result, {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["active_candidate_verification_failed"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        })
        self.assertNotIn(leaked, json.dumps(result))

    def test_upstream_candidate_exception_is_flat_and_non_sensitive(self) -> None:
        with tempfile.TemporaryDirectory() as directory, patch(
            "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
            side_effect=OSError("C:\\private\\candidate.json"),
        ):
            result = load_active_portfolio_research_source(Path(directory))

        self.assertEqual(result, {
            "ok": False,
            "status": "BLOCK",
            "blockers": ["active_candidate_verification_failed"],
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        })

    def test_unproven_completion_verification_blocks_before_report_read(self) -> None:
        raw = _report_bytes()
        active = _active_result(raw)
        active["experiment_artifact_verification"] = {
            "status": "BLOCK",
            "blockers": ["report_artifact_hash_mismatch"],
        }
        with tempfile.TemporaryDirectory() as directory, patch(
            "exchange_terminal.services.portfolio_active_research_source.load_active_portfolio_candidate",
            return_value=active,
        ), patch(
            "exchange_terminal.services.portfolio_active_research_source.read_forward_json_artifact",
        ) as read_artifact:
            result = load_active_portfolio_research_source(Path(directory))

        self.assertEqual(result["status"], "BLOCK")
        self.assertEqual(
            result["blockers"],
            ["active_candidate_completion_verification_failed"],
        )
        read_artifact.assert_not_called()

    def test_default_runner_block_never_expands_or_runs_research(self) -> None:
        blocked = {
            "status": "BLOCK",
            "blockers": ["active_candidate_verification_failed"],
        }
        modules = (
            (run_internal_execution_rehearsal, "run_research_report_execution_rehearsal"),
            (run_internal_portfolio_statistical_audit, "audit_portfolio_research_statistics"),
        )
        for module, computation_name in modules:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory, patch.object(
                module,
                "load_active_portfolio_research_source",
                return_value=blocked,
            ), patch.object(module, "expand_portfolio_evidence_bundle") as expand, patch.object(
                module,
                computation_name,
            ) as computation, patch.object(
                sys,
                "argv",
                [module.__name__, "--report-dir", directory],
            ):
                stream = StringIO()
                with redirect_stdout(stream):
                    code = module.main()
            payload = json.loads(stream.getvalue())
            self.assertEqual(code, 2)
            self.assertEqual(payload["status"], "BLOCK")
            self.assertEqual(payload["blockers"], ["active_candidate_verification_failed"])
            self.assertNotIn(str(Path(directory).resolve()), stream.getvalue())
            expand.assert_not_called()
            computation.assert_not_called()

    def test_default_runner_reuses_loader_sha_without_reopening_report(self) -> None:
        raw = _report_bytes()
        modules = (
            (
                run_internal_execution_rehearsal,
                "run_research_report_execution_rehearsal",
                {"status": "BLOCK", "stage_summary": {}},
            ),
            (
                run_internal_portfolio_statistical_audit,
                "audit_portfolio_research_statistics",
                {"status": "BLOCK", "conclusion": "historical_only", "stages": {}, "audit_hash": "audit"},
            ),
        )
        for module, computation_name, computation_result in modules:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source_path = root / "portfolio_research_bound.json"
                output = root / "result.json"
                active_source = {
                    "status": "PASS",
                    "report_path": str(source_path),
                    "report_file_sha256": hashlib.sha256(raw).hexdigest(),
                    "report": json.loads(raw.decode("utf-8")),
                    "registry": {"candidate_hash": CANDIDATE_HASH},
                }
                with patch.object(
                    module,
                    "load_active_portfolio_research_source",
                    return_value=active_source,
                ), patch.object(
                    module,
                    "expand_portfolio_evidence_bundle",
                    return_value=(active_source["report"], {"status": "PASS", "blockers": []}),
                ), patch.object(
                    module,
                    computation_name,
                    return_value=copy.deepcopy(computation_result),
                ), patch.object(module, "_file_sha256") as file_sha256, patch.object(
                    sys,
                    "argv",
                    [
                        module.__name__,
                        "--report-dir",
                        str(root),
                        "--output",
                        str(output),
                    ],
                ), redirect_stdout(StringIO()):
                    code = module.main()
                self.assertEqual(code, 2)
                file_sha256.assert_not_called()
                artifact = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(
                    artifact["source_research_file_sha256"],
                    hashlib.sha256(raw).hexdigest(),
                )

    def test_explicit_research_report_bypasses_shared_active_source_loader(self) -> None:
        raw = _report_bytes()
        modules = (
            (
                run_internal_execution_rehearsal,
                "run_research_report_execution_rehearsal",
                {"status": "BLOCK", "stage_summary": {}},
            ),
            (
                run_internal_portfolio_statistical_audit,
                "audit_portfolio_research_statistics",
                {"status": "BLOCK", "conclusion": "historical_only", "stages": {}, "audit_hash": "audit"},
            ),
        )
        for module, computation_name, computation_result in modules:
            with self.subTest(module=module.__name__), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source_path = root / "explicit.json"
                output = root / "result.json"
                source_path.write_bytes(raw)
                source = json.loads(raw.decode("utf-8"))
                with patch.object(
                    module,
                    "load_active_portfolio_research_source",
                ) as load_active, patch.object(
                    module,
                    "expand_portfolio_evidence_bundle",
                    return_value=(source, {"status": "PASS", "blockers": []}),
                ), patch.object(
                    module,
                    computation_name,
                    return_value=copy.deepcopy(computation_result),
                ), patch.object(
                    sys,
                    "argv",
                    [
                        module.__name__,
                        "--report-dir",
                        str(root),
                        "--research-report",
                        str(source_path),
                        "--output",
                        str(output),
                    ],
                ), redirect_stdout(StringIO()):
                    code = module.main()
                self.assertEqual(code, 2)
                self.assertTrue(output.is_file())
                load_active.assert_not_called()
                artifact = json.loads(output.read_text(encoding="utf-8"))
                self.assertEqual(artifact["source_research_report"], str(source_path.resolve()))
                self.assertEqual(artifact["active_candidate_hash"], "")


if __name__ == "__main__":
    unittest.main()
