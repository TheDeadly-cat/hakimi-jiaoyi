"""Coverage and failure contracts for the offline terminal CI entry point."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from run_terminal_contracts import TEST_FILES, require_loopback, result_succeeded, validate_coverage


class TerminalCiGateTests(unittest.TestCase):
    def test_checkout_contains_every_required_terminal_test(self):
        self.assertEqual(validate_coverage(), TEST_FILES)

    def test_missing_or_unlisted_terminal_contract_fails_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            tests = root / "outputs/python_quant_bot/tests"
            tests.mkdir(parents=True)
            for name in TEST_FILES:
                (tests / name).touch()
            self.assertEqual(validate_coverage(root), TEST_FILES)
            (tests / "test_terminal_future_feature.py").touch()
            with self.assertRaisesRegex(ValueError, "not_in_gate"):
                validate_coverage(root)
            (tests / "test_terminal_future_feature.py").unlink()
            (tests / "test_terminal_insights.py").unlink()
            with self.assertRaisesRegex(ValueError, "missing"):
                validate_coverage(root)

    def test_only_complete_non_skipped_success_is_accepted(self):
        result = Mock(testsRun=3, skipped=[], expectedFailures=[], unexpectedSuccesses=[])
        result.wasSuccessful.return_value = True
        self.assertTrue(result_succeeded(result, 3))
        for expected in (0, 2, 4):
            self.assertFalse(result_succeeded(result, expected))
        for field in ("skipped", "expectedFailures", "unexpectedSuccesses"):
            setattr(result, field, ["not a complete pass"])
            self.assertFalse(result_succeeded(result, 3))
            setattr(result, field, [])
        result.wasSuccessful.return_value = False
        self.assertFalse(result_succeeded(result, 3))

    def test_local_http_fixture_is_allowed_but_market_or_provider_hosts_are_not(self):
        for address in (("127.0.0.1", 1234), ("::1", 1234), ("localhost", 1234)):
            require_loopback(address)
        for address in (("example.com", 443), ("192.168.1.2", 80), ("8.8.8.8", 443), None, "socket"):
            with self.assertRaisesRegex(AssertionError, "non-loopback"):
                require_loopback(address)


if __name__ == "__main__":
    unittest.main()
