"""Run every terminal contract on fixtures; never replay saved market studies."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[1]
TEST_FILES = (
    "test_causal_structure.py",
    "test_exit_comparison_math.py",
    "test_indicator_contract.py",
    "test_indicator_migration.py",
    "test_offline_execution.py",
    "test_quant_kernel_isolation.py",
    "test_quant_completion_adapter.py",
    "test_quant_workspace.py",
    "test_strategy_presentation.py",
    "test_terminal_ai_evidence.py",
    "test_terminal_ai_strategy_binding.py",
    "test_terminal_candidate_service.py",
    "test_terminal_broker_candidate_service.py",
    "test_terminal_broker_execution_plan.py",
    "test_terminal_broker_wire_profile.py",
    "test_terminal_broker_execution_journal.py",
    "test_terminal_broker_response_facts.py",
    "test_terminal_broker_response_recording.py",
    "test_terminal_broker_worker_supervisor.py",
    "test_terminal_broker_scoped_transport.py",
    "test_futu_us_equity_simulate_wire_v2.py",
    "test_terminal_broker_package_loader.py",
    "test_terminal_broker_plan_service.py",
    "test_terminal_broker_plan_integration.py",
    "test_terminal_broker_plan_routes.py",
    "test_terminal_broker_integration.py",
    "test_terminal_corporate_actions.py",
    "test_terminal_continuous_replay.py",
    "test_terminal_daily_bridge.py",
    "test_terminal_daily_integration.py",
    "test_terminal_daily_research.py",
    "test_terminal_data_preflight.py",
    "test_terminal_execution_integration.py",
    "test_terminal_execution_integration_core.py",
    "test_terminal_execution_explanation.py",
    "test_terminal_execution_service.py",
    "test_terminal_exit_research.py",
    "test_terminal_history.py",
    "test_terminal_insights.py",
    "test_terminal_integration_contract.py",
    "test_terminal_judgment.py",
    "test_terminal_market_data.py",
    "test_terminal_public_daily_access.py",
    "test_terminal_research.py",
    "test_terminal_replay_adapter.py",
    "test_terminal_replay_api.py",
    "test_terminal_replay_capacity.py",
    "test_terminal_replay_integration.py",
    "test_terminal_result_comparison.py",
    "test_terminal_saved_results.py",
    "test_terminal_strategy_candidates.py",
    "test_terminal_task_names.py",
    "test_terminal_workspace_history.py",
    "test_terminal_workspace_history_msix.py",
)
TEST_PATTERNS = (
    "test_terminal_*.py", "test_indicator_*.py", "test_quant_workspace.py",
    "test_quant_kernel_isolation.py", "test_quant_completion_adapter.py", "test_strategy_presentation.py",
    "test_causal_structure.py", "test_exit_comparison_math.py", "test_offline_execution.py",
    "test_futu_us_equity_simulate_wire_v2.py",
)


def validate_coverage(repo_root: Path = REPO_ROOT) -> tuple[str, ...]:
    test_root = repo_root / "outputs/python_quant_bot/tests"
    actual = {path.name for pattern in TEST_PATTERNS for path in test_root.glob(pattern)}
    expected = set(TEST_FILES)
    if len(expected) != len(TEST_FILES) or actual != expected:
        raise ValueError(
            f"terminal test coverage mismatch: missing={sorted(expected - actual)}, "
            f"not_in_gate={sorted(actual - expected)}"
        )
    return TEST_FILES


def require_loopback(address: object) -> None:
    host = address[0] if isinstance(address, tuple) and address else None
    if host == "localhost":
        return
    try:
        if isinstance(host, str) and ipaddress.ip_address(host).is_loopback:
            return
    except ValueError:
        pass
    raise AssertionError(f"terminal contract attempted non-loopback network access: {address!r}")


def build_suite(repo_root: Path = REPO_ROOT) -> tuple[unittest.TestSuite, dict[str, int]]:
    names = validate_coverage(repo_root)
    terminal_root = repo_root / "outputs/python_quant_bot"
    # This repository harness needs terminal tests and their sibling fixtures.
    # Do not inject src or the frozen vendor into the interpreter search path:
    # the canonical package must already be installed, as in the CI job.
    sys.path[:0] = [str(terminal_root / "tests"), str(terminal_root)]
    suite = unittest.TestSuite()
    counts = {}
    for name in names:
        loaded = unittest.defaultTestLoader.loadTestsFromName(Path(name).stem)
        count = loaded.countTestCases()
        if count == 0:
            raise ValueError(f"terminal contract collected no tests: {name}")
        counts[name] = count
        suite.addTests(loaded)
    return suite, counts


def result_succeeded(result: unittest.TestResult, expected_count: int) -> bool:
    return (expected_count > 0 and result.testsRun == expected_count
            and result.wasSuccessful() and not result.skipped
            and not result.expectedFailures and not result.unexpectedSuccesses)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-coverage", action="store_true")
    args = parser.parse_args(argv)
    validate_coverage()
    if args.check_coverage:
        print(json.dumps({"terminal_contract_files": list(TEST_FILES), "coverage": "PASS"}))
        return 0
    os.environ["HAKIMI_SKIP_LOCAL_AI_ENV"] = "1"
    os.environ["HAKIMI_RUNTIME_READ_ONLY"] = "1"
    original_connect, original_connect_ex = socket.socket.connect, socket.socket.connect_ex
    original_getaddrinfo = socket.getaddrinfo

    def connect(sock, address):
        require_loopback(address)
        return original_connect(sock, address)

    def connect_ex(sock, address):
        require_loopback(address)
        return original_connect_ex(sock, address)

    def getaddrinfo(host, port, *values, **kwargs):
        require_loopback((host, port))
        return original_getaddrinfo(host, port, *values, **kwargs)

    with ExitStack() as stack:
        stack.enter_context(patch.object(socket.socket, "connect", connect))
        stack.enter_context(patch.object(socket.socket, "connect_ex", connect_ex))
        stack.enter_context(patch.object(socket, "getaddrinfo", getaddrinfo))
        suite, counts = build_suite()
        result = unittest.TextTestRunner(verbosity=2).run(suite)
    success = result_succeeded(result, sum(counts.values()))
    print(json.dumps({"terminal_contracts": "PASS" if success else "FAIL",
                      "files": counts, "tests_run": result.testsRun,
                      "skipped": len(result.skipped), "failures": len(result.failures),
                      "errors": len(result.errors), "external_network_allowed": False}))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
