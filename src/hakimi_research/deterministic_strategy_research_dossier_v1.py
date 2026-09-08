from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from hakimi_research.source_layout import REPOSITORY_ROOT
from hakimi_research.synthetic_strategy_report_bundle import canonical_sha256


CONTRACT_VERSION = "deterministic-strategy-research-dossier-v1"
VERIFIER_VERSION = "deterministic-strategy-research-dossier-verifier-v1"
RECEIPT_VERSION = "deterministic-strategy-research-dossier-receipt-v1"
MANIFEST_VERSION = "deterministic-strategy-research-dossier-manifest-v1"
MATURITY = "SYNTHETIC_RESEARCH_DOSSIER_WITH_ALIGNED_STATISTICAL_REFERENCE_ONLY"
STATUS = "BLOCK"
REFERENCE_ROOT = (
    REPOSITORY_ROOT / "examples" / "deterministic_strategy_research_dossier_v1"
)
REFERENCE_FILE_NAMES = (
    "expected_receipt.json",
    "expected_report.md",
    "fixture_manifest.json",
)
LOCK_PATH = REPOSITORY_ROOT / "requirements.research.lock"

V14_PLAN_SHA256 = "aa3d864f83b990b5a736f9a692c3c41e450f77d4d946b117bc1e66ed1b100a14"
V14_SOURCE_REPORT_SHA256 = (
    "97a628fcf8c621863144ffdca97b0760ed1ad4266bcdc05022f5981902c798da"
)
V14_APPLICABILITY_PROOF_SHA256 = (
    "b3f1226dba58a05b31e2312426e65e45f85a40db353f2affb3aaf075cb8103dc"
)
V14_ALIGNMENT_BINDING_SHA256 = (
    "4d0c4eaaa07bb0745325b49d9eda98fdbc739e91fd2c524defc048e9d2b8bfbc"
)
V14_REPORT_SHA256 = "f8581a41583793f9d62f7a19c43ce5f05e802c9cfc6055bb539b9f59132a70d5"
V14_RECEIPT_SHA256 = (
    "480772c268e528716e1e1c1bedea1ec2ec881f36f2f218beb88a2ea3bec5e75f"
)
STATISTICAL_V3_RECEIPT_SHA256 = (
    "3e917119630fbd5f4335c8b8449ea55d80cc7a3a94194f77428dff24e18ab2a2"
)

_COMPONENT_RELATIVE_PATHS = {
    "family_bundle_json": (
        "examples/deterministic_strategy_family_benchmark_v1/expected_bundle.json"
    ),
    "family_bundle_markdown": (
        "examples/deterministic_strategy_family_benchmark_v1/expected_bundle.md"
    ),
    "family_fixture_manifest": (
        "examples/deterministic_strategy_family_benchmark_v1/fixture_manifest.json"
    ),
    "robustness_receipt_json": (
        "examples/deterministic_strategy_robustness_benchmark_v1/expected_receipt.json"
    ),
    "robustness_receipt_markdown": (
        "examples/deterministic_strategy_robustness_benchmark_v1/expected_receipt.md"
    ),
    "robustness_fixture_manifest": (
        "examples/deterministic_strategy_robustness_benchmark_v1/fixture_manifest.json"
    ),
    "statistical_v3_receipt_json": (
        "examples/deterministic_strategy_statistical_correction_benchmark_v3/expected_receipt.json"
    ),
    "statistical_v3_receipt_markdown": (
        "examples/deterministic_strategy_statistical_correction_benchmark_v3/expected_receipt.md"
    ),
    "statistical_v3_fixture_manifest": (
        "examples/deterministic_strategy_statistical_correction_benchmark_v3/fixture_manifest.json"
    ),
}
SOURCE_RELATIVE_PATHS = (
    "src/hakimi_research/deterministic_strategy_research_dossier_v1.py",
    "outputs/python_quant_bot/examples/build_synthetic_strategy_benchmark_report_v14.py",
    "src/hakimi_research/synthetic_strategy_baseline_lineage_proof.py",
    "src/hakimi_research/deterministic_strategy_family_benchmark.py",
    "src/hakimi_research/deterministic_strategy_robustness_benchmark.py",
    "src/hakimi_research/deterministic_strategy_statistical_correction_benchmark_v3.py",
)
_AUTHORITY = {
    "blind_test_complete": False,
    "formal_inference_authorized": False,
    "live_authorized": False,
    "order_entry_authorized": False,
    "paper_authorized": False,
    "profitability_proven": False,
    "ranking_authorized": False,
}
_DOSSIER_GAPS = {
    "COMPACT_DOSSIER_DOES_NOT_EMBED_V14_REPORT_JSON",
    "ENSEMBLE_STRATEGY_NOT_IMPLEMENTED",
    "FULL_V14_REBUILD_REQUIRED_FOR_SEMANTIC_REVALIDATION",
    "SYNTHETIC_DOSSIER_ONLY",
}
_RESOLVED_GAPS = {"FULL_REPORT_STATISTICAL_SOURCE_ALIGNMENT_NOT_PROVEN"}


