from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
from typing import Any, Callable, Iterator
import uuid

from .backtest_engine import EXECUTION_MODEL_VERSION
from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable
from .strategy_data_admission import verify_strategy_data_admission


AuditWriter = Callable[[dict[str, Any]], Any]


class StrategyPipeline:
    """Persistent research-to-paper release gate. Live release is intentionally absent."""

    STAGE_ORDER = ["definition", "backtest", "doctor", "paper_authorization", "paper_run", "audit_review"]
    VALIDATED_PAPER_PROFILE = {
        "direction_mode": "LONG_ONLY",
        "risk_source": "MANUAL",
        "risk_value_mode": "PCT",
        "trailing_take_enabled": False,
        "trailing_stop_enabled": False,
        "reduce_only": False,
        "order_type": "CURRENT",
        "margin_mode": "CROSS",
    }

    def __init__(
        self,
        *,
        db_path: Path,
        now_ms: Callable[[], int],
        audit_writer: AuditWriter | None = None,
        minimum_forward_duration_ms: int = 7 * 24 * 60 * 60 * 1000,
        minimum_forward_closed_trades: int = 20,
        maximum_forward_drawdown_pct: float = 12.0,
        read_only: bool = False,
    ) -> None:
        self.db_path = db_path
        self.now_ms = now_ms
        self.audit_writer = audit_writer
        self.minimum_forward_duration_ms = max(int(minimum_forward_duration_ms), 0)
        self.minimum_forward_closed_trades = max(int(minimum_forward_closed_trades), 1)
        self.maximum_forward_drawdown_pct = max(float(maximum_forward_drawdown_pct), 0.1)
        self.read_only = bool(read_only)
        self._lock = threading.RLock()
        if not self.read_only:
            self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = connect_runtime_sqlite(self.db_path, read_only=self.read_only)
        connection.row_factory = sqlite3.Row
        if not self.read_only:
            connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=15000")
        try:
            yield connection
            if not self.read_only:
                connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS strategy_runs (
                    run_id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_strategy_runs_latest
                    ON strategy_runs(symbol, strategy_id, updated_at DESC);
                CREATE TABLE IF NOT EXISTS strategy_versions (
                    version_id TEXT PRIMARY KEY,
                    strategy_id TEXT NOT NULL,
                    fingerprint TEXT NOT NULL UNIQUE,
                    created_at INTEGER NOT NULL,
                    spec_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_strategy_versions_strategy
                    ON strategy_versions(strategy_id, created_at DESC);
                CREATE TABLE IF NOT EXISTS backtest_artifacts (
                    artifact_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL UNIQUE,
                    run_hash TEXT NOT NULL,
                    report_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_backtest_artifacts_run_hash
                    ON backtest_artifacts(run_hash, created_at DESC);
                """
            )

    def _emit(self, event_type: str, run: dict[str, Any]) -> None:
        if self.audit_writer:
            self.audit_writer({
                "type": event_type,
                "run_id": run.get("run_id"),
                "strategy_id": run.get("strategy_id"),
                "symbol": run.get("symbol"),
                "status": run.get("status"),
                "stage": run.get("current_stage"),
                "strategy_version_id": run.get("strategy_version_id"),
            })

    @staticmethod
    def _canonical(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)

    def _ensure_version(
        self,
        *,
        strategy_id: str,
        params: dict[str, Any],
        code_fingerprint: str,
    ) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="strategy_pipeline")
        spec = {
            "schema_version": 1,
            "strategy_id": strategy_id,
            "params": json.loads(self._canonical(params)),
            "code_fingerprint": str(code_fingerprint or "unversioned-code"),
        }
        fingerprint = hashlib.sha256(self._canonical(spec).encode("utf-8")).hexdigest()
        version_id = f"strategy-{strategy_id}-{fingerprint[:16]}"
        created_at = self.now_ms()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO strategy_versions(version_id, strategy_id, fingerprint, created_at, spec_json)
                VALUES(?, ?, ?, ?, ?)
                """,
                (version_id, strategy_id, fingerprint, created_at, self._canonical(spec)),
            )
            row = connection.execute(
                "SELECT version_id, strategy_id, fingerprint, created_at, spec_json FROM strategy_versions WHERE fingerprint = ?",
                (fingerprint,),
            ).fetchone()
        return {
            "version_id": str(row["version_id"]),
            "strategy_id": str(row["strategy_id"]),
            "fingerprint": str(row["fingerprint"]),
            "created_at": int(row["created_at"]),
            "spec": json.loads(row["spec_json"]),
        }

    def _save(self, run: dict[str, Any]) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="strategy_pipeline")
        run["updated_at"] = self.now_ms()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO strategy_runs(
                    run_id, strategy_id, symbol, status, created_at, updated_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run["run_id"], run["strategy_id"], run["symbol"], run["status"],
                    run["created_at"], run["updated_at"],
                    json.dumps(run, ensure_ascii=False, default=str),
                ),
            )
        return run

    def _store_backtest_artifact(self, run: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="strategy_pipeline")
        reproducibility = report.get("reproducibility") if isinstance(report.get("reproducibility"), dict) else {}
        created_at = self.now_ms()
        artifact_id = f"backtest-{run['run_id']}"
        payload = {
            "schema_version": 1,
            "artifact_id": artifact_id,
            "run_id": run["run_id"],
            "strategy_id": run["strategy_id"],
            "strategy_version_id": run.get("strategy_version_id"),
            "strategy_fingerprint": run.get("strategy_fingerprint"),
            "code_fingerprint": run.get("code_fingerprint"),
            "symbol": run["symbol"],
            "params": run.get("params", {}),
            "source": report.get("source"),
            "data_points": report.get("data_points"),
            "dataset_manifest": report.get("dataset_manifest") or reproducibility.get("dataset_manifest", {}),
            "reproducibility": reproducibility,
            "execution_model": report.get("execution_model") or reproducibility.get("execution_model", ""),
            "acceptance": report.get("acceptance", {}),
            "lookahead_check": report.get("lookahead_check", {}),
            "temporal_validation": report.get("temporal_validation", {}),
            "selection_evidence": report.get("selection_evidence", {}),
            "data_admission": report.get("data_admission", {}),
            "current": report.get("current", {}),
            "created_at": created_at,
            "research_only": True,
            "paper_only": True,
            "live_order_allowed": False,
        }
        payload_json = self._canonical(payload)
        report_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        run_hash = str(reproducibility.get("run_hash") or report_hash[:16])
        with self._connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO backtest_artifacts(
                    artifact_id, run_id, run_hash, report_hash, created_at, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (artifact_id, run["run_id"], run_hash, report_hash, created_at, payload_json),
            )
        return {
            "artifact_id": artifact_id,
            "run_hash": run_hash,
            "report_hash": report_hash,
            "created_at": created_at,
            "integrity_status": "PASS",
        }

    def get_backtest_artifact(self, run_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT artifact_id, run_id, run_hash, report_hash, created_at, payload_json
                FROM backtest_artifacts WHERE run_id = ?
                """,
                (str(run_id or ""),),
            ).fetchone()
        if not row:
            return None
        payload_json = str(row["payload_json"])
        calculated_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
        return {
            "artifact_id": str(row["artifact_id"]),
            "run_id": str(row["run_id"]),
            "run_hash": str(row["run_hash"]),
            "report_hash": str(row["report_hash"]),
            "created_at": int(row["created_at"]),
            "integrity_status": "PASS" if calculated_hash == str(row["report_hash"]) else "BLOCK",
            "payload": json.loads(payload_json),
        }

    def define(
        self,
        *,
        strategy_id: str,
        symbol: str,
        params: dict[str, Any] | None = None,
        research_summary_id: str = "",
        code_fingerprint: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            timestamp = self.now_ms()
            clean_strategy_id = str(strategy_id or "").strip() or "unknown"
            clean_params = json.loads(self._canonical(dict(params or {})))
            version = self._ensure_version(
                strategy_id=clean_strategy_id,
                params=clean_params,
                code_fingerprint=code_fingerprint,
            )
            run = {
                "run_id": f"run-{timestamp}-{uuid.uuid4().hex[:8]}",
                "strategy_id": clean_strategy_id,
                "strategy_version_id": version["version_id"],
                "strategy_fingerprint": version["fingerprint"],
                "code_fingerprint": version["spec"]["code_fingerprint"],
                "symbol": str(symbol or "").strip().upper() or "UNKNOWN",
                "status": "DEFINED",
                "current_stage": "definition",
                "created_at": timestamp,
                "updated_at": timestamp,
                "params": clean_params,
                "research_summary_id": research_summary_id,
                "stages": {
                    "definition": {"status": "PASS", "time": timestamp},
                    "backtest": {"status": "WAIT"},
                    "doctor": {"status": "WAIT"},
                    "paper_authorization": {"status": "WAIT"},
                    "paper_run": {"status": "WAIT"},
                    "audit_review": {"status": "WAIT"},
                    "live_trading": {"status": "BLOCKED", "reason": "Live trading hard wall."},
                },
                "live_ready": False,
                "live_order_allowed": False,
            }
            self._save(run)
            self._emit("strategy_pipeline_defined", run)
            return run

    def get(self, run_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT payload_json FROM strategy_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def get_version(self, version_id: str) -> dict[str, Any] | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT version_id, strategy_id, fingerprint, created_at, spec_json FROM strategy_versions WHERE version_id = ?",
                (str(version_id or ""),),
            ).fetchone()
        if not row:
            return None
        return {
            "version_id": str(row["version_id"]),
            "strategy_id": str(row["strategy_id"]),
            "fingerprint": str(row["fingerprint"]),
            "created_at": int(row["created_at"]),
            "spec": json.loads(row["spec_json"]),
        }

    def latest(self, symbol: str = "", strategy_id: str = "") -> dict[str, Any] | None:
        clauses: list[str] = []
        params: list[Any] = []
        if symbol:
            clauses.append("symbol = ?")
            params.append(symbol.upper())
        if strategy_id:
            clauses.append("strategy_id = ?")
            params.append(strategy_id)
        sql = "SELECT payload_json FROM strategy_runs"
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY updated_at DESC LIMIT 1"
        with self._lock, self._connect() as connection:
            row = connection.execute(sql, params).fetchone()
        return json.loads(row["payload_json"]) if row else None

    def list(self, limit: int = 40) -> list[dict[str, Any]]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json FROM strategy_runs ORDER BY updated_at DESC LIMIT ?",
                (max(1, min(int(limit or 40), 500)),),
            ).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def _public_run(self, run: dict[str, Any]) -> dict[str, Any]:
        view = json.loads(json.dumps(run, ensure_ascii=False, default=str))
        stages = view.get("stages") if isinstance(view.get("stages"), dict) else {}
        legacy_blockers: list[str] = []
        validation_blockers: list[str] = []
        if not view.get("strategy_version_id"):
            legacy_blockers.append("immutable_strategy_version")
        if not view.get("code_fingerprint"):
            legacy_blockers.append("strategy_code_fingerprint")
        backtest = view.get("backtest") if isinstance(view.get("backtest"), dict) else {}
        has_backtest_evidence = bool(backtest) or stages.get("backtest", {}).get("status") in {"PASS", "BLOCK"}
        if has_backtest_evidence:
            lookahead_raw = backtest.get("lookahead_check")
            if not isinstance(lookahead_raw, dict) or not lookahead_raw:
                legacy_blockers.append("causal_prefix_invariance")
            else:
                prefix_raw = lookahead_raw.get("prefix_invariance")
                if not isinstance(prefix_raw, dict) or not prefix_raw:
                    legacy_blockers.append("causal_prefix_invariance")
                elif lookahead_raw.get("status") != "PASS" or prefix_raw.get("status") != "PASS":
                    validation_blockers.append("causal_prefix_invariance")

            evidence_contracts = (
                ("temporal_validation", "temporal_validation"),
                ("selection_evidence", "independent_selection_evidence"),
                ("data_admission", "strategy_data_admission"),
                ("acceptance", "backtest_acceptance"),
                ("binding", "backtest_binding"),
            )
            for field, blocker in evidence_contracts:
                evidence = backtest.get(field)
                if not isinstance(evidence, dict) or not evidence:
                    legacy_blockers.append(blocker)
                elif evidence.get("status") != "PASS":
                    validation_blockers.append(blocker)

            reproducibility = backtest.get("reproducibility")
            if not isinstance(reproducibility, dict) or not reproducibility:
                legacy_blockers.append("causal_reproducibility")
            elif (
                reproducibility.get("dataset_status") != "PASS"
                or reproducibility.get("hash_scope") != "FULL_OHLCV"
                or reproducibility.get("execution_model") != EXECUTION_MODEL_VERSION
                or not reproducibility.get("run_hash")
                or not reproducibility.get("data_hash")
                or not reproducibility.get("param_hash")
            ):
                validation_blockers.append("causal_reproducibility")

            data_admission = backtest.get("data_admission")
            if isinstance(data_admission, dict) and data_admission:
                admission_audit = verify_strategy_data_admission(
                    data_admission,
                    expected_symbol=str(view.get("symbol") or ""),
                    expected_data_hash=str(reproducibility.get("data_hash") or ""),
                    expected_lineage_id=str(data_admission.get("dataset_lineage_id") or ""),
                    verification_at=self.now_ms(),
                )
                backtest["data_admission_verification"] = admission_audit
                if admission_audit.get("status") != "PASS":
                    validation_blockers.append("strategy_data_admission")

        legacy_blockers = list(dict.fromkeys(legacy_blockers))
        validation_blockers = list(dict.fromkeys(validation_blockers))
        blockers = [*legacy_blockers, *validation_blockers]
        if blockers:
            view["stored_status"] = view.get("status")
            view["status"] = "LEGACY_BLOCKED" if legacy_blockers else "VALIDATION_BLOCKED"
            if legacy_blockers:
                view["legacy_blockers"] = legacy_blockers
            if validation_blockers:
                view["validation_blockers"] = validation_blockers
            view["paper_authorized"] = False
            view["validation_complete"] = False
            view["live_ready"] = False
            view["live_order_allowed"] = False
            stages["paper_authorization"] = {
                "status": "BLOCK",
                "reason": (
                    "Legacy run must be revalidated with the current kernel."
                    if legacy_blockers
                    else "Current validation evidence did not pass every mandatory gate."
                ),
                "blockers": blockers,
            }
            view["stages"] = stages
        return view

    def record_backtest(self, run_id: str, report: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            run = self.get(run_id)
            if not run:
                raise ValueError("Unknown strategy run.")
            acceptance = report.get("acceptance") if isinstance(report.get("acceptance"), dict) else {}
            lookahead = report.get("lookahead_check") if isinstance(report.get("lookahead_check"), dict) else {}
            temporal = report.get("temporal_validation") if isinstance(report.get("temporal_validation"), dict) else {}
            selection_evidence = report.get("selection_evidence") if isinstance(report.get("selection_evidence"), dict) else {}
            data_admission = report.get("data_admission") if isinstance(report.get("data_admission"), dict) else {}
            reproducibility = report.get("reproducibility") if isinstance(report.get("reproducibility"), dict) else {}
            prefix_invariance = lookahead.get("prefix_invariance") if isinstance(lookahead.get("prefix_invariance"), dict) else {}
            binding_blockers: list[str] = []
            if str(reproducibility.get("symbol") or "").upper() != str(run.get("symbol") or "").upper():
                binding_blockers.append("symbol_mismatch")
            if str(reproducibility.get("strategy_id") or "") != str(run.get("strategy_id") or ""):
                binding_blockers.append("strategy_id_mismatch")
            if str(reproducibility.get("strategy_fingerprint") or "") != str(run.get("code_fingerprint") or ""):
                binding_blockers.append("strategy_code_mismatch")
            if self._canonical(reproducibility.get("params") or {}) != self._canonical(run.get("params") or {}):
                binding_blockers.append("parameter_mismatch")
            if not reproducibility.get("run_hash") or not reproducibility.get("data_hash") or not reproducibility.get("param_hash"):
                binding_blockers.append("missing_reproducibility_hash")
            data_admission_verification = verify_strategy_data_admission(
                data_admission,
                expected_symbol=str(run.get("symbol") or ""),
                expected_data_hash=str(reproducibility.get("data_hash") or ""),
                expected_lineage_id=str(data_admission.get("dataset_lineage_id") or ""),
                verification_at=self.now_ms(),
            )
            if data_admission_verification.get("status") != "PASS":
                binding_blockers.append("data_admission_binding")
            binding = {
                "status": "PASS" if not binding_blockers else "BLOCK",
                "blockers": binding_blockers,
            }
            passed = (
                bool(report.get("ok"))
                and acceptance.get("status") == "PASS"
                and lookahead.get("status") == "PASS"
                and prefix_invariance.get("status") == "PASS"
                and temporal.get("status") == "PASS"
                and selection_evidence.get("status") == "PASS"
                and data_admission.get("paper_gate_status") == "PASS"
                and data_admission_verification.get("status") == "PASS"
                and binding["status"] == "PASS"
            )
            run["backtest"] = {
                "ok": bool(report.get("ok")),
                "source": report.get("source"),
                "data_points": report.get("data_points"),
                "reproducibility": report.get("reproducibility", {}),
                "dataset_manifest": report.get("dataset_manifest") or (report.get("reproducibility") or {}).get("dataset_manifest", {}),
                "execution_model": report.get("execution_model") or (report.get("reproducibility") or {}).get("execution_model", ""),
                "binding": binding,
                "acceptance": acceptance,
                "lookahead_check": lookahead,
                "current": report.get("current", {}),
                "temporal_validation": temporal,
                "selection_evidence": selection_evidence,
                "data_admission": data_admission,
                "data_admission_verification": data_admission_verification,
            }
            run["stages"]["backtest"] = {"status": "PASS" if passed else "BLOCK", "time": self.now_ms()}
            run["status"] = "BACKTESTED" if passed else "BLOCKED"
            run["current_stage"] = "backtest"
            run["backtest_artifact"] = self._store_backtest_artifact(run, report)
            self._save(run)
            self._emit("strategy_pipeline_backtest", run)
            return run

    def record_doctor(self, run_id: str, report: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            run = self.get(run_id)
            if not run:
                raise ValueError("Unknown strategy run.")
            score = float(report.get("score") or 0.0)
            lookahead = report.get("lookahead_check") if isinstance(report.get("lookahead_check"), dict) else {}
            passed = bool(report.get("ok")) and score >= 60 and lookahead.get("status") == "PASS"
            run["doctor"] = {
                "ok": bool(report.get("ok")),
                "score": score,
                "lookahead_check": lookahead,
                "summary": report.get("summary"),
            }
            run["stages"]["doctor"] = {"status": "PASS" if passed else "BLOCK", "time": self.now_ms()}
            backtest_passed = run["stages"].get("backtest", {}).get("status") == "PASS"
            run["status"] = "VALIDATED" if passed and backtest_passed else "BLOCKED"
            run["current_stage"] = "doctor"
            self._save(run)
            self._emit("strategy_pipeline_doctor", run)
            return run

    def authorize_paper(
        self,
        run_id: str,
        *,
        requested_params: dict[str, Any] | None = None,
        execution_profile: dict[str, Any] | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:
        with self._lock:
            run = self.get(run_id)
            if not run:
                raise ValueError("Unknown strategy run.")
            stages = run.get("stages", {})
            blockers = [name for name in ("backtest", "doctor") if stages.get(name, {}).get("status") != "PASS"]
            if not run.get("strategy_version_id"):
                blockers.append("immutable_strategy_version")
            temporal = (run.get("backtest") or {}).get("temporal_validation")
            if not isinstance(temporal, dict) or temporal.get("status") != "PASS":
                blockers.append("temporal_validation")
            backtest = run.get("backtest") if isinstance(run.get("backtest"), dict) else {}
            lookahead = backtest.get("lookahead_check") if isinstance(backtest.get("lookahead_check"), dict) else {}
            prefix_invariance = lookahead.get("prefix_invariance") if isinstance(lookahead.get("prefix_invariance"), dict) else {}
            if lookahead.get("status") != "PASS" or prefix_invariance.get("status") != "PASS":
                blockers.append("causal_prefix_invariance")
            acceptance = backtest.get("acceptance") if isinstance(backtest.get("acceptance"), dict) else {}
            reproducibility = backtest.get("reproducibility") if isinstance(backtest.get("reproducibility"), dict) else {}
            if acceptance.get("status") != "PASS":
                blockers.append("backtest_acceptance")
            if (
                reproducibility.get("dataset_status") != "PASS"
                or reproducibility.get("hash_scope") != "FULL_OHLCV"
                or reproducibility.get("execution_model") != EXECUTION_MODEL_VERSION
                or not reproducibility.get("run_hash")
                or not reproducibility.get("data_hash")
                or not reproducibility.get("param_hash")
            ):
                blockers.append("causal_reproducibility")
            binding = backtest.get("binding") if isinstance(backtest.get("binding"), dict) else {}
            if binding.get("status") != "PASS":
                blockers.append("backtest_binding")
            selection_evidence = backtest.get("selection_evidence") if isinstance(backtest.get("selection_evidence"), dict) else {}
            if selection_evidence.get("status") != "PASS":
                blockers.append("independent_selection_evidence")
            data_admission = backtest.get("data_admission") if isinstance(backtest.get("data_admission"), dict) else {}
            data_admission_verification = verify_strategy_data_admission(
                data_admission,
                expected_symbol=str(run.get("symbol") or ""),
                expected_data_hash=str(reproducibility.get("data_hash") or ""),
                expected_lineage_id=str(data_admission.get("dataset_lineage_id") or ""),
                verification_at=self.now_ms(),
            )
            if data_admission.get("paper_gate_status") != "PASS" or data_admission_verification.get("status") != "PASS":
                blockers.append("strategy_data_admission")
            backtest["data_admission_verification"] = data_admission_verification

            expected_params = run.get("params") if isinstance(run.get("params"), dict) else {}
            clean_requested_params = (
                json.loads(self._canonical(requested_params))
                if isinstance(requested_params, dict)
                else None
            )
            parameter_match = (
                clean_requested_params is not None
                and self._canonical(clean_requested_params) == self._canonical(expected_params)
            )
            if not parameter_match:
                blockers.append("paper_parameter_binding")

            clean_profile = dict(execution_profile or {})
            profile_mismatches: list[str] = []
            if not clean_profile:
                profile_mismatches.append("missing_execution_profile")
            for key, expected in self.VALIDATED_PAPER_PROFILE.items():
                actual = clean_profile.get(key)
                if isinstance(expected, str):
                    matches = str(actual or "").upper() == expected
                else:
                    matches = bool(actual) is expected
                if not matches:
                    profile_mismatches.append(key)
            try:
                profile_leverage = float(clean_profile.get("leverage"))
            except (TypeError, ValueError):
                profile_leverage = 0.0
            if abs(profile_leverage - 1.0) > 1e-9:
                profile_mismatches.append("leverage")
            if profile_mismatches:
                blockers.append("paper_execution_profile")

            run["paper_request_binding"] = {
                "status": "PASS" if parameter_match and not profile_mismatches else "BLOCK",
                "expected_params": expected_params,
                "requested_params": clean_requested_params or {},
                "execution_profile": clean_profile,
                "parameter_match": parameter_match,
                "profile_mismatches": list(dict.fromkeys(profile_mismatches)),
            }
            blockers = list(dict.fromkeys(blockers))
            allowed = not blockers
            run["paper_authorized"] = allowed
            run["paper_authorization_reason"] = "Validation gates passed." if allowed else f"Missing gates: {', '.join(blockers)}."
            run["stages"]["paper_authorization"] = {
                "status": "PASS" if allowed else "BLOCK",
                "time": self.now_ms(),
                "blockers": blockers,
            }
            run["status"] = "PAPER_READY" if allowed else "BLOCKED"
            run["current_stage"] = "paper_authorization"
            run["paper_authorization_preview"] = not commit
            if commit:
                run.pop("paper_authorization_preview", None)
                self._save(run)
                self._emit("strategy_pipeline_paper_authorized" if allowed else "strategy_pipeline_paper_blocked", run)
            return run

    def preview_paper_authorization(
        self,
        run_id: str,
        *,
        requested_params: dict[str, Any] | None = None,
        execution_profile: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.authorize_paper(
            run_id,
            requested_params=requested_params,
            execution_profile=execution_profile,
            commit=False,
        )

    def record_paper_run(self, run_id: str, paper: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            run = self.get(run_id)
            if not run:
                raise ValueError("Unknown strategy run.")
            if not run.get("paper_authorized"):
                raise ValueError("Paper run is not authorized by the validation pipeline.")
            timestamp = self.now_ms()
            run.setdefault("forward_started_at", timestamp)
            ledger_metrics = paper.get("ledger_metrics") if isinstance(paper.get("ledger_metrics"), dict) else {}
            closed_trade_count = int(ledger_metrics.get("closed_trade_count") or 0)
            duration_ms = max(timestamp - int(run.get("forward_started_at") or timestamp), 0)
            drawdown_pct = float(paper.get("drawdown_pct") or 0.0)
            blockers: list[str] = []
            if bool(paper.get("armed")):
                blockers.append("前向模拟仍在运行，停止后才能进入审计")
            if duration_ms < self.minimum_forward_duration_ms:
                blockers.append(f"前向运行 {duration_ms}ms，最低要求 {self.minimum_forward_duration_ms}ms")
            if closed_trade_count < self.minimum_forward_closed_trades:
                blockers.append(f"闭合交易 {closed_trade_count} 笔，最低要求 {self.minimum_forward_closed_trades} 笔")
            if drawdown_pct > self.maximum_forward_drawdown_pct:
                blockers.append(f"前向回撤 {drawdown_pct:.2f}% 超过上限 {self.maximum_forward_drawdown_pct:.2f}%")
            eligible = not blockers
            run["paper_run"] = {
                "armed": bool(paper.get("armed")),
                "equity": paper.get("equity"),
                "drawdown_pct": drawdown_pct,
                "order_count": int(ledger_metrics.get("order_count") or len(paper.get("orders") or [])),
                "filled_order_count": int(ledger_metrics.get("filled_order_count") or 0),
                "closed_trade_count": closed_trade_count,
                "recorded_at": timestamp,
                "duration_ms": duration_ms,
            }
            run["forward_graduation"] = {
                "eligible_for_audit": eligible,
                "status": "PASS" if eligible else "WAIT" if paper.get("armed") else "BLOCK",
                "blockers": blockers,
                "requirements": {
                    "minimum_duration_ms": self.minimum_forward_duration_ms,
                    "minimum_closed_trades": self.minimum_forward_closed_trades,
                    "maximum_drawdown_pct": self.maximum_forward_drawdown_pct,
                },
            }
            run["stages"]["paper_run"] = {
                "status": "PASS" if eligible else "RUNNING" if paper.get("armed") else "BLOCK",
                "time": timestamp,
                "blockers": blockers,
            }
            run["status"] = "PAPER_ELIGIBLE_FOR_REVIEW" if eligible else "PAPER_RUNNING" if paper.get("armed") else "PAPER_INSUFFICIENT"
            run["current_stage"] = "paper_run"
            self._save(run)
            self._emit("strategy_pipeline_paper_run", run)
            return run

    def review_paper_run(
        self,
        run_id: str,
        *,
        decision: str,
        reviewer: str,
        notes: str = "",
    ) -> dict[str, Any]:
        with self._lock:
            run = self.get(run_id)
            if not run:
                raise ValueError("Unknown strategy run.")
            clean_decision = str(decision or "").strip().upper()
            if clean_decision not in {"APPROVE", "REJECT"}:
                raise ValueError("Audit decision must be APPROVE or REJECT.")
            reviewer_name = str(reviewer or "").strip()
            if not reviewer_name:
                raise ValueError("Audit reviewer is required.")
            graduation = run.get("forward_graduation") if isinstance(run.get("forward_graduation"), dict) else {}
            eligible = bool(graduation.get("eligible_for_audit"))
            approved = clean_decision == "APPROVE" and eligible
            blockers = [] if eligible else list(graduation.get("blockers") or ["前向模拟尚未达到毕业门槛"])
            if clean_decision == "REJECT":
                blockers.append("人工审计拒绝")
            review = {
                "decision": clean_decision,
                "reviewer": reviewer_name,
                "notes": str(notes or "")[:2000],
                "reviewed_at": self.now_ms(),
                "approved": approved,
                "blockers": blockers,
            }
            run["audit_review"] = review
            run["stages"]["audit_review"] = {
                "status": "PASS" if approved else "BLOCK",
                "time": review["reviewed_at"],
                "blockers": blockers,
            }
            run["status"] = "PAPER_VALIDATED" if approved else "AUDIT_REJECTED" if clean_decision == "REJECT" else "AUDIT_BLOCKED"
            run["current_stage"] = "audit_review"
            run["validation_complete"] = approved
            run["live_ready"] = False
            run["live_order_allowed"] = False
            self._save(run)
            self._emit("strategy_pipeline_audit_pass" if approved else "strategy_pipeline_audit_block", run)
            return run

    def snapshot(self) -> dict[str, Any]:
        rows = [self._public_run(run) for run in self.list(20)]
        latest = rows[0] if rows else None
        with self._lock, self._connect() as connection:
            version_count = int(connection.execute("SELECT COUNT(*) FROM strategy_versions").fetchone()[0])
            run_count = int(connection.execute("SELECT COUNT(*) FROM strategy_runs").fetchone()[0])
            artifact_count = int(connection.execute("SELECT COUNT(*) FROM backtest_artifacts").fetchone()[0])
        return {
            "ok": True,
            "latest": latest,
            "runs": rows,
            "run_count": run_count,
            "version_count": version_count,
            "backtest_artifact_count": artifact_count,
            "forward_requirements": {
                "minimum_duration_ms": self.minimum_forward_duration_ms,
                "minimum_closed_trades": self.minimum_forward_closed_trades,
                "maximum_drawdown_pct": self.maximum_forward_drawdown_pct,
            },
            "stage_order": self.STAGE_ORDER,
            "live_order_allowed": False,
        }
