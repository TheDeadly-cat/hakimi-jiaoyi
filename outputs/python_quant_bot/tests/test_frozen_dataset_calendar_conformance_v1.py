from __future__ import annotations

from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import sys
import unittest
from typing import Any

import pandas as pd


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
BOT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for candidate in (str(SRC_ROOT), str(BOT_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from hakimi_research.dataset_calendar_conformance import (  # noqa: E402
    SCHEMA_VERSION,
    build_dataset_calendar_conformance,
    verify_dataset_calendar_conformance,
)
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_protocol,
    build_frozen_evaluation_report,
)
from tests.test_frozen_evaluation_protocol_v1 import (  # noqa: E402
    config,
    context,
    dataset_governance,
    protocol,
    synthetic_frame,
)


class HostileStr(str):
    calls = 0

    def _fail(self, *_args: Any, **_kwargs: Any) -> Any:
        type(self).calls += 1
        raise AssertionError("subclass-controlled text method invoked")

    strip = _fail
    lower = _fail
    encode = _fail
    __str__ = _fail


class HostileDict(dict):
    calls = 0

    def _fail(self, *_args: Any, **_kwargs: Any) -> Any:
        type(self).calls += 1
        raise AssertionError("subclass-controlled mapping method invoked")

    get = _fail
    items = _fail
    keys = _fail
    values = _fail
    __iter__ = _fail


def time_contract() -> dict[str, str]:
    return deepcopy(dataset_governance()["time"])


def irregular_frame() -> pd.DataFrame:
    frame = synthetic_frame()
    frame.index = pd.DatetimeIndex([
        timestamp if index < 64 else timestamp + timedelta(days=1)
        for index, timestamp in enumerate(frame.index)
    ])
    return frame


class FrozenDatasetCalendarConformanceV1Tests(unittest.TestCase):
    def test_canonical_source_is_outside_outputs_and_versioned(self) -> None:
        source = SRC_ROOT / "hakimi_research" / "dataset_calendar_conformance.py"
        self.assertTrue(source.is_file())
        self.assertNotIn("outputs", source.relative_to(REPO_ROOT).parts)
        self.assertEqual(SCHEMA_VERSION, "dataset-calendar-conformance-v1")

    def test_synthetic_daily_schedule_is_exact_and_self_verifying(self) -> None:
        frame = synthetic_frame()
        evidence = build_dataset_calendar_conformance(
            frame.index,
            time_contract=time_contract(),
            timeframe="1d",
            source_kind="SYNTHETIC_FIXTURE",
        )
        self.assertEqual(evidence["status"], "PASS")
        self.assertEqual(evidence["provider"], "DETERMINISTIC_SYNTHETIC_DAILY")
        self.assertEqual(evidence["observed_count"], 128)
        self.assertEqual(evidence["expected_count"], 128)
        self.assertEqual(evidence["missing_timestamps"], [])
        self.assertEqual(evidence["unexpected_timestamps"], [])
        self.assertTrue(
            verify_dataset_calendar_conformance(
                evidence,
                frame.index,
                time_contract=time_contract(),
                timeframe="1d",
                source_kind="SYNTHETIC_FIXTURE",
            )
        )

    def test_two_day_gap_is_explicitly_blocked(self) -> None:
        evidence = build_dataset_calendar_conformance(
            irregular_frame().index,
            time_contract=time_contract(),
            timeframe="1d",
            source_kind="SYNTHETIC_FIXTURE",
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertEqual(len(evidence["missing_timestamps"]), 1)
        self.assertIn("CALENDAR_TIMESTAMPS_MISSING:1", evidence["blockers"])

    def test_frozen_protocol_rejects_irregular_declared_daily_timeline(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "frozen_evaluation_dataset_calendar_conformance_failed",
        ):
            build_frozen_evaluation_protocol(
                irregular_frame(),
                config(),
                dataset_governance=dataset_governance(),
                train_rows=40,
                purge_rows=4,
                validation_rows=40,
                embargo_rows=4,
                frozen_test_rows=40,
                random_seed=17,
                experiment_context=context(),
            )

    def test_real_exchange_calendar_requires_external_schedule_attestation(self) -> None:
        declared = time_contract()
        declared["trading_calendar"] = "XNYS"
        declared["session_policy"] = "EXCHANGE_SESSIONS"
        evidence = build_dataset_calendar_conformance(
            synthetic_frame().index,
            time_contract=declared,
            timeframe="1d",
            source_kind="PUBLIC_MARKET_DATA",
        )
        self.assertEqual(evidence["status"], "BLOCK")
        self.assertEqual(
            evidence["blockers"],
            ["EXTERNAL_SCHEDULE_ATTESTATION_REQUIRED"],
        )

    def test_non_native_values_never_invoke_subclass_methods(self) -> None:
        HostileStr.calls = HostileDict.calls = 0
        with self.assertRaisesRegex(ValueError, "dataset_calendar_conformance_"):
            build_dataset_calendar_conformance(
                synthetic_frame().index,
                time_contract=HostileDict(time_contract()),
                timeframe="1d",
                source_kind="SYNTHETIC_FIXTURE",
            )
        with self.assertRaisesRegex(ValueError, "dataset_calendar_conformance_"):
            build_dataset_calendar_conformance(
                synthetic_frame().index,
                time_contract=time_contract(),
                timeframe="1d",
                source_kind=HostileStr("SYNTHETIC_FIXTURE"),
            )
        self.assertEqual((HostileStr.calls, HostileDict.calls), (0, 0))

    def test_tampered_evidence_fails_recomputation(self) -> None:
        frame = synthetic_frame()
        evidence = build_dataset_calendar_conformance(
            frame.index,
            time_contract=time_contract(),
            timeframe="1d",
            source_kind="SYNTHETIC_FIXTURE",
        )
        evidence["observed_count"] -= 1
        with self.assertRaisesRegex(
            ValueError,
            "dataset_calendar_conformance_verification_failed",
        ):
            verify_dataset_calendar_conformance(
                evidence,
                frame.index,
                time_contract=time_contract(),
                timeframe="1d",
                source_kind="SYNTHETIC_FIXTURE",
            )

    def test_protocol_report_and_markdown_bind_conformance_hash(self) -> None:
        frame = synthetic_frame()
        candidate = protocol(frame, config())
        report = build_frozen_evaluation_report(
            candidate,
            frame,
            config(),
            experiment_context=context(),
        )
        conformance_hash = candidate["dataset"]["calendar_conformance"][
            "conformance_hash"
        ]
        self.assertEqual(
            report["dataset_calendar_conformance_hash"],
            conformance_hash,
        )
        self.assertFalse(report["authority"]["paper"])
        self.assertFalse(report["authority"]["live"])
        self.assertFalse(report["authority"]["order"])


if __name__ == "__main__":
    unittest.main()
