from __future__ import annotations

import argparse
import json
from pathlib import Path

from hakimi_research.product_capabilities import (
    build_product_capability_catalog,
    product_capability_status_for_cli_command,
    supported_cli_commands,
)
from hakimi_research.source_layout import (
    LEGACY_PROJECT_ROOT,
    REPOSITORY_ROOT,
)


from hakimi_research.backtest import (
    BacktestEngine,
    build_backtest_reproducibility,
)
from hakimi_research.config import BotConfig  # noqa: E402
from hakimi_research.data import build_data_provider
from hakimi_research.experiment_manifest import (  # noqa: E402
    build_local_experiment_context,
    canonical_payload_hash,
)
from hakimi_research.experiment_provenance_consumer_adapter_v1 import (  # noqa: E402
    build_cli_report_provenance_bundle_candidate,
    verify_cli_report_provenance_bundle_candidate,
)
from hakimi_research.logging_setup import setup_logging  # noqa: E402
from hakimi_research.reporting import (  # noqa: E402
    RESEARCH_JSON_REPORT_SCHEMA_VERSION,
    build_json_report_bundle_v2,
    save_json_report_bundle_v2,
    verify_json_report_bundle_v2,
)
from hakimi_research.risk import RiskManager
from hakimi_research.strategies.templates import build_strategy


LEGACY_PAPER_ENABLED = False
LEGACY_OPTIMIZE_ENABLED = False
DEFAULT_CONFIG_PATH = LEGACY_PROJECT_ROOT / "config.example.json"
REPORT_DIR = LEGACY_PROJECT_ROOT / "runtime" / "reports"


SUMMARY_FIELDS = [
    "total_return",
    "annualized_return",
    "max_drawdown",
    "win_rate",
    "sharpe_ratio",
    "trades",
    "final_equity",
]


def load_stack(config_path: str | Path):
    config = BotConfig.from_file(config_path)
    setup_logging(config.logging.log_dir, config.logging.level)
    provider = build_data_provider(config)
    strategy = build_strategy(config.strategy.name, config.strategy.params)
    risk = RiskManager(config.risk)
    return config, provider, strategy, risk


def command_backtest(args: argparse.Namespace) -> None:
    config, provider, strategy, risk = load_stack(args.config)
    data = provider.get_history(config.symbol, config.timeframe, config.data.history_limit)
    experiment_context = build_local_experiment_context(REPOSITORY_ROOT)
    expected_reproducibility = build_backtest_reproducibility(
        data,
        config,
        strategy,
        experiment_context=experiment_context,
        max_volume_participation_rate=None,
    )
    engine = BacktestEngine(
        config=config,
        strategy=strategy,
        risk_manager=risk,
        experiment_context=experiment_context,
    )
    report = engine.run(data)
    report_payload = report.to_dict()
    result_payload = {
        key: value
        for key, value in report_payload.items()
        if key != "experiment_manifest"
    }
    identity_hash = canonical_payload_hash({
        "source_run_hash": expected_reproducibility["run_hash"],
        "result_hash": canonical_payload_hash(result_payload),
    })
    experiment_id = f"hexp-{identity_hash[:20]}"
    expected_context = {
        **experiment_context,
        "random_seed": expected_reproducibility["random_seed"],
    }
    expected_manifest_identity = {
        "experiment_id": experiment_id,
        "strategy_name": strategy.name,
        "strategy_version": strategy.version,
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "fee_rate": config.execution.fee_rate,
        "slippage_pct": config.execution.slippage_pct,
        "evaluation_role": "UNCLASSIFIED",
        "evaluation_protocol_hash": "",
        "evaluation_protocol_verified": False,
    }
    prefix = f"backtest_{config.strategy.name}_{config.symbol}"
    artifact_identity = {
        "artifact_id": experiment_id,
        "prefix": prefix,
        "report_schema_version": RESEARCH_JSON_REPORT_SCHEMA_VERSION,
        "filename": f"{prefix}_{experiment_id}.json",
    }
    provenance_receipt = build_cli_report_provenance_bundle_candidate(
        report_payload,
        expected_reproducibility=expected_reproducibility,
        expected_context=expected_context,
        expected_manifest_identity=expected_manifest_identity,
        expected_artifact_identity=artifact_identity,
    )
    if not verify_cli_report_provenance_bundle_candidate(
        provenance_receipt,
        report_payload,
        expected_reproducibility=expected_reproducibility,
        expected_context=expected_context,
        expected_manifest_identity=expected_manifest_identity,
        expected_artifact_identity=artifact_identity,
    ):
        raise RuntimeError("CLI report provenance verification failed.")
    bundle = build_json_report_bundle_v2(
        report_payload,
        provenance_receipt,
        artifact_identity=artifact_identity,
    )
    if not verify_json_report_bundle_v2(bundle):
        raise RuntimeError("CLI report bundle verification failed.")
    output = save_json_report_bundle_v2(bundle, str(REPORT_DIR))
    summary = {field: getattr(report, field) for field in SUMMARY_FIELDS}
    summary.update({
        "strategy": config.strategy.name,
        "symbol": config.symbol,
        "timeframe": config.timeframe,
        "data_rows": len(data),
        "experiment_id": experiment_id,
        "reproducibility_status": report.experiment_manifest.get("status"),
        "ranking_input_allowed": report.experiment_manifest.get("ranking_gate", {}).get(
            "input_allowed", False
        ),
        "full_report": str(output),
    })
    print(json.dumps(summary, indent=2, ensure_ascii=False))