class DeterministicStrategyResearchDossierV1Error(ValueError):
    pass


def _fail(message: str) -> None:
    raise DeterministicStrategyResearchDossierV1Error(message)


def _require_exact_json(value: Any, *, path: str = "$") -> None:
    value_type = type(value)
    if value is None or value_type in (str, int, bool):
        return
    if value_type is float:
        if not math.isfinite(value):
            raise TypeError(f"{path} must contain finite native floats")
        return
    if value_type is list:
        for index, item in enumerate(value):
            _require_exact_json(item, path=f"{path}[{index}]")
        return
    if value_type is dict:
        for key, item in value.items():
            if type(key) is not str:
                raise TypeError(f"{path} keys must be exact native strings")
            _require_exact_json(item, path=f"{path}.{key}")
        return
    raise TypeError(f"{path} must use exact native JSON types")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _json_bytes(value: Any) -> bytes:
    _require_exact_json(value)
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _seal(payload: dict[str, Any], field: str) -> dict[str, Any]:
    unsigned = {key: value for key, value in payload.items() if key != field}
    result = copy.deepcopy(unsigned)
    result[field] = canonical_sha256(unsigned)
    return result


def _verify_seal(value: dict[str, Any], field: str, label: str) -> None:
    unsigned = {key: item for key, item in value.items() if key != field}
    if value.get(field) != canonical_sha256(unsigned):
        _fail(f"{label} self-hash mismatch")


def _require_denied_authority(value: Any, label: str) -> None:
    if type(value) is not dict or not value:
        _fail(f"{label} authority missing")
    if any(type(item) is not bool or item is not False for item in value.values()):
        _fail(f"{label} authority escalation")


def _read_components() -> dict[str, Any]:
    raw = {
        label: (REPOSITORY_ROOT / relative_path).read_bytes()
        for label, relative_path in _COMPONENT_RELATIVE_PATHS.items()
    }
    parsed: dict[str, Any] = {
        "family": json.loads(raw["family_bundle_json"]),
        "family_manifest": json.loads(raw["family_fixture_manifest"]),
        "robustness": json.loads(raw["robustness_receipt_json"]),
        "robustness_manifest": json.loads(raw["robustness_fixture_manifest"]),
        "statistical_v3": json.loads(raw["statistical_v3_receipt_json"]),
        "statistical_v3_manifest": json.loads(
            raw["statistical_v3_fixture_manifest"]
        ),
    }
    for label, value in parsed.items():
        _require_exact_json(value, path=f"$.{label}")
    parsed["raw"] = raw
    _verify_components(parsed)
    return parsed


