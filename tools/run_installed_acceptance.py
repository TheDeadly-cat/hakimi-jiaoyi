"""Run the copied offline tests against the installed wheel and record real outcomes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.test_ids = []

    def startTest(self, test):
        self.test_ids.append(test.id())
        super().startTest(test)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    def deny_network(event, _args):
        if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
            raise RuntimeError("installed_acceptance_network_access_denied")

    sys.addaudithook(deny_network)
    suite = unittest.defaultTestLoader.discover(str(args.tests), pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(suite)
    counts = {
        "tests_run": result.testsRun,
        "failures": len(result.failures), "errors": len(result.errors),
        "skipped": len(result.skipped), "expected_failures": len(result.expectedFailures),
        "unexpected_successes": len(result.unexpectedSuccesses),
    }
    passed = counts["tests_run"] > 0 and all(value == 0 for name, value in counts.items() if name != "tests_run")
    record = {
        "schema_version": "research-installed-test-results-v1",
        "status": "PASS" if passed else "FAIL", **counts,
        "test_ids": sorted(result.test_ids),
        "network_policy": "OUTBOUND_PYTHON_SOCKET_ACCESS_DENIED",
    }
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(record, stream, indent=2, sort_keys=True)
        stream.write("\n")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
