"""Publication preserves accepted bytes and cannot turn private/partial evidence into PASS."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("release_wheel_bundle", ROOT / "tools/release_wheel_bundle.py")
BUNDLE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BUNDLE)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fixture(directory, *, code=b'value = 1\norigin = "https://example.test"\n'):
    wheel = directory / "hakimi_research-0.2.1-py3-none-any.whl"
    lock = b"sample==1.0\n"
    files = {"__init__.py": code, "resources/requirements.research.lock": lock}
    files["runtime-files.json"] = json.dumps({"schema_version": "research-runtime-files-v1", "files": sorted([*files, "runtime-files.json"])}).encode()
    hashes = {name: sha(data) for name, data in files.items()}
    source_hash = sha(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode())
    build = {"schema_version": "research-build-source-v1", "content_sha256": source_hash, "file_hashes": hashes,
             "git": {"commit": "a" * 40, "status": "CLEAN"},
             "build_definition_sha256": {"pyproject.toml": "b" * 64, "setup.py": "c" * 64}}
    with zipfile.ZipFile(wheel, "w") as archive:
        for name, data in files.items():
            archive.writestr("hakimi_research/" + name, data)
        archive.writestr("hakimi_research/_build_identity.json", json.dumps(build))
        archive.writestr("hakimi_research-0.2.1.dist-info/METADATA", "Name: hakimi-research\nVersion: 0.2.1\n")
    return {
        "schema_version": "research-wheel-acceptance-v1", "status": "PASS",
        "wheel": str(wheel), "wheel_sha256": sha(wheel.read_bytes()),
        "python": "C:\\Users\\PRIVATE_USER\\venv\\python.exe", "outside_directory": "/home/PRIVATE_USER/work",
        "account_token": "PRIVATE_CREDENTIAL_NOT_FOR_PUBLICATION", "runner_system": "Windows",
        "editable": False, "pythonpath_used": False, "system_site_packages": False, "source_checkout_unchanged": True,
        "build_inputs_sha256": {**build["build_definition_sha256"], "requirements.research.lock": sha(lock)},
        "independent_test_support_sha256": {"scripts/reconcile_research_ledger.py": "d" * 64},
        "test_inputs_sha256": {"tests/test_contract.py": "e" * 64},
        "tests": ["test_contract.py"], "console_smoke_commands": ["--help", "capabilities", "list-strategies"],
        "test_execution": {"schema_version": "research-installed-test-results-v1", "status": "PASS", "tests_run": 2,
                           "failures": 0, "errors": 0, "skipped": 0, "expected_failures": 0, "unexpected_successes": 0,
                           "test_ids": ["test_contract.ContractTests.test_one", "test_contract.ContractTests.test_two"],
                           "network_policy": "OUTBOUND_PYTHON_SOCKET_ACCESS_DENIED"},
        "installed_runtime": {
            "source_identity": {"status": "BUILD_VERIFIED", "content_sha256": source_hash, "file_hashes": hashes, "build_receipt": build},
            "environment_verified": {"status": "VERIFIED", "lock_sha256": sha(lock), "lock_fully_pinned": True,
                                     "missing": [], "mismatched": [], "errors": [], "packages": {"sample": {"required": "1.0", "installed": "1.0"}},
                                     "python_version": "3.14.6", "python_supported": True},
            "execution_permission": {"research_only": True, "paper_authorized": False, "live_order_allowed": False, "order_entry_allowed": False},
            "machine_receipt": {"machine": "PRIVATE_HOST", "package_location": "C:\\Users\\PRIVATE_USER\\package", "secret": "PRIVATE_CREDENTIAL"},
        },
    }


class ReleaseWheelBundleTests(unittest.TestCase):
    def test_shared_proof_rejects_partial_concurrency_crash_and_private_fields(self):
        workflow=dict(schema_version='installed-shared-funds-workflow-v1',status='PASS',operator='AGENT',data_kind='SYNTHETIC_TEST',
            competition='COMMITTED_RECEIPT_FIFO_ALL_OR_NOTHING',registered_strategies=['price.dual_ma@1','price.buy_and_hold@1',
                'event.earnings_schedule@1','content.price_confirmation@1','content.reviewed_outlook@1'],
            process_proof=dict(concurrent_statuses=['REJECTED','RESERVED'],concurrent_sequence=2,
                crashes=[dict(boundary='before',exit_code=74,committed_receipts=0),dict(boundary='after',exit_code=75,committed_receipts=1)]),
            provider_calls=0,external_account_calls=0,broker_order_calls=0,checkout_data_used=False,source_modified=False)
        for flag in ['actual_cold_console','actual_menu','exit_reopen','task_capital_ignored','all_or_nothing','duplicate_operation_idempotent',
                'terminal_signal_not_reopened','cancel_releases_funds','canonical_settlement','global_loss_latch','conditional_resume',
                'manual_pause_preserved','receipt_lookup','workspace_migration','read_preserves_bytes','independent_backtests_forbidden']:
            workflow[flag]=True
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);receipt=fixture(root);receipt['shared_funds_installed_workflow']=workflow
            BUNDLE.export_bundle(receipt,root/'good')
            self.assertEqual(json.loads((root/'good/installed-shared-funds.json').read_bytes()),workflow)
            clock=deepcopy(workflow);clock['schema_version']='installed-shared-funds-workflow-v2'
            flags=['wrong_clock_rejected_without_account_change','no_op_does_not_poison_clock','legacy_v1_readable_with_original_bytes','legacy_v1_mutation_blocked']
            for flag in flags:clock[flag]=True
            BUNDLE.validate_shared_workflow(clock)
            for flag in flags:
                bad=deepcopy(clock);bad[flag]=False
                with self.subTest(flag=flag),self.assertRaises(ValueError):BUNDLE.validate_shared_workflow(bad)
            symbols=deepcopy(clock);symbols['schema_version']='installed-shared-funds-workflow-v3'
            symbol_flags=['duplicate_symbol_config_rejected_before_publication','distinct_symbol_limits_preserved',
                'legacy_v2_aliases_read_only_original_bytes']
            for flag in symbol_flags:symbols[flag]=True
            BUNDLE.validate_shared_workflow(symbols)
            for flag in symbol_flags:
                bad=deepcopy(symbols);bad[flag]=False
                with self.subTest(flag=flag),self.assertRaises(ValueError):BUNDLE.validate_shared_workflow(bad)
            mutations=[lambda w:w.update(provider_calls=True),lambda w:w.update(broker_order_calls=1),
                lambda w:w.update(actual_menu=False),lambda w:w.update(registered_strategies=[]),
                lambda w:w['process_proof'].update(concurrent_statuses=['RESERVED','RESERVED']),
                lambda w:w['process_proof']['crashes'][0].update(committed_receipts=1),
                lambda w:w['process_proof']['crashes'][1].update(private_path='C:\\Users\\PRIVATE\\account'),
                lambda w:w.update(private_account='PRIVATE')]
            for i,change in enumerate(mutations):
                bad=deepcopy(receipt);change(bad['shared_funds_installed_workflow'])
                with self.subTest(i=i),self.assertRaises(ValueError):BUNDLE.export_bundle(bad,root/('bad-'+str(i)))
                self.assertFalse((root/('bad-'+str(i))).exists())

    def test_exact_wheel_is_exported_with_allowlisted_evidence_and_checkable_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = fixture(root)
            receipt["equity_console_smoke_commands"] = ["--help", "capabilities"]
            original = Path(receipt["wheel"]).read_bytes()
            output = root / "public"
            public = BUNDLE.export_bundle(receipt, output, ci_context={"checkout_sha": "a" * 40, "reviewed_head_sha": "f" * 40, "run_id": "123", "run_attempt": "2"})
            self.assertEqual((output / Path(receipt["wheel"]).name).read_bytes(), original)
            self.assertEqual(Path(receipt["wheel"]).read_bytes(), original)
            self.assertEqual(public["ci_context"]["checkout_sha"], "a" * 40)
            self.assertEqual(public["ci_context"]["reviewed_head_sha"], "f" * 40)
            self.assertEqual(len(list(output.iterdir())), 6)
            scope = json.loads((output / "test-scope.json").read_text(encoding="utf-8"))
            self.assertEqual(scope["equity_console_smoke_commands"], ["--help", "capabilities"])
            for path in output.glob("*.json"):
                content = path.read_text(encoding="utf-8")
                self.assertNotIn("PRIVATE_", content)
                self.assertNotIn(str(root), content)
            lines = (output / "SHA256SUMS.txt").read_text().splitlines()
            self.assertEqual(len(lines), 5)
            for line in lines:
                digest, name = line.split("  ")
                self.assertEqual(sha((output / name).read_bytes()), digest)
            with self.assertRaisesRegex(ValueError, "already exists"):
                BUNDLE.export_bundle(receipt, output)

    def test_installed_input_receipt_preserves_scope_and_rejects_private_or_partial_proof(self):
        # Schema fixtures exercise export rejection, not installed acceptance.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = fixture(root)
            flags = ['actual_installed_cold_console','actual_menu_csv_import','actual_menu_research_binding',
                'snapshot_original_bytes_preserved','research_packet_original_bytes_preserved','missing_context_rejected',
                'paused_task_rejected','rejections_keep_committed_state','task_version_binding','pause_preserved',
                'old_reports_unchanged','schedule_version_changes_filter','unapproved_content_holds',
                'approved_fixture_content_no_intervention_matches_price_result','exit_reopen','workspace_migration','migrated_replay_verified']
            workflow = dict(schema_version='installed-offline-input-workflow-v1',status='PASS',operator='AGENT',
                data_kind='SYNTHETIC_TEST',fixture_review='SYNTHETIC_CONTRACT_RECEIPT_ONLY',
                transcript=[dict(command='input-check',status='INPUTS_APPLICABLE_NO_SIMULATION') for _ in range(30)],
                **{k:True for k in flags}, **{k:0 for k in ['input_checks_new_economic_runs',
                    'comparison_new_economic_runs','migrated_view_new_economic_runs','provider_calls','account_calls','order_calls']},
                human_review_claimed=False,checkout_data_used=False,source_modified=False)
            receipt['input_workflow_installed_workflow'] = workflow
            original = Path(receipt['wheel']).read_bytes()
            BUNDLE.export_bundle(receipt, root/'valid')
            self.assertEqual(json.loads((root/'valid/installed-input-workflow.json').read_bytes()), workflow)
            self.assertEqual(Path(receipt['wheel']).read_bytes(), original)
            changes = [lambda r:r.update(human_review_claimed=True),lambda r:r.update(order_calls=False),
                lambda r:r.update(actual_menu_research_binding=False),lambda r:r.update(local_path=str(root)),
                lambda r:r['transcript'][0].update(command=str(root)),
                lambda r:r['transcript'][0].update(expected_reason='C:/Users/PRIVATE_USER/error')]
            for index, change in enumerate(changes):
                with self.subTest(index=index):
                    bad = deepcopy(receipt)
                    change(bad['input_workflow_installed_workflow'])
                    target = root/f'rejected-input-{index}'
                    with self.assertRaises(ValueError):
                        BUNDLE.export_bundle(bad,target)
                    self.assertFalse(target.exists())
                    self.assertEqual(Path(receipt['wheel']).read_bytes(), original)

    def test_content_boundary_export_rejects_missing_paths_private_fields_and_repeat_economics(self):
        # These are exporter schema fixtures, never installed proof.
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);receipt=fixture(root)
            keys=['price.dual_ma@1','price.buy_and_hold@1','event.earnings_schedule@1',
                'content.price_confirmation@1','content.reviewed_outlook@1']
            flags=['actual_cold_legacy_menu','normal_content_readable','legal_zero_fill_readable',
                'blocked_content_readable','protective_exit_readable','reads_forbid_engines',
                'original_reports_unchanged','rejected_copies_unchanged']
            workflow=dict(schema_version='installed-content-boundary-workflow-v1',status='PASS',operator='AGENT',
                data_kind='SYNTHETIC_TEST',**{k:True for k in flags},checkout_data_used=False,historical_reports_modified=False,
                **{k:0 for k in ['view_recovery_compare_new_economic_runs','provider_calls','account_calls','order_calls']},
                menu_tasks=[dict(strategy=k,configuration_checked=True,run_view_checked=True) for k in keys],
                rehashed_bad_copy_rejections=[dict(case=c,command=v,status='STOPPED',reason='contract_rejected')
                    for c in ['symbol','fill_time','signal_time','fill_basis','wrong-opportunity','duplicate','filtered']
                    for v in ['report','recover','compare']])
            receipt['content_boundary_installed_workflow']=workflow
            BUNDLE.export_bundle(receipt,root/'valid-content')
            self.assertEqual(json.loads((root/'valid-content/installed-content-boundary.json').read_bytes()),workflow)
            changes=[lambda w:w['rehashed_bad_copy_rejections'].pop(),lambda w:w['menu_tasks'].pop(),
                lambda w:w.update(local_path=str(root)),lambda w:w.update(view_recovery_compare_new_economic_runs=1),
                lambda w:w.update(reads_forbid_engines=False),
                lambda w:w['rehashed_bad_copy_rejections'][0].update(reason='C:/Users/PRIVATE_USER/error')]
            for i,change in enumerate(changes):
                bad=deepcopy(receipt);change(bad['content_boundary_installed_workflow']);target=root/f'bad-content-{i}'
                with self.subTest(i=i),self.assertRaises(ValueError):BUNDLE.export_bundle(bad,target)
                self.assertFalse(target.exists())

    def test_changed_wheel_or_mismatched_source_cannot_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = fixture(root)
            wheel = Path(receipt["wheel"])
            original = wheel.read_bytes()
            wheel.write_bytes(original + b"changed")
            with self.assertRaisesRegex(ValueError, "wheel bytes changed"):
                BUNDLE.export_bundle(receipt, root / "changed")
            self.assertFalse((root / "changed").exists())
            wheel.write_bytes(original)
            receipt["installed_runtime"]["source_identity"]["file_hashes"]["__init__.py"] = "f" * 64
            with self.assertRaisesRegex(ValueError, "aggregate mismatch"):
                BUNDLE.export_bundle(receipt, root / "wrong-source")
            self.assertFalse((root / "wrong-source").exists())

    def test_partial_tests_bad_dependencies_or_execution_permission_never_publish(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = fixture(root)
            changes = (
                lambda r: r["test_execution"].update(skipped=1),
                lambda r: r["test_execution"].update(tests_run=0),
                lambda r: r["test_execution"].update(tests_run=3),
                lambda r: r["test_execution"].update(test_ids=["test_contract.ContractTests.test_one"] * 2),
                lambda r: r.update(tests=["test_other.py"]),
                lambda r: r["installed_runtime"]["environment_verified"]["packages"]["sample"].update(installed="9.0"),
                lambda r: r["installed_runtime"]["execution_permission"].update(paper_authorized=True),
                lambda r: r.update(editable=True),
            )
            for index, change in enumerate(changes):
                with self.subTest(index=index):
                    receipt = deepcopy(original)
                    change(receipt)
                    output = root / f"bad-{index}"
                    with self.assertRaises(ValueError):
                        BUNDLE.export_bundle(receipt, output)
                    self.assertFalse(output.exists())

    def test_a_private_path_inside_the_wheel_is_rejected_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = fixture(root, code=b'local = "C:\\Users\\PRIVATE_USER\\secret"\n')
            original = Path(receipt["wheel"]).read_bytes()
            with self.assertRaisesRegex(ValueError, "machine-specific absolute path"):
                BUNDLE.export_bundle(receipt, root / "public")
            self.assertEqual(Path(receipt["wheel"]).read_bytes(), original)
            self.assertFalse((root / "public").exists())

    def test_ci_checkout_identity_cannot_be_relabelled_as_reviewed_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            receipt = fixture(root)
            with self.assertRaisesRegex(ValueError, "checkout differs"):
                BUNDLE.export_bundle(receipt, root / "public", ci_context={"checkout_sha": "f" * 40, "reviewed_head_sha": "f" * 40, "run_id": "123", "run_attempt": "1"})
            self.assertFalse((root / "public").exists())

    def test_installed_runner_records_real_counts_and_rejects_skipped_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "tests"
            tests.mkdir()
            path = tests / "test_example.py"
            for skipped in (False, True):
                with self.subTest(skipped=skipped):
                    decorator = "    @unittest.skip('fixture')\n" if skipped else ""
                    path.write_text("import unittest\nclass Example(unittest.TestCase):\n" + decorator + "    def test_one(self):\n        self.assertEqual(1, 1)\n", encoding="utf-8")
                    output = root / f"result-{skipped}.json"
                    result = subprocess.run([sys.executable, "-B", str(ROOT / "tools/run_installed_acceptance.py"), "--tests", str(tests), "--output", str(output)], cwd=root, capture_output=True, text=True)
                    record = json.loads(output.read_text(encoding="utf-8"))
                    self.assertEqual(result.returncode, 1 if skipped else 0, result.stderr)
                    self.assertEqual(record["tests_run"], 1)
                    self.assertEqual(record["skipped"], int(skipped))
                    self.assertEqual(record["test_ids"], ["test_example.Example.test_one"])


if __name__ == "__main__":
    unittest.main()