def _verify_components(components: dict[str, Any]) -> None:
    family = components["family"]
    robustness = components["robustness"]
    statistical = components["statistical_v3"]
    family_manifest = components["family_manifest"]
    robustness_manifest = components["robustness_manifest"]
    statistical_manifest = components["statistical_v3_manifest"]
    for label, value, field in (
        ("family", family, "bundle_sha256"),
        ("family manifest", family_manifest, "manifest_sha256"),
        ("robustness", robustness, "receipt_sha256"),
        ("robustness manifest", robustness_manifest, "manifest_sha256"),
        ("statistical v3", statistical, "receipt_sha256"),
        ("statistical v3 manifest", statistical_manifest, "manifest_sha256"),
    ):
        if type(value) is not dict:
            raise TypeError(f"{label} must be an exact native dict")
        _verify_seal(value, field, label)
    for label, value in (
        ("family", family),
        ("robustness", robustness),
        ("statistical v3", statistical),
    ):
        if value.get("status") != STATUS:
            _fail(f"{label} status must remain BLOCK")
        _require_denied_authority(value.get("authority"), label)
    if family.get("runtime_mutations") is not False:
        _fail("family runtime mutations must remain false")
    strategy_ids = family.get("strategy_inventory", {}).get(
        "registered_strategy_ids"
    )
    if strategy_ids != ["bollinger", "dual_ma", "grid", "macd", "momentum", "rsi"]:
        _fail("canonical strategy inventory drifted")
    reports = family.get("strategy_reports")
    if type(reports) is not list or [item.get("strategy_id") for item in reports] != strategy_ids:
        _fail("canonical strategy report membership drifted")
    for report in reports:
        runs = report.get("runs")
        if type(runs) is not dict or set(runs) != {
            "train",
            "validation",
            "frozen_1x",
            "frozen_2x",
            "frozen_3x",
        }:
            _fail("strategy Train/Validation/Frozen coverage drifted")
        if [runs[f"frozen_{value}x"].get("cost_multiplier") for value in (1, 2, 3)] != [1, 2, 3]:
            _fail("strategy Frozen cost-stress coverage drifted")
    if set(family.get("benchmarks", {})) != {"buy_and_hold", "cash"}:
        _fail("canonical benchmark inventory drifted")
    if robustness.get("source_bundle_sha256") != family.get("bundle_sha256"):
        _fail("robustness source bundle mismatch")
    if robustness.get("registered_strategy_ids") != strategy_ids:
        _fail("robustness strategy membership mismatch")
    if statistical.get("receipt_sha256") != STATISTICAL_V3_RECEIPT_SHA256:
        _fail("statistical v3 receipt identity drifted")
    if statistical.get("source_bundle_sha256") != family.get("bundle_sha256"):
        _fail("statistical v3 source bundle mismatch")
    if statistical.get("robustness_bundle_sha256") != robustness.get(
        "robustness_bundle_sha256"
    ):
        _fail("statistical v3 robustness bundle mismatch")
    if (
        statistical.get("full_statistical_reference_applicability_proven") is not True
        or statistical.get("statistical_ledger_alignment_proven") is not True
        or statistical.get("full_report_alignment_proven") is not False
    ):
        _fail("statistical v3 applicability boundary drifted")
    if any(value is not False for value in statistical.get("claims", {}).values()):
        _fail("statistical v3 claim escalation")
    if family_manifest.get("bundle_sha256") != family.get("bundle_sha256"):
        _fail("family manifest binding mismatch")
    if robustness_manifest.get("receipt_sha256") != robustness.get("receipt_sha256"):
        _fail("robustness manifest binding mismatch")
    if statistical_manifest.get("receipt_sha256") != statistical.get("receipt_sha256"):
        _fail("statistical v3 manifest binding mismatch")


