from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
PROJECT_ROOT = REPOSITORY_ROOT / "outputs" / "python_quant_bot"
for path in (str(SOURCE_ROOT), str(PROJECT_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)

from exchange_terminal.application.deterministic_strategy_research_dossier_v2 import (  # noqa: E402
    REFERENCE_FILE_NAMES,
    REFERENCE_ROOT,
    build_deterministic_strategy_research_dossier_material_v2,
    verify_deterministic_strategy_research_dossier_material_v2,
)
from exchange_terminal.application.synthetic_strategy_benchmark_controls_v1 import (  # noqa: E402
    build_synthetic_strategy_benchmark_controls_v1,
)
from exchange_terminal.application.synthetic_strategy_report_bundle_v1 import (  # noqa: E402
    build_synthetic_strategy_report_bundle_v1,
)


def plan_deterministic_strategy_research_dossier_v2() -> dict[str, Any]:
    return {
        "schema_version": "deterministic-strategy-research-dossier-v2-build-plan",
        "planned_source_run_count": 32,
        "planned_additional_control_run_count": 18,
        "planned_total_logical_run_count": 50,
        "requires_explicit_execute": True,
        "writes_reference_by_default": False,
        "candidate_only": True,
        "current_activation": False,
        "full_v14_rebuild_planned": False,
        "runtime_mutations": False,
    }


def build_deterministic_strategy_research_dossier_v2(
    *, execute: bool = False
) -> dict[str, Any]:
    if type(execute) is not bool:
        raise TypeError("execute must be an exact native bool")
    if execute is False:
        return plan_deterministic_strategy_research_dossier_v2()
    source = build_synthetic_strategy_report_bundle_v1(execute=True)
    controls = build_synthetic_strategy_benchmark_controls_v1(source, execute=True)
    material = build_deterministic_strategy_research_dossier_material_v2(controls)
    verification = verify_deterministic_strategy_research_dossier_material_v2(
        material, controls
    )
    return {
        "material": material,
        "benchmark_controls_bundle": controls,
        "verification": verification,
    }


def write_deterministic_strategy_research_dossier_reference_v2(
    material: dict[str, Any],
) -> None:
    if type(material) is not dict or set(material) != {"receipt", "manifest", "files"}:
        raise TypeError("material shape invalid")
    files = material.get("files")
    if type(files) is not dict or set(files) != set(REFERENCE_FILE_NAMES):
        raise ValueError("reference file set invalid")
    REFERENCE_ROOT.mkdir(parents=True, exist_ok=True)
    unexpected = {
        path.name for path in REFERENCE_ROOT.iterdir() if path.is_file()
    } - set(REFERENCE_FILE_NAMES)
    if unexpected:
        raise ValueError(f"unexpected reference files:{sorted(unexpected)}")
    for name in REFERENCE_FILE_NAMES:
        value = files[name]
        if type(value) is not str:
            raise TypeError(f"reference file must be text:{name}")
        temporary = REFERENCE_ROOT / f"{name}.tmp"
        temporary.write_bytes(value.encode("utf-8"))
        temporary.replace(REFERENCE_ROOT / name)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the non-current deterministic strategy dossier v2 candidate."
    )
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--write-reference", action="store_true")
    args = parser.parse_args()
    if args.write_reference and not args.execute:
        parser.error("--write-reference requires --execute")
    result = build_deterministic_strategy_research_dossier_v2(
        execute=args.execute
    )
    if args.execute:
        if args.write_reference:
            write_deterministic_strategy_research_dossier_reference_v2(
                result["material"]
            )
        output = {
            **result["verification"],
            "reference_written": bool(args.write_reference),
            "benchmark_control_bundle_sha256": result[
                "benchmark_controls_bundle"
            ]["bundle_sha256"],
        }
    else:
        output = result
    print(json.dumps(output, allow_nan=False, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