def command_frozen_benchmark(_args: argparse.Namespace) -> None:
    from hakimi_research.deterministic_frozen_benchmark import (
        verify_deterministic_frozen_benchmark_reference,
    )

    receipt = verify_deterministic_frozen_benchmark_reference()
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))


def command_strategy_family_benchmark(_args: argparse.Namespace) -> None:
    from hakimi_research.deterministic_strategy_family_benchmark import (
        verify_deterministic_strategy_family_reference,
    )

    receipt = verify_deterministic_strategy_family_reference()
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))


def command_strategy_robustness_benchmark(_args: argparse.Namespace) -> None:
    from hakimi_research.deterministic_strategy_robustness_benchmark import (
        verify_deterministic_strategy_robustness_reference,
    )

    receipt = verify_deterministic_strategy_robustness_reference()
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))


def command_strategy_statistical_correction_benchmark(
    args: argparse.Namespace,
) -> None:
    version = getattr(args, "statistical_reference_version", "v1")
    if version == "v2":
        from hakimi_research.deterministic_strategy_statistical_correction_benchmark_v2 import (
            verify_deterministic_strategy_statistical_correction_reference_v2,
        )

        receipt = verify_deterministic_strategy_statistical_correction_reference_v2()
    else:
        from hakimi_research.deterministic_strategy_statistical_correction_benchmark import (
            verify_deterministic_strategy_statistical_correction_reference,
        )

        receipt = verify_deterministic_strategy_statistical_correction_reference()
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))


def command_strategy_research_dossier(_args: argparse.Namespace) -> None:
    from hakimi_research.deterministic_strategy_research_dossier_v1 import (
        verify_deterministic_strategy_research_dossier_reference_v1,
    )

    receipt = verify_deterministic_strategy_research_dossier_reference_v1()
    print(json.dumps(receipt, indent=2, sort_keys=True, ensure_ascii=False))


def command_paper(args: argparse.Namespace) -> None:
    if product_capability_status_for_cli_command("paper") != "Archived":
        raise RuntimeError("Product capability catalog rejected the paper boundary.")
    raise RuntimeError(
        "Legacy paper path is archived and permanently disabled in the research-only product."
    )


def command_optimize(args: argparse.Namespace) -> None:
    if product_capability_status_for_cli_command("optimize") != "Archived":
        raise RuntimeError("Product capability catalog rejected the optimize boundary.")
    raise RuntimeError(
        "Legacy optimize path is archived and permanently disabled in the research-only product."
    )


def command_capabilities(_args: argparse.Namespace) -> None:
    print(json.dumps(
        build_product_capability_catalog().to_dict(),
        indent=2,
        ensure_ascii=False,
    ))


def command_list_strategies(_args: argparse.Namespace) -> None:
    from hakimi_research.strategies.templates import STRATEGY_REGISTRY

    print("Available strategies:")
    for name in sorted(STRATEGY_REGISTRY):
        print(f"- {name}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Hakimi research-only strategy platform")
    parser.add_argument("command", choices=supported_cli_commands())
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument(
        "--statistical-reference-version",
        choices=("v1", "v2"),
        default="v1",
        help="Explicit statistical-correction reference version; v1 remains default.",
    )
    args = parser.parse_args(argv)

    try:
        if args.command == "backtest":
            command_backtest(args)
        elif args.command == "frozen-benchmark":
            command_frozen_benchmark(args)
        elif args.command == "strategy-family-benchmark":
            command_strategy_family_benchmark(args)
        elif args.command == "strategy-robustness-benchmark":
            command_strategy_robustness_benchmark(args)
        elif args.command == "strategy-statistical-correction-benchmark":
            command_strategy_statistical_correction_benchmark(args)
        elif args.command == "strategy-research-dossier":
            command_strategy_research_dossier(args)
        elif args.command == "capabilities":
            command_capabilities(args)
        elif args.command == "list-strategies":
            command_list_strategies(args)
        else:
            raise RuntimeError(f"Unsupported command: {args.command}")
    except RuntimeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2, ensure_ascii=False))
        raise SystemExit(1)