def _recorded_v14_receipt() -> dict[str, Any]:
    payload = {
        "schema_version": "synthetic-strategy-benchmark-report-receipt-v14",
        "report_id": "deterministic-synthetic-strategy-benchmark-v14",
        "report_sha256": V14_REPORT_SHA256,
        "plan_sha256": V14_PLAN_SHA256,
        "alignment_binding_sha256": V14_ALIGNMENT_BINDING_SHA256,
        "source_report_v12_sha256": V14_SOURCE_REPORT_SHA256,
        "statistical_applicability_proof_bundle_sha256": (
            V14_APPLICABILITY_PROOF_SHA256
        ),
        "statistical_reference_v3_receipt_sha256": (
            STATISTICAL_V3_RECEIPT_SHA256
        ),
        "source_logical_run_count": 222,
        "statistical_reference_executed_run_count": 179,
        "combined_total_logical_run_count": None,
        "run_accounting_additive": False,
        "composition_executed_run_count": 0,
        "additional_backtest_run_count": 0,
        "legacy_v12_statistical_evidence_superseded": True,
        "statistical_reference_v3_applied": True,
        "bootstrap_v3_replaces_legacy_v1": True,
        "full_report_alignment_proven": True,
        "formal_inference_claimed": False,
        "decision_threshold": None,
        "evidence_state": "OBSERVED_WITH_GAPS",
        "maturity": "SYNTHETIC_FULL_REPORT_STATISTICAL_SOURCE_ALIGNED_ONLY",
        "status": STATUS,
        "authority": {
            key: value for key, value in _AUTHORITY.items() if key != "ranking_authorized"
        },
        "runtime_mutations": False,
    }
    receipt = _seal(payload, "receipt_sha256")
    if receipt["receipt_sha256"] != V14_RECEIPT_SHA256:
        _fail("recorded v14 receipt reconstruction mismatch")
    return receipt


def _combined_gaps(components: dict[str, Any]) -> list[str]:
    gaps = (
        set(components["family"]["gaps"])
        | set(components["robustness"]["gaps"])
        | set(components["statistical_v3"]["remaining_gaps"])
    )
    return sorted((gaps - _RESOLVED_GAPS) | _DOSSIER_GAPS)


