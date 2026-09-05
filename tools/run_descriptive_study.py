"""Execute all prespecified cost cells; no parameter or outcome selection."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from hakimi_research.dataset_registry import load_snapshot
from hakimi_research.documents import digest, read_document
from hakimi_research.reporting import save_json_report
from hakimi_research.source_layout import DEFAULT_EXPERIMENT_SPEC_PATH


def run(snapshot_path: Path, output: Path, expanded: bool = False):
    snapshot = load_snapshot(snapshot_path)
    template = read_document(DEFAULT_EXPERIMENT_SPEC_PATH)
    template["snapshot_id"] = snapshot.snapshot_id
    cli = Path(__file__).with_name("run_offline_cli.py")
    attempts = []
    cells = [("dual_ma", dict(template["strategy"]["params"]), factor, "base") for factor in (1, 2, 3)]
    if expanded:
        methods = [("cash", {}), ("buy_and_hold", {"target_position_pct": 1}),
                   ("dual_ma", dict(template["strategy"]["params"])),
                   ("rsi", {"window": 14, "oversold": 30, "overbought": 70,
                            "position_pct": 0.25, "stop_loss_pct": 0.03})]
        cells = [(name, params, factor, "base") for name, params in methods for factor in (1, 2, 3)]
        for fast, slow in ((18, 54), (22, 66)):
            cells.append(("dual_ma", {**methods[2][1], "fast_window": fast, "slow_window": slow}, 1, f"adjacent-{fast}-{slow}"))
        for window in (13, 15):
            cells.append(("rsi", {**methods[3][1], "window": window}, 1, f"adjacent-{window}"))
    for strategy_name, params, factor, cell in cells:
        spec = {**template, "name": f"btc-spot-1h-{strategy_name}-{cell}-cost-{factor}x",
                "strategy": {"name": strategy_name, "params": params},
                "fee_rate": template["fee_rate"] * factor,
                "slippage_pct": template["slippage_pct"] * factor}
        if strategy_name == "buy_and_hold":
            spec["execution_policy"] = "BUY_AND_HOLD_SINGLE_ENTRY_MARK_TO_MARKET"
            spec["risk"] = {**template["risk"], "max_position_pct": 1, "min_cash_pct": 0}
        else:
            spec["execution_policy"] = "STANDARD_STRATEGY_RISK"
        spec_path = save_json_report(spec, output / "specs", "spec", artifact_id=digest(spec))
        command = [sys.executable, "-B", str(cli), "research", "--snapshot", str(snapshot_path),
                   "--spec", str(spec_path), "--output-dir", str(output)]
        completed = subprocess.run(command, text=True, capture_output=True, check=False)
        attempt = {"strategy": strategy_name, "cell": cell, "cost_factor": factor, "spec_hash": digest(spec), "spec_path": str(spec_path),
                   "returncode": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr,
                   "network_policy": "PYTHON_SOCKET_AUDIT_DENY"}
        attempts.append(attempt)
        save_json_report(attempt, output / "attempts", "attempt", artifact_id=digest(attempt))
        if completed.returncode != 0:
            raise RuntimeError(completed.stdout + completed.stderr)
    summary = {"schema_version": "descriptive-study-run-v1", "snapshot_id": snapshot.snapshot_id,
               "planned_attempt_count": len(cells), "actual_attempt_count": len(attempts),
               "data_previously_viewed": expanded,
               "prespecified_cost_factors": [1, 2, 3], "attempts": attempts,
               "parameter_selection": False, "confirmation_evaluation": False,
               "live_allowed": False, "order_allowed": False}
    path = save_json_report(summary, output, "study", artifact_id=digest(summary))
    print(json.dumps({"study": str(path), "reports": [json.loads(a["stdout"]) for a in attempts]}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expanded", action="store_true", help="Run all16 cells from the detailed-outline amendment.")
    arguments = parser.parse_args()
    run(arguments.snapshot.resolve(), arguments.output_dir.resolve(), arguments.expanded)
