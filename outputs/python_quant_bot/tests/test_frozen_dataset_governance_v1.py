from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
BOT_ROOT = REPO_ROOT / "outputs" / "python_quant_bot"
for candidate in (str(SRC_ROOT), str(BOT_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from hakimi_research.dataset_governance import (  # noqa: E402
    SCHEMA_VERSION,
    bind_dataset_governance,
    canonical_dataset_governance_hash,
    verify_dataset_governance,
)
from hakimi_research.experiment_manifest import canonical_payload_hash  # noqa: E402
from hakimi_research.frozen_evaluation import (  # noqa: E402
    build_frozen_evaluation_protocol,
    verify_frozen_evaluation_protocol,
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
    endswith = _fail
    replace = _fail
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


def binding_facts() -> dict[str, Any]:
    frame = synthetic_frame()
    payload = {
        "hash_scope": "FULL_OHLCV_CANONICAL_DECIMAL_TEXT_V1",
        "columns": ["timestamp", "open", "high", "low", "close", "volume"],
        "rows": [
            [
                timestamp.isoformat(),
                *(format(float(row[column]), ".17g") for column in ("open", "high", "low", "close", "volume")),
            ]
            for timestamp, row in frame.iterrows()
        ],
    }
    return {
        "dataset_hash": canonical_payload_hash(payload),
        "market": "stock",
        "symbol": "SYNTH-001",
        "timeframe": "1d",
        "row_count": len(frame),
        "start_time": frame.index[0].isoformat(),
        "end_time": frame.index[-1].isoformat(),
        "dataset_timezone": "UTC",
    }


class FrozenDatasetGovernanceV1Tests(unittest.TestCase):
    def test_canonical_source_is_outside_outputs_and_versioned(self) -> None:
        source = SRC_ROOT / "hakimi_research" / "dataset_governance.py"
        self.assertTrue(source.is_file())
        self.assertNotIn("outputs", source.relative_to(REPO_ROOT).parts)
        self.assertEqual(SCHEMA_VERSION, "dataset-governance-v1")

    def test_v1_v9_reference_remains_historical_and_unmodified(self) -> None:
        old_root = REPO_ROOT / "examples" / "deterministic_frozen_benchmark_v1"
        manifest = json.loads(
            (old_root / "fixture_manifest.json").read_text(encoding="utf-8")
        )
        report = json.loads(
            (old_root / "expected_report.json").read_text(encoding="utf-8")
        )
        self.assertEqual(report["schema_version"], "frozen-evaluation-report-v9")
        self.assertEqual(
            manifest["protocol_hash"],
            "69de4ce1fbb258a12db821f355cf7c82c98453f22c5f8f4a3d2b8ce82e00ee85",
        )
        self.assertEqual(
            manifest["report_hash"],
            "d850be4b62ac7252747ccb362096160c8fb82c496d520acdb9e8b90b944c5e76",
        )
        self.assertEqual(
            manifest["manifest_sha256"],
            "bc364728a79d8fa84c8ad77c87bf391b99edd66036219e08faa2f2682fe42542",
        )

    def test_bound_governance_is_exact_and_self_verifying(self) -> None:
        facts = binding_facts()
        bound = bind_dataset_governance(dataset_governance(), **facts)
        self.assertTrue(verify_dataset_governance(bound, **facts))
        self.assertEqual(bound["dataset_binding"]["dataset_hash"], facts["dataset_hash"])
        self.assertEqual(bound["time"]["timezone"], facts["dataset_timezone"])
        self.assertEqual(
            bound["governance_hash"],
            canonical_dataset_governance_hash(
                {key: value for key, value in bound.items() if key != "governance_hash"}
            ),
        )

    def test_frozen_protocol_identity_changes_with_governance(self) -> None:
        first = protocol()
        changed = dataset_governance()
        changed["source"]["provider_id"] = "different-deterministic-fixture"
        second = build_frozen_evaluation_protocol(
            synthetic_frame(),
            config(),
            dataset_governance=changed,
            train_rows=40,
            purge_rows=4,
            validation_rows=40,
            embargo_rows=4,
            frozen_test_rows=40,
            random_seed=17,
            experiment_context=context(),
        )
        self.assertNotEqual(first["protocol_hash"], second["protocol_hash"])
        self.assertNotEqual(
            first["dataset"]["governance"]["governance_hash"],
            second["dataset"]["governance"]["governance_hash"],
        )
        self.assertTrue(verify_frozen_evaluation_protocol(first, synthetic_frame(), config(), experiment_context=context()))
        self.assertTrue(verify_frozen_evaluation_protocol(second, synthetic_frame(), config(), experiment_context=context()))

    def test_missing_or_conflicting_governance_fails_before_protocol(self) -> None:
        kwargs = {
            "data": synthetic_frame(),
            "config": config(),
            "train_rows": 40,
            "purge_rows": 4,
            "validation_rows": 40,
            "embargo_rows": 4,
            "frozen_test_rows": 40,
            "random_seed": 17,
        }
        with self.assertRaises(TypeError):
            build_frozen_evaluation_protocol(**kwargs, experiment_context=context())
        conflicting = dataset_governance()
        conflicting["time"]["timezone"] = "Asia/Shanghai"
        with self.assertRaisesRegex(ValueError, "dataset_governance_time_timezone"):
            build_frozen_evaluation_protocol(
                **kwargs,
                dataset_governance=conflicting,
                experiment_context=context(),
            )

    def test_tampered_governance_or_extra_authority_alias_fails_closed(self) -> None:
        candidate = protocol()
        tampered = deepcopy(candidate)
        tampered["dataset"]["governance"]["population"]["policy"] = "CURRENT_SURVIVORS_ONLY"
        core = {
            key: value
            for key, value in tampered.items()
            if key not in {"protocol_id", "protocol_hash"}
        }
        tampered["protocol_hash"] = canonical_payload_hash(core)
        tampered["protocol_id"] = f"hfep-{tampered['protocol_hash'][:20]}"
        with self.assertRaisesRegex(ValueError, "dataset_governance_"):
            verify_frozen_evaluation_protocol(tampered, synthetic_frame(), config(), experiment_context=context())

        declaration = dataset_governance()
        declaration["paper_authorized"] = False
        with self.assertRaisesRegex(ValueError, "dataset_governance_declaration_fields"):
            bind_dataset_governance(declaration, **binding_facts())

    def test_non_native_identity_values_never_invoke_subclass_methods(self) -> None:
        HostileStr.calls = HostileDict.calls = 0
        declaration = dataset_governance()
        declaration["source"]["provider_id"] = HostileStr("deterministic-test-fixture")
        with self.assertRaisesRegex(ValueError, "dataset_governance_"):
            bind_dataset_governance(declaration, **binding_facts())
        with self.assertRaisesRegex(ValueError, "dataset_governance_"):
            bind_dataset_governance(
                HostileDict(dataset_governance()),
                **binding_facts(),
            )
        self.assertEqual((HostileStr.calls, HostileDict.calls), (0, 0))

    def test_protocol_and_report_expose_governance_without_authority(self) -> None:
        candidate = protocol()
        governance = candidate["dataset"]["governance"]
        self.assertEqual(governance["schema_version"], SCHEMA_VERSION)
        self.assertNotIn("paper_authorized", governance)
        self.assertNotIn("live_order_allowed", governance)
        self.assertEqual(candidate["authority"]["paper"], False)
        self.assertEqual(candidate["authority"]["live"], False)
        self.assertEqual(candidate["authority"]["order"], False)


if __name__ == "__main__":
    unittest.main()