def _build_receipt(components: dict[str, Any]) -> dict[str, Any]:
    family = components["family"]
    robustness = components["robustness"]
    statistical = components["statistical_v3"]
    raw = components["raw"]
    strategy_ids = family["strategy_inventory"]["registered_strategy_ids"]
    payload = {
        "schema_version": RECEIPT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "data_source": "PURE_SYNTHETIC_REFERENCE_ARTIFACTS",
        "component_file_sha256": {
            label: _sha256_bytes(value) for label, value in sorted(raw.items())
        },
        "family_bundle_sha256": family["bundle_sha256"],
        "robustness_receipt_sha256": robustness["receipt_sha256"],
        "robustness_bundle_sha256": robustness["robustness_bundle_sha256"],
        "statistical_v3_receipt_sha256": statistical["receipt_sha256"],
        "statistical_v3_bootstrap_bundle_sha256": statistical[
            "bootstrap_bundle_sha256"
        ],
        "statistical_v3_run_ledger_sha256": statistical[
            "run_reproducibility_ledger_sha256"
        ],
        "v14_full_rebuild_receipt": _recorded_v14_receipt(),
        "v14_full_rebuild_semantic_revalidation_required": True,
        "v14_report_json_embedded": False,
        "registered_strategy_ids": list(strategy_ids),
        "registered_strategy_count": len(strategy_ids),
        "observed_family_ids": ["RANGE", "TREND"],
        "gap_family_ids": ["ENSEMBLE"],
        "benchmark_ids": ["buy_and_hold", "cash"],
        "frozen_cost_stress_multipliers": [1, 2, 3],
        "frozen_strategy_observation_count": len(strategy_ids) * 3,
        "full_report_alignment_proven": True,
        "formal_frozen_blind_test_complete": False,
        "formal_inference_claimed": False,
        "profitability_proven": False,
        "ranking_performed": False,
        "decision_threshold": None,
        "status": STATUS,
        "maturity": MATURITY,
        "gaps": _combined_gaps(components),
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    return _seal(payload, "receipt_sha256")


def _decimal(value: Any) -> str:
    if type(value) not in (int, float) or type(value) is bool:
        _fail("report metric must be an exact native number")
    number = float(value)
    if not math.isfinite(number):
        _fail("report metric must be finite")
    return f"{number:.6f}"


def _render_report(receipt: dict[str, Any], family: dict[str, Any]) -> str:
    benchmark_lines = [
        "| Benchmark | Synthetic total return | Max drawdown |",
        "| --- | ---: | ---: |",
    ]
    for benchmark_id in receipt["benchmark_ids"]:
        result = family["benchmarks"][benchmark_id]["result"]
        benchmark_lines.append(
            f"| {benchmark_id} | {_decimal(result['total_return'])} | "
            f"{_decimal(result['max_drawdown'])} |"
        )
    strategy_lines = [
        "| Family | Strategy | Train | Validation | Frozen 1x | Frozen 2x | Frozen 3x |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for report in family["strategy_reports"]:
        runs = report["runs"]
        strategy_lines.append(
            f"| {report['family_id']} | {report['strategy_id']} | "
            f"{_decimal(runs['train']['result']['total_return'])} | "
            f"{_decimal(runs['validation']['result']['total_return'])} | "
            f"{_decimal(runs['frozen_1x']['result']['total_return'])} | "
            f"{_decimal(runs['frozen_2x']['result']['total_return'])} | "
            f"{_decimal(runs['frozen_3x']['result']['total_return'])} |"
        )
    lines = [
        "# Deterministic Synthetic Strategy Research Dossier v1",
        "",
        "All numeric observations below come from fixed synthetic fixtures. They are not profitability evidence or trading permission.",
        "",
        "## SOURCE",
        f"- Family bundle: `{receipt['family_bundle_sha256']}`",
        f"- Robustness receipt: `{receipt['robustness_receipt_sha256']}`",
        f"- Statistical v3 receipt: `{receipt['statistical_v3_receipt_sha256']}`",
        f"- V14 full-rebuild receipt: `{receipt['v14_full_rebuild_receipt']['receipt_sha256']}`",
        "- Protocol: Train -> Purge -> Validation -> Embargo -> Frozen.",
        "- Frozen cost stress multiplies fee and slippage together at 1x, 2x, and 3x.",
        "- Run counts from overlapping artifacts are not added.",
        "",
        "### Fixed synthetic benchmarks",
        *benchmark_lines,
        "",
        "### Registered strategy synthetic total-return observations",
        *strategy_lines,
        "",
        "## GAP",
        *[f"- `{gap}`" for gap in receipt["gaps"]],
        "",
        "## MATURITY",
        f"- Status: `{receipt['status']}`",
        f"- Maturity: `{receipt['maturity']}`",
        "- RANGE and TREND families: observed on fixed synthetic fixtures.",
        "- ENSEMBLE family: GAP; no registered implementation.",
        "- Full-report statistical source alignment: TRUE for the recorded synthetic v14 rebuild only.",
        "- Full v14 rebuild is required for semantic revalidation.",
        "",
        "## PERMISSION",
        "- Profitability proven: `false`",
        "- Formal inference authorized: `false`",
        "- Ranking authorized: `false`",
        "- Paper authorized: `false`",
        "- Live authorized: `false`",
        "- Order entry authorized: `false`",
    ]
    markdown = "\n".join(lines) + "\n"
    if "READY" in markdown or "Profitability proven: `true`" in markdown:
        _fail("dossier renderer contains an authority-escalating token")
    return markdown


def build_deterministic_strategy_research_dossier_material_v1() -> dict[str, Any]:
    components = _read_components()
    receipt = _build_receipt(components)
    receipt_bytes = _json_bytes(receipt)
    report_bytes = _render_report(receipt, components["family"]).encode("utf-8")
    source_files = {
        path: _sha256_bytes((REPOSITORY_ROOT / path).read_bytes())
        for path in SOURCE_RELATIVE_PATHS
    }
    component_files = receipt["component_file_sha256"]
    manifest_core = {
        "contract_version": MANIFEST_VERSION,
        "receipt_schema_version": receipt["schema_version"],
        "receipt_sha256": receipt["receipt_sha256"],
        "family_bundle_sha256": receipt["family_bundle_sha256"],
        "robustness_receipt_sha256": receipt["robustness_receipt_sha256"],
        "statistical_v3_receipt_sha256": receipt[
            "statistical_v3_receipt_sha256"
        ],
        "v14_report_sha256": V14_REPORT_SHA256,
        "v14_receipt_sha256": V14_RECEIPT_SHA256,
        "v14_alignment_binding_sha256": V14_ALIGNMENT_BINDING_SHA256,
        "full_report_alignment_proven": True,
        "full_rebuild_required_for_semantic_revalidation": True,
        "source_files": source_files,
        "source_file_count": len(source_files),
        "component_files": copy.deepcopy(component_files),
        "component_file_count": len(component_files),
        "dependency_lock": {
            "name": LOCK_PATH.name,
            "sha256": _sha256_bytes(LOCK_PATH.read_bytes()),
            "fully_pinned": True,
        },
        "expected_receipt_file_sha256": _sha256_bytes(receipt_bytes),
        "expected_report_file_sha256": _sha256_bytes(report_bytes),
        "status": STATUS,
        "maturity": MATURITY,
        "authority": copy.deepcopy(_AUTHORITY),
        "runtime_mutations": False,
    }
    manifest = _seal(manifest_core, "manifest_sha256")
    return {
        "receipt": receipt,
        "manifest": manifest,
        "files": {
            "expected_receipt.json": receipt_bytes.decode("utf-8"),
            "expected_report.md": report_bytes.decode("utf-8"),
            "fixture_manifest.json": _json_bytes(manifest).decode("utf-8"),
        },
    }


def verify_deterministic_strategy_research_dossier_material_v1(
    material: dict[str, Any],
) -> dict[str, Any]:
    if type(material) is not dict:
        raise TypeError("material must be an exact native dict")
    _require_exact_json(material)
    if set(material) != {"receipt", "manifest", "files"}:
        _fail("dossier material shape mismatch")
    expected = build_deterministic_strategy_research_dossier_material_v1()
    if material != expected:
        _fail("dossier material does not match deterministic current sources")
    return {
        "status": "PASS",
        "contract_version": CONTRACT_VERSION,
        "receipt_sha256": material["receipt"]["receipt_sha256"],
        "manifest_sha256": material["manifest"]["manifest_sha256"],
        "full_report_alignment_proven": True,
        "full_rebuild_required_for_semantic_revalidation": True,
        "runtime_mutations": False,
        "authority": copy.deepcopy(_AUTHORITY),
    }


def verify_deterministic_strategy_research_dossier_reference_v1(
    reference_root: str | None = None,
) -> dict[str, Any]:
    root = REFERENCE_ROOT if reference_root is None else Path(reference_root)
    expected = build_deterministic_strategy_research_dossier_material_v1()
    verify_deterministic_strategy_research_dossier_material_v1(expected)
    if not root.is_dir():
        _fail("dossier reference root missing")
    actual_names = {path.name for path in root.iterdir() if path.is_file()}
    checks = {
        "reference_file_set": actual_names == set(REFERENCE_FILE_NAMES),
        "lf_only": all(
            b"\r" not in (root / name).read_bytes()
            for name in REFERENCE_FILE_NAMES
            if (root / name).is_file()
        ),
        "expected_bytes_exact": all(
            (root / name).is_file()
            and (root / name).read_bytes()
            == expected["files"][name].encode("utf-8")
            for name in REFERENCE_FILE_NAMES
        ),
    }
    failed = [name for name, passed in checks.items() if passed is not True]
    if failed:
        _fail(f"dossier reference verification failed:{failed}")
    return {
        "status": "PASS",
        "contract_version": VERIFIER_VERSION,
        "receipt_sha256": expected["receipt"]["receipt_sha256"],
        "manifest_sha256": expected["manifest"]["manifest_sha256"],
        "checks": checks,
        "full_report_alignment_proven": True,
        "full_rebuild_required_for_semantic_revalidation": True,
        "runtime_mutations": False,
        "authority": copy.deepcopy(_AUTHORITY),
    }


__all__ = [
    "CONTRACT_VERSION",
    "REFERENCE_FILE_NAMES",
    "REFERENCE_ROOT",
    "build_deterministic_strategy_research_dossier_material_v1",
    "verify_deterministic_strategy_research_dossier_material_v1",
    "verify_deterministic_strategy_research_dossier_reference_v1",
]
