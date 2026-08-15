from __future__ import annotations

import argparse
import json
from pathlib import Path

from exchange_terminal import server
from exchange_terminal.services.portfolio_forward import (
    DEFAULT_ACTIVE_CANDIDATE_FILE,
    activate_portfolio_candidate,
)
from exchange_terminal.services.portfolio_experiment import PortfolioExperimentRegistry
from exchange_terminal.services.trusted_clock import attest_utc_clock


def main() -> int:
    parser = argparse.ArgumentParser(description="Explicitly lock one frozen research candidate for forward observation.")
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--robustness", required=True)
    parser.add_argument("--registry", default="")
    parser.add_argument("--experiment-db", default="")
    args = parser.parse_args()

    report_dir = Path(server.RUNTIME_DIR) / "reports"
    registry_path = Path(args.registry).resolve() if args.registry else report_dir / DEFAULT_ACTIVE_CANDIDATE_FILE
    experiment_db = (
        Path(args.experiment_db).resolve()
        if args.experiment_db
        else Path(server.RUNTIME_DIR) / "portfolio_experiments.sqlite3"
    )
    candidate_payload: dict[str, object] = {}
    try:
        decoded = json.loads(Path(args.candidate).read_text(encoding="utf-8"))
        if isinstance(decoded, dict):
            candidate_payload = decoded
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        candidate_payload = {}
    governance = (
        candidate_payload.get("research_governance")
        if isinstance(candidate_payload.get("research_governance"), dict)
        else {}
    )
    experiment_binding = (
        governance.get("experiment_binding")
        if isinstance(governance.get("experiment_binding"), dict)
        else {}
    )
    experiment_id = str(experiment_binding.get("experiment_id") or "")
    experiment_record = PortfolioExperimentRegistry(db_path=experiment_db).get(experiment_id)
    experiment_completion = (
        experiment_record.get("completion")
        if experiment_record.get("ok") is True
        and experiment_record.get("status") == "COMPLETED"
        and (experiment_record.get("registry_audit") or {}).get("status") == "PASS"
        and isinstance(experiment_record.get("completion"), dict)
        else {}
    )
    activation_clock = attest_utc_clock()
    result = activate_portfolio_candidate(
        candidate_path=Path(args.candidate),
        registry_path=registry_path,
        robustness_path=Path(args.robustness),
        activated_at=int(activation_clock.get("attested_now_ms") or 0),
        activation_clock_attestation=activation_clock,
        experiment_completion_receipt=experiment_completion,
    )
    result["experiment_registry"] = {
        "status": experiment_record.get("status"),
        "experiment_id": experiment_id,
        "audit_status": (experiment_record.get("registry_audit") or {}).get("status"),
        "completion_receipt_hash": str(experiment_completion.get("receipt_hash") or ""),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "ACTIVATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
