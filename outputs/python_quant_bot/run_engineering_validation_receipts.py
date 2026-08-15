from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time

from exchange_terminal.services.internal_backtest_readiness import (
    ENGINEERING_EVIDENCE_TYPES,
    REUSABLE_ENGINEERING_CHECKS,
    build_expected_engineering_actions,
)
from exchange_terminal.services.validation_receipts import (
    create_validation_receipt,
    file_sha256,
    load_validation_receipt,
    prune_receipts,
    receipt_path,
    result_from_process,
    utc_now,
    verify_validation_receipt,
    write_validation_receipt,
)
from run_lean_validation import isolated_environment


ENGINEERING_EVIDENCE_SCHEMA = "hakimi-engineering-evidence-v2"


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def _receipt_row(
    *,
    check_id: str,
    action: dict[str, object],
    receipt: dict[str, object],
    artifact_path: Path,
    execution: str,
) -> dict[str, object]:
    predicate = receipt.get("predicate") if isinstance(receipt.get("predicate"), dict) else {}
    result = predicate.get("result") if isinstance(predicate.get("result"), dict) else {}
    verification = verify_validation_receipt(receipt, expected_action=action)
    return {
        "id": check_id,
        "status": "PASS" if verification.get("status") == "PASS" else "BLOCK",
        "execution": execution,
        "command": list(action.get("argv") or []),
        "evidence_type": ENGINEERING_EVIDENCE_TYPES[check_id],
        "result": dict(result),
        "artifact_path": str(artifact_path.resolve()),
        "artifact_sha256": file_sha256(artifact_path),
        "validation_receipt": receipt,
        "reuse_allowed": True,
        "receipt_verification": verification,
    }


def run_checks(
    check_ids: list[str],
    *,
    output_dir: Path,
    fresh: bool,
) -> dict[str, object]:
    actions = build_expected_engineering_actions()
    receipts_dir = output_dir.resolve() / "receipts"
    rows: list[dict[str, object]] = []
    executed = 0
    reused = 0
    with tempfile.TemporaryDirectory(prefix="hakimi-engineering-receipts-") as directory:
        env = isolated_environment(Path(directory))
        for check_id in check_ids:
            action = actions[check_id]
            artifact = receipt_path(receipts_dir, action)
            receipt: dict[str, object] | None = None
            if artifact.is_file() and not fresh:
                try:
                    candidate = load_validation_receipt(artifact)
                    if verify_validation_receipt(candidate, expected_action=action).get("status") == "PASS":
                        receipt = candidate
                except (OSError, ValueError, json.JSONDecodeError):
                    receipt = None
            if receipt is not None:
                reused += 1
                rows.append(_receipt_row(
                    check_id=check_id,
                    action=action,
                    receipt=receipt,
                    artifact_path=artifact,
                    execution="REUSED",
                ))
                continue

            started_at = utc_now()
            started = time.perf_counter()
            completed = subprocess.run(
                list(action.get("argv") or []),
                cwd=Path(str(action.get("cwd") or "")),
                env=env,
                check=False,
                capture_output=True,
                text=True,
                errors="replace",
            )
            if completed.stdout:
                print(completed.stdout, end="" if completed.stdout.endswith("\n") else "\n")
            if completed.stderr:
                print(completed.stderr, end="" if completed.stderr.endswith("\n") else "\n", file=sys.stderr)
            result = result_from_process(
                action=action,
                exit_code=int(completed.returncode),
                stdout=str(completed.stdout or ""),
                stderr=str(completed.stderr or ""),
                duration_sec=time.perf_counter() - started,
            )
            receipt = create_validation_receipt(
                action=action,
                result=result,
                started_at=started_at,
                finished_at=utc_now(),
            )
            verification = verify_validation_receipt(receipt, expected_action=action)
            if verification.get("status") != "PASS":
                return {
                    "schema_version": ENGINEERING_EVIDENCE_SCHEMA,
                    "status": "BLOCK",
                    "failed_check": check_id,
                    "blockers": list(verification.get("blockers") or []),
                    "engineering_checks": rows,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            write_validation_receipt(artifact, receipt)
            prune_receipts(receipts_dir, check_id)
            executed += 1
            rows.append(_receipt_row(
                check_id=check_id,
                action=action,
                receipt=receipt,
                artifact_path=artifact,
                execution="EXECUTED",
            ))
            if completed.returncode != 0:
                break

    passed = len(rows) == len(check_ids) and all(row.get("status") == "PASS" for row in rows)
    return {
        "schema_version": ENGINEERING_EVIDENCE_SCHEMA,
        "status": "PASS" if passed else "BLOCK",
        "generated_at": utc_now(),
        "requested_checks": list(check_ids),
        "executed_check_count": executed,
        "reused_check_count": reused,
        "engineering_checks": rows,
        "runtime_bound_checks_required": ["browser_interaction", "read_only_mutation_probe"],
        "runtime_bound_evidence_reuse_allowed": False,
        "scope": "ENGINEERING_RECEIPTS_ONLY_NOT_READINESS",
        "formal_run_allowed": False,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create or reuse exact-match deterministic engineering receipts. Runtime/browser probes are never included."
    )
    parser.add_argument("--checks", nargs="+", required=True, choices=REUSABLE_ENGINEERING_CHECKS)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--evidence-output", required=True)
    parser.add_argument("--fresh", action="store_true")
    parser.add_argument(
        "--include-full-suite",
        action="store_true",
        help="Required acknowledgement before executing or reusing python_full_suite.",
    )
    args = parser.parse_args()
    check_ids = list(dict.fromkeys(args.checks))
    if "python_full_suite" in check_ids and not args.include_full_suite:
        raise SystemExit("python_full_suite requires explicit --include-full-suite")
    output_dir = Path(args.output_dir).resolve()
    evidence_output = Path(args.evidence_output).resolve()
    try:
        evidence_output.relative_to(output_dir)
    except ValueError as exc:
        raise SystemExit("engineering evidence output must remain inside output-dir") from exc
    payload = run_checks(check_ids, output_dir=output_dir, fresh=args.fresh)
    _write_json_atomic(evidence_output, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())

