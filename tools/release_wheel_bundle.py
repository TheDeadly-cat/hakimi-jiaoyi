"""Export only the exact accepted wheel and allowlisted, portable public evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile


_SHA = re.compile(r"[0-9a-f]{64}")
_COMMIT = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_PATH = re.compile(r"[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*")
_PRIVATE_PATH = re.compile(rb"(?i)(?<![A-Za-z0-9])(?:[a-z]:[\\/]|/(?:home|Users|tmp|private)/)")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _json_bytes(value):
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True, allow_nan=False) + "\n").encode("utf-8")


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _relative(name):
    _require(type(name) is str and _PATH.fullmatch(name) is not None and ".." not in PurePosixPath(name).parts, "public evidence path is not relative")
    return name


def _hashes(mapping):
    _require(type(mapping) is dict and mapping, "source hashes missing")
    checked = {}
    for name, value in mapping.items():
        _require(type(value) is str and _SHA.fullmatch(value) is not None, "invalid evidence hash")
        checked[_relative(name)] = value
    return checked


def _git(value):
    _require(type(value) is dict and set(value) == {"commit", "status"} and value.get("status") in {"CLEAN", "DIRTY", "UNKNOWN"}, "invalid source Git observation")
    commit = value.get("commit")
    _require(type(commit) is str and (commit == "" or _COMMIT.fullmatch(commit)), "invalid source commit")
    return {"commit": commit, "status": value["status"]}


def validate_shared_workflow(workflow):
    true_fields={'actual_cold_console','actual_menu','exit_reopen','task_capital_ignored','all_or_nothing',
        'duplicate_operation_idempotent','terminal_signal_not_reopened','cancel_releases_funds','canonical_settlement',
        'global_loss_latch','conditional_resume','manual_pause_preserved','receipt_lookup','workspace_migration',
        'read_preserves_bytes','independent_backtests_forbidden'}
    zeros={'provider_calls','external_account_calls','broker_order_calls'}
    false_fields={'checkout_data_used','source_modified'}
    headers={'schema_version','status','operator','data_kind','competition','registered_strategies','process_proof'}
    _require(type(workflow) is dict and set(workflow)==headers|true_fields|zeros|false_fields,'shared workflow receipt shape changed')
    _require(workflow['schema_version']=='installed-shared-funds-workflow-v1' and workflow['status']=='PASS'
        and workflow['operator']=='AGENT' and workflow['data_kind']=='SYNTHETIC_TEST'
        and workflow['competition']=='COMMITTED_RECEIPT_FIFO_ALL_OR_NOTHING','shared workflow identity invalid')
    _require(all(workflow[k] is True for k in true_fields) and all(workflow[k] is False for k in false_fields)
        and all(type(workflow[k]) is int and workflow[k]==0 for k in zeros),'shared workflow proof incomplete')
    _require(workflow['registered_strategies']==['price.dual_ma@1','price.buy_and_hold@1','event.earnings_schedule@1',
        'content.price_confirmation@1','content.reviewed_outlook@1'],'shared strategy coverage incomplete')
    proof=workflow['process_proof']
    _require(type(proof) is dict and set(proof)=={'concurrent_statuses','concurrent_sequence','crashes'}
        and proof['concurrent_statuses']==['REJECTED','RESERVED'] and type(proof['concurrent_sequence']) is int
        and proof['concurrent_sequence']==2,'shared concurrent process proof incomplete')
    rows=proof['crashes']
    _require(type(rows) is list and len(rows)==2,'shared crash proof missing')
    for row,mode,code,count in zip(rows,['before','after'],[74,75],[0,1]):
        _require(type(row) is dict and set(row)=={'boundary','exit_code','committed_receipts'} and row['boundary']==mode
            and type(row['exit_code']) is int and row['exit_code']==code and type(row['committed_receipts']) is int
            and row['committed_receipts']==count,'shared crash proof invalid')
    return workflow


def export_bundle(receipt: dict, output_dir: Path, *, ci_context: dict | None = None) -> dict:
    """Validate all links before writing; never redact, rebuild, or rewrite the wheel."""
    _require(receipt.get("schema_version") == "research-wheel-acceptance-v1" and receipt.get("status") == "PASS", "wheel acceptance did not pass")
    for name in ("editable", "pythonpath_used", "system_site_packages"):
        _require(receipt.get(name) is False, "installation isolation not proven")
    _require(receipt.get("source_checkout_unchanged") is True, "source changed during acceptance")
    wheel = Path(receipt["wheel"])
    _require(wheel.is_file() and not wheel.is_symlink() and wheel.name.endswith(".whl"), "accepted wheel missing")
    _relative(wheel.name)
    wheel_bytes = wheel.read_bytes()
    _require(_sha(wheel_bytes) == receipt.get("wheel_sha256"), "accepted wheel bytes changed")
    runtime = receipt["installed_runtime"]
    source = runtime["source_identity"]
    environment = runtime["environment_verified"]
    _require(source.get("status") == "BUILD_VERIFIED" and environment.get("status") == "VERIFIED", "installed provenance not verified")
    file_hashes = _hashes(source["file_hashes"])
    aggregate = _sha(json.dumps(file_hashes, sort_keys=True, separators=(",", ":")).encode())
    _require(aggregate == source.get("content_sha256"), "source hash aggregate mismatch")
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        _require(len(names) == len(set(names)), "wheel contains duplicate members")
        for name in names:
            _relative(name)
            _require(not _PRIVATE_PATH.search(archive.read(name)), "wheel contains a machine-specific absolute path")
        package_files = {name.removeprefix("hakimi_research/") for name in names if name.startswith("hakimi_research/")}
        _require(package_files == set(file_hashes) | {"_build_identity.json"}, "wheel runtime files differ from installed evidence")
        actual_hashes = {name: _sha(archive.read("hakimi_research/" + name)) for name in file_hashes}
        _require(actual_hashes == file_hashes, "wheel source bytes differ from installed evidence")
        raw_build = json.loads(archive.read("hakimi_research/_build_identity.json"))
        _require(raw_build == source.get("build_receipt"), "wheel build receipt differs from installed evidence")
        _require(set(raw_build) == {"schema_version", "content_sha256", "file_hashes", "git", "build_definition_sha256"}, "unexpected build receipt fields")
        _require(raw_build["schema_version"] == "research-build-source-v1" and raw_build["content_sha256"] == aggregate and raw_build["file_hashes"] == file_hashes, "wheel build identity mismatch")
        lock_bytes = archive.read("hakimi_research/resources/requirements.research.lock")
    build_definitions = _hashes(raw_build["build_definition_sha256"])
    _require(set(build_definitions) == {"pyproject.toml", "setup.py"}, "build definition identity incomplete")
    build_inputs = _hashes(receipt["build_inputs_sha256"])
    _require(set(build_inputs) == {"pyproject.toml", "setup.py", "requirements.research.lock"}, "acceptance build inputs incomplete")
    _require(all(build_inputs[name] == value for name, value in build_definitions.items()), "acceptance and wheel build definitions differ")
    _require(_sha(lock_bytes) == build_inputs["requirements.research.lock"] == environment["lock_sha256"], "accepted dependency lock differs from wheel")
    _require(environment.get("lock_fully_pinned") is True and all(environment.get(name) == [] for name in ("missing", "mismatched", "errors")), "dependency evidence incomplete")
    packages = {}
    for line in lock_bytes.decode("utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9._-]*)==([A-Za-z0-9][A-Za-z0-9.!+_-]*)", line.strip())
        _require(match is not None, "dependency lock is not exact pins")
        name, version = match.groups()
        name = re.sub(r"[-_.]+", "-", name).lower()
        _require(name not in packages and environment["packages"].get(name) == {"required": version, "installed": version}, "dependency versions differ from lock")
        packages[name] = {"required": version, "installed": version}
    _require(packages and set(packages) == set(environment["packages"]), "dependency package set mismatch")
    python_version = environment.get("python_version")
    _require(type(python_version) is str and _VERSION.fullmatch(python_version) and environment.get("python_supported") is True, "Python version evidence invalid")
    tests = receipt["test_execution"]
    _require(tests.get("schema_version") == "research-installed-test-results-v1" and tests.get("status") == "PASS", "test execution evidence missing")
    count = tests.get("tests_run")
    _require(type(count) is int and count > 0, "no installed tests executed")
    for name in ("failures", "errors", "skipped", "expected_failures", "unexpected_successes"):
        _require(type(tests.get(name)) is int and tests[name] == 0, "installed test failure or skipped coverage")
    ids = tests.get("test_ids")
    _require(type(ids) is list and len(ids) == count and all(type(item) is str and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", item) for item in ids), "test identities invalid")
    _require(ids == sorted(set(ids)), "test identities duplicated or unordered")
    _require(tests.get("network_policy") == "OUTBOUND_PYTHON_SOCKET_ACCESS_DENIED", "offline test boundary missing")
    modules = receipt["tests"]
    _require(type(modules) is list and modules and modules == sorted(set(modules)) and all(_relative(name).startswith("test_") and name.endswith(".py") and "/" not in name for name in modules), "test scope modules invalid")
    _require({item.split(".", 1)[0] + ".py" for item in ids} == set(modules), "test execution does not cover declared modules")
    support = _hashes(receipt["independent_test_support_sha256"])
    test_inputs = _hashes(receipt["test_inputs_sha256"])
    _require(all("tests/" + name in test_inputs for name in modules), "test source identity missing")
    permission = runtime.get("execution_permission")
    _require(permission == {"research_only": True, "paper_authorized": False, "live_order_allowed": False, "order_entry_allowed": False}, "research-only boundary invalid")
    system = receipt.get("runner_system")
    _require(system in {"Windows", "Linux", "Darwin"}, "runner operating system invalid")
    context = {"runner_system": system}
    if ci_context:
        _require(set(ci_context) == {"checkout_sha", "reviewed_head_sha", "run_id", "run_attempt"}, "CI identity fields invalid")
        for name in ("checkout_sha", "reviewed_head_sha"):
            _require(type(ci_context[name]) is str and _COMMIT.fullmatch(ci_context[name]), "CI commit identity invalid")
        for name in ("run_id", "run_attempt"):
            _require(type(ci_context[name]) is str and re.fullmatch(r"[1-9][0-9]*", ci_context[name]), "CI run identity invalid")
        _require(ci_context["checkout_sha"] == raw_build["git"]["commit"], "CI checkout differs from wheel build commit")
        context.update(ci_context)
    build = {"schema_version": raw_build["schema_version"], "content_sha256": aggregate,
             "file_hashes": file_hashes, "git": _git(raw_build["git"]), "build_definition_sha256": build_definitions}
    public_acceptance = {
        "schema_version": "research-wheel-acceptance-public-v1", "status": "PASS",
        "wheel": wheel.name, "wheel_sha256": receipt["wheel_sha256"], "source_content_sha256": aggregate,
        "build_git": build["git"], "ci_context": context,
        "installation": {"editable": False, "pythonpath_used": False, "system_site_packages": False, "outside_checkout": True},
        "source_checkout_unchanged": True, "build_inputs_sha256": build_inputs,
        "execution_permission": permission,
        "scope": "EXACT_WHEEL_INSTALLATION_AND_OFFLINE_CONTRACTS_NOT_MARKET_OR_STRATEGY_VALIDATION",
        "privacy": "ALLOWLISTED_METADATA_MACHINE_RECEIPT_AND_LOCAL_PATHS_OMITTED_WHEEL_UNCHANGED",
    }
    test_scope = {"schema_version": "research-installed-test-scope-v1", "wheel_sha256": receipt["wheel_sha256"],
                  "execution": {name: tests[name] for name in ("status", "tests_run", "failures", "errors", "skipped", "expected_failures", "unexpected_successes", "test_ids", "network_policy")},
                  "modules": modules, "independent_test_support_sha256": support,
                  "test_inputs_sha256": test_inputs,
                  "console_smoke_commands": ["--help", "capabilities", "list-strategies"]}
    _require(receipt.get("console_smoke_commands") == test_scope["console_smoke_commands"], "console smoke coverage changed")
    if "equity_console_smoke_commands" in receipt:
        _require(receipt["equity_console_smoke_commands"] == ["--help", "capabilities"], "equity console smoke coverage changed")
        test_scope["equity_console_smoke_commands"] = ["--help", "capabilities"]
    if "trade_console_smoke_commands" in receipt:
        _require(receipt["trade_console_smoke_commands"] == ["--help", "capabilities", "strategies"], "trade console smoke coverage changed")
        workflow = receipt["trade_installed_workflow"]
        _require(set(workflow) == {"schema_version", "status", "data_kind", "task_results", "source_workflow", "checkout_data_used", "source_modified"}, "trade workflow receipt shape changed")
        _require(workflow["schema_version"] == "offline-tool-installed-workflow-v1" and workflow["status"] == "PASS"
            and workflow["data_kind"] == "SYNTHETIC_TEST" and workflow["source_workflow"] is True
            and workflow["checkout_data_used"] is False and workflow["source_modified"] is False, "trade installed workflow not proven")
        _require(len(workflow["task_results"]) == 2 and all(set(row) == {"task_id", "replay_verified", "report_recovered", "recovery_new_economic_runs"}
            and row["replay_verified"] is True and row["report_recovered"] is True and row["recovery_new_economic_runs"] == 0
            for row in workflow["task_results"]), "trade installed task coverage incomplete")
        _require(all(re.fullmatch("[0-9a-f]{64}", row["task_id"]) for row in workflow["task_results"]), "trade task identity invalid")
        test_scope["trade_console_smoke_commands"] = receipt["trade_console_smoke_commands"]
        test_scope["trade_installed_workflow"] = workflow
    files = {
        wheel.name: wheel_bytes,
        "wheel-acceptance.json": _json_bytes(public_acceptance),
        "source-build-identity.json": _json_bytes(build),
        "dependencies.json": _json_bytes({"schema_version": "research-accepted-dependencies-v1", "status": "VERIFIED", "python_version": python_version, "lock_sha256": _sha(lock_bytes), "packages": packages}),
        "test-scope.json": _json_bytes(test_scope),
    }
    if 'input_workflow_installed_workflow' in receipt:
        workflow = receipt['input_workflow_installed_workflow']
        true_flags = ['actual_installed_cold_console','actual_menu_csv_import','actual_menu_research_binding',
            'snapshot_original_bytes_preserved','research_packet_original_bytes_preserved','missing_context_rejected',
            'paused_task_rejected','rejections_keep_committed_state','task_version_binding','pause_preserved',
            'old_reports_unchanged','schedule_version_changes_filter','unapproved_content_holds',
            'approved_fixture_content_no_intervention_matches_price_result','exit_reopen','workspace_migration','migrated_replay_verified']
        zero_fields = ['input_checks_new_economic_runs','comparison_new_economic_runs','migrated_view_new_economic_runs',
            'provider_calls','account_calls','order_calls']
        false_flags = ['human_review_claimed','checkout_data_used','source_modified']
        headers = {'schema_version','status','operator','data_kind','fixture_review','transcript'}
        _require(set(workflow)==headers|set(true_flags)|set(zero_fields)|set(false_flags), 'input workflow receipt shape changed')
        _require(workflow['schema_version']=='installed-offline-input-workflow-v1' and workflow['status']=='PASS'
            and workflow['operator']=='AGENT' and workflow['data_kind']=='SYNTHETIC_TEST'
            and workflow['fixture_review']=='SYNTHETIC_CONTRACT_RECEIPT_ONLY', 'installed input workflow not proven')
        _require(all(workflow[k] is True for k in true_flags) and all(workflow[k] is False for k in false_flags)
            and all(type(workflow[k]) is int and workflow[k]==0 for k in zero_fields), 'input workflow proof incomplete')
        _require(type(workflow['transcript']) is list and len(workflow['transcript'])>=30, 'input workflow console transcript missing')
        for row in workflow['transcript']:
            _require(set(row) in ({'command','status'},{'command','status','expected_reason'}), 'input transcript shape invalid')
            _require(type(row['command']) is str and re.fullmatch(r'[a-z-]+',row['command'])
                and type(row['status']) is str and re.fullmatch(r'[A-Z0-9_]+',row['status']), 'input transcript must omit local paths')
            if 'expected_reason' in row:
                _require(type(row['expected_reason']) is str and re.fullmatch(r'[a-z0-9_]+',row['expected_reason']), 'input rejection receipt must omit local paths')
        files['installed-input-workflow.json'] = _json_bytes(workflow)
    if 'content_boundary_installed_workflow' in receipt:
        workflow = receipt['content_boundary_installed_workflow']
        true_fields = {'actual_cold_legacy_menu','normal_content_readable','legal_zero_fill_readable',
            'blocked_content_readable','protective_exit_readable','reads_forbid_engines','original_reports_unchanged','rejected_copies_unchanged'}
        false_fields = {'checkout_data_used','historical_reports_modified'}
        zero_fields = {'view_recovery_compare_new_economic_runs','provider_calls','account_calls','order_calls'}
        headers = {'schema_version','status','operator','data_kind','menu_tasks','rehashed_bad_copy_rejections'}
        _require(set(workflow)==headers|true_fields|false_fields|zero_fields, 'content boundary receipt shape changed')
        _require(workflow['schema_version']=='installed-content-boundary-workflow-v1' and workflow['status']=='PASS'
            and workflow['operator']=='AGENT' and workflow['data_kind']=='SYNTHETIC_TEST', 'content boundary workflow not proven')
        _require(all(workflow[k] is True for k in true_fields) and all(workflow[k] is False for k in false_fields)
            and all(type(workflow[k]) is int and workflow[k]==0 for k in zero_fields), 'content boundary proof incomplete')
        keys = ['price.dual_ma@1','price.buy_and_hold@1','event.earnings_schedule@1','content.price_confirmation@1','content.reviewed_outlook@1']
        _require(type(workflow['menu_tasks']) is list and [r.get('strategy') for r in workflow['menu_tasks']]==keys, 'legacy menu strategy coverage incomplete')
        _require(all(set(r)=={'strategy','configuration_checked','run_view_checked'} and r['configuration_checked'] is True
            and r['run_view_checked'] is True for r in workflow['menu_tasks']), 'legacy menu task receipt invalid')
        cases = {'symbol','fill_time','signal_time','fill_basis','wrong-opportunity','duplicate','filtered'}
        rows = workflow['rehashed_bad_copy_rejections']
        _require(type(rows) is list and len(rows)==21, 'content rejection coverage incomplete')
        _require({(r.get('case'),r.get('command')) for r in rows}=={(c,v) for c in cases for v in ['report','recover','compare']}, 'content rejection paths incomplete')
        _require(all(set(r)=={'case','command','status','reason'} and r['status']=='STOPPED'
            and type(r['reason']) is str and re.fullmatch(r'[a-z_]+',r['reason']) for r in rows), 'content rejection receipt must omit local paths')
        files['installed-content-boundary.json'] = _json_bytes(workflow)
    if wheel.name.split('-')[1].startswith('0.5.'):
        _require('shared_funds_installed_workflow' in receipt,'M3 shared funds installed proof required')
    if 'shared_funds_installed_workflow' in receipt:
        files['installed-shared-funds.json']=_json_bytes(validate_shared_workflow(receipt['shared_funds_installed_workflow']))
    files["SHA256SUMS.txt"] = "".join(f"{_sha(data)}  {name}\n" for name, data in sorted(files.items())).encode()
    output_dir = Path(output_dir)
    _require(not output_dir.exists(), "public bundle destination already exists")
    output_dir.mkdir(parents=True)
    for name, data in files.items():
        with (output_dir / name).open("xb") as stream:
            stream.write(data)
        _require((output_dir / name).read_bytes() == data, "public bundle write verification failed")
    _require(wheel.read_bytes() == wheel_bytes, "accepted wheel changed during export")
    return public_acceptance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    export_bundle(json.loads(args.acceptance.read_text(encoding="utf-8")), args.output)
