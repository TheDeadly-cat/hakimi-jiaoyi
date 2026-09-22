"""Portable preview identity, offline display and explicit installation boundaries."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


PREVIEW = module("supervised_preview", ROOT / "tools/supervised_preview.py")
EXPORT = module("release_wheel_bundle", ROOT / "tools/release_wheel_bundle.py")
with patch.dict(sys.modules, supervised_preview=PREVIEW, release_wheel_bundle=EXPORT):
    BUILD = module("build_supervised_preview", ROOT / "tools/build_supervised_preview.py")


def bundle(path, kind="research", *, followup=False):
    files = {
        "preview.py": (ROOT / "tools/supervised_preview.py").read_bytes(),
        "evidence/amd-research-summary.json": (ROOT / BUILD.EVIDENCE["evidence/amd-research-summary.json"]).read_bytes(),
        "evidence/futu-preflight-20260920.json": (ROOT / BUILD.EVIDENCE["evidence/futu-preflight-20260920.json"]).read_bytes(),
    }
    if followup:
        for name in ('evidence/futu-readonly-followup.json', 'evidence/equity-events/study-final-results.json'):
            files[name] = (ROOT / BUILD.EVIDENCE[name]).read_bytes()
    record = BUILD.write_bundle(path, kind, files, {"version": "test", "source": {"test_fixture": True}})
    return path / record["directory"]


class SupervisedPreviewTests(unittest.TestCase):
    def test_latest_evidence_preserves_first_failure_unknown_and_excluded_events_without_running(self):
        with tempfile.TemporaryDirectory() as temp:
            root = bundle(Path(temp), followup=True)
            with patch.object(PREVIEW.subprocess, 'run', side_effect=AssertionError('unexpected process')):
                status = PREVIEW.show_status(root)
            orders = status['order_test']
            self.assertEqual(orders['first_preflight_preserved']['status'], 'PREFLIGHT_INCOMPLETE')
            self.assertEqual(orders['latest_retained_preflight']['initial_order_gate']['status'], 'BLOCKED_EXISTING_PROVIDER_ORDERS')
            self.assertTrue(orders['latest_retained_preflight']['stable_read_completed'])
            self.assertFalse(orders['latest_retained_preflight']['account_state_checked_now'])
            self.assertFalse(orders['latest_retained_preflight']['regular_session_open'])
            self.assertEqual(orders['latest_retained_preflight']['orders_sent'], 0)
            study = status['completed_fixed_event_study']
            self.assertEqual(study['event_coverage']['planned'], 10)
            self.assertEqual(study['event_coverage']['AB_completed'], 7)
            self.assertEqual(sum(e['status'] == 'PENDING_DATA_CROSSCHECK' for e in study['events']), 3)
            self.assertEqual(study['reports_verified'], 42)
            self.assertFalse(study['rerun_by_status_command'])
            self.assertFalse(study['profitability_verified'])

    def test_same_inputs_have_identical_content_address_and_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            first = bundle(root / "first")
            second = bundle(root / "second")
            self.assertEqual(first.name, second.name)
            self.assertEqual(first.with_suffix(".zip").read_bytes(), second.with_suffix(".zip").read_bytes())

    def test_status_is_history_and_never_invokes_a_runtime_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            root = bundle(Path(temp))
            with patch.object(PREVIEW.subprocess, "run", side_effect=AssertionError("unexpected process")):
                status = PREVIEW.show_status(root)
            self.assertEqual(status["installation"]["status"], "NOT_CHECKED")
            self.assertEqual(status["runtime_health"]["live_processes_accounts_databases"], "NOT_CHECKED")
            self.assertEqual(status["order_test"]["status"], "NOT_RUN_BY_PREVIEW")
            self.assertEqual(status["order_test"]["latest_retained_preflight"]["status"], "PREFLIGHT_INCOMPLETE")
            self.assertEqual(status["order_test"]["latest_retained_preflight"]["observed_gate"], "provider_order_quantity_or_price_invalid")
            self.assertEqual(status["order_test"]["latest_retained_preflight"]["orders_sent"], 0)
            self.assertLess(status["historical_sample"]["A"]["total_return"], 0)
            self.assertEqual(status["historical_sample"]["B"]["blocked_new_buy_intents"], 0)

    def test_changed_payload_is_rejected_before_install_or_process(self):
        with tempfile.TemporaryDirectory() as temp:
            root = bundle(Path(temp))
            (root / "preview.py").write_text("changed", encoding="utf-8")
            with patch.object(PREVIEW.subprocess, "run", side_effect=AssertionError("unexpected process")):
                with self.assertRaisesRegex(ValueError, "file_identity_mismatch"):
                    PREVIEW.show_status(root)

    def test_manifest_cannot_escape_bundle_even_with_recomputed_identity(self):
        with tempfile.TemporaryDirectory() as temp:
            root = bundle(Path(temp))
            path = root / "preview-manifest.json"
            manifest = json.loads(path.read_bytes())
            manifest["files"]["../secret.json"] = "0" * 64
            core = {k: v for k, v in manifest.items() if k != "build_id"}
            manifest["build_id"] = "supervised-research-" + PREVIEW.sha(PREVIEW.canonical(core))
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "file_path_invalid"):
                PREVIEW.verify_bundle(root)

    def test_referenced_evidence_must_be_a_hashed_bundle_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = bundle(Path(temp))
            path = root / "preview-manifest.json"
            manifest = json.loads(path.read_bytes())
            manifest["observation_summary"] = "../private.json"
            core = {k: v for k, v in manifest.items() if k != "build_id"}
            manifest["build_id"] = "supervised-research-" + PREVIEW.sha(PREVIEW.canonical(core))
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "reference_not_bound"):
                PREVIEW.show_status(root)

    def test_install_needs_explicit_dependency_source_before_any_write(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = bundle(base)
            runtime = base / "runtime"
            with self.assertRaisesRegex(ValueError, "supply_wheelhouse"):
                PREVIEW.install(root, runtime)
            self.assertFalse(runtime.exists())
            with self.assertRaisesRegex(ValueError, "runtime_must_be_outside"):
                PREVIEW.install(root, root / "runtime", allow_downloads=True)

    def test_failed_or_existing_environment_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            root = bundle(base)
            runtime = base / "runtime"
            (runtime / "research-env").mkdir(parents=True)
            marker = runtime / "research-env/preserve.txt"
            marker.write_text("first failure", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "destination_exists"):
                PREVIEW.install(root, runtime, allow_downloads=True)
            self.assertEqual(marker.read_text(), "first failure")


if __name__ == "__main__":
    unittest.main()
