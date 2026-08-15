from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Callable, Iterator

from .implementation_manifest import build_implementation_manifest
from .portfolio_evidence_bundle import verify_portfolio_evidence_bundle
from .sqlite_runtime import connect_runtime_sqlite, require_runtime_writable
from .trusted_clock import verify_trusted_clock_attestation


PORTFOLIO_EXPERIMENT_REGISTRY_VERSION = "portfolio-experiment-registry-v1"
PORTFOLIO_EXPERIMENT_INTENT_VERSION = "portfolio-experiment-intent-v1"
PORTFOLIO_EXPERIMENT_BINDING_VERSION = "portfolio-experiment-binding-v1"
PORTFOLIO_EXPERIMENT_COMPLETION_VERSION = "portfolio-experiment-completion-v1"


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def fingerprint_source_files(source_files: list[Path | str]) -> dict[str, Any]:
    return build_implementation_manifest(source_files)


def verify_research_protocol(protocol: dict[str, Any]) -> dict[str, Any]:
    payload = dict(protocol or {})
    expected_hash = str(payload.pop("protocol_hash", "") or "")
    blockers: list[str] = []
    if not str(protocol.get("schema_version") or ""):
        blockers.append("protocol_schema_missing")
    if not str(protocol.get("research_generation") or ""):
        blockers.append("research_generation_missing")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("protocol_hash_mismatch")
    if protocol.get("research_only") is not True:
        blockers.append("protocol_must_be_research_only")
    if protocol.get("paper_authorized") is not False or protocol.get("live_order_allowed") is not False:
        blockers.append("protocol_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": blockers,
        "protocol_hash": expected_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_experiment_binding(binding: dict[str, Any]) -> dict[str, Any]:
    payload = dict(binding or {})
    expected_hash = str(payload.pop("binding_hash", "") or "")
    blockers: list[str] = []
    if str(binding.get("schema_version") or "") != PORTFOLIO_EXPERIMENT_BINDING_VERSION:
        blockers.append("experiment_binding_schema_invalid")
    if str(binding.get("status") or "") != "CLAIMED_FOR_SINGLE_RUN":
        blockers.append("experiment_binding_status_invalid")
    for field in (
        "experiment_id",
        "intent_hash",
        "protocol_hash",
        "implementation_fingerprint",
        "start_event_hash",
    ):
        if not str(binding.get(field) or ""):
            blockers.append(f"experiment_binding_{field}_missing")
    if int(binding.get("registered_at") or 0) <= 0 or int(binding.get("started_at") or 0) <= 0:
        blockers.append("experiment_binding_timestamp_invalid")
    if int(binding.get("started_at") or 0) + 5_000 < int(binding.get("registered_at") or 0):
        blockers.append("experiment_started_before_registration")
    clock = dict(binding.get("start_clock_attestation") or {})
    clock_verification = verify_trusted_clock_attestation(clock)
    if clock_verification.get("status") != "PASS":
        blockers.extend(
            f"experiment_start_clock:{item}"
            for item in clock_verification.get("blockers") or ["attestation_blocked"]
        )
    if str(binding.get("start_clock_attestation_hash") or "") != str(clock.get("attestation_hash") or ""):
        blockers.append("experiment_start_clock_hash_mismatch")
    if abs(int(binding.get("started_at") or 0) - int(clock.get("attested_now_ms") or 0)) > 5_000:
        blockers.append("experiment_start_clock_timestamp_mismatch")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("experiment_binding_hash_mismatch")
    if binding.get("research_only") is not True:
        blockers.append("experiment_binding_must_be_research_only")
    if binding.get("paper_authorized") is not False or binding.get("live_order_allowed") is not False:
        blockers.append("experiment_binding_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "binding_hash": expected_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_experiment_completion_receipt(receipt: dict[str, Any]) -> dict[str, Any]:
    payload = dict(receipt or {})
    expected_hash = str(payload.pop("receipt_hash", "") or "")
    blockers: list[str] = []
    if str(receipt.get("schema_version") or "") != PORTFOLIO_EXPERIMENT_COMPLETION_VERSION:
        blockers.append("experiment_completion_schema_invalid")
    if str(receipt.get("status") or "") != "COMPLETED":
        blockers.append("experiment_completion_status_invalid")
    for field in (
        "experiment_id",
        "intent_hash",
        "protocol_hash",
        "binding_hash",
        "batch_run_hash",
        "dataset_hash",
        "report_file",
        "report_path",
        "report_file_sha256",
        "completion_event_hash",
    ):
        if not str(receipt.get(field) or ""):
            blockers.append(f"experiment_completion_{field}_missing")
    if int(receipt.get("completed_at") or 0) <= 0:
        blockers.append("experiment_completion_timestamp_invalid")
    clock = dict(receipt.get("completion_clock_attestation") or {})
    clock_verification = verify_trusted_clock_attestation(clock)
    if clock_verification.get("status") != "PASS":
        blockers.extend(
            f"experiment_completion_clock:{item}"
            for item in clock_verification.get("blockers") or ["attestation_blocked"]
        )
    if str(receipt.get("completion_clock_attestation_hash") or "") != str(clock.get("attestation_hash") or ""):
        blockers.append("experiment_completion_clock_hash_mismatch")
    if abs(int(receipt.get("completed_at") or 0) - int(clock.get("attested_now_ms") or 0)) > 5_000:
        blockers.append("experiment_completion_clock_timestamp_mismatch")
    if str(receipt.get("candidate_file") or ""):
        if not str(receipt.get("candidate_path") or ""):
            blockers.append("experiment_completion_candidate_path_missing")
        if not str(receipt.get("candidate_file_sha256") or ""):
            blockers.append("experiment_completion_candidate_file_hash_missing")
        if not str(receipt.get("candidate_hash") or ""):
            blockers.append("experiment_completion_candidate_hash_missing")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("experiment_completion_receipt_hash_mismatch")
    if receipt.get("research_only") is not True:
        blockers.append("experiment_completion_must_be_research_only")
    if receipt.get("paper_authorized") is not False or receipt.get("live_order_allowed") is not False:
        blockers.append("experiment_completion_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "receipt_hash": expected_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_experiment_completion_artifacts(
    receipt: dict[str, Any],
    *,
    candidate_path: Path | str | None = None,
    required_directory: Path | str | None = None,
) -> dict[str, Any]:
    receipt_verification = verify_experiment_completion_receipt(receipt)
    blockers = list(receipt_verification.get("blockers") or [])
    report_path = Path(str(receipt.get("report_path") or "")).resolve()
    recorded_candidate_path = Path(str(receipt.get("candidate_path") or "")).resolve()
    directory = Path(required_directory).resolve() if required_directory else None
    if report_path.name != str(receipt.get("report_file") or ""):
        blockers.append("experiment_report_artifact_name_mismatch")
    if directory and report_path.parent != directory:
        blockers.append("experiment_report_artifact_directory_mismatch")
    try:
        report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
    except OSError:
        report_hash = ""
        blockers.append("experiment_report_artifact_unavailable")
    if report_hash != str(receipt.get("report_file_sha256") or ""):
        blockers.append("experiment_report_artifact_hash_mismatch")
    if str(receipt.get("candidate_file") or ""):
        if recorded_candidate_path.name != str(receipt.get("candidate_file") or ""):
            blockers.append("experiment_candidate_artifact_name_mismatch")
        if directory and recorded_candidate_path.parent != directory:
            blockers.append("experiment_candidate_artifact_directory_mismatch")
        if candidate_path and Path(candidate_path).resolve() != recorded_candidate_path:
            blockers.append("experiment_candidate_artifact_path_mismatch")
        try:
            candidate_hash = hashlib.sha256(recorded_candidate_path.read_bytes()).hexdigest()
        except OSError:
            candidate_hash = ""
            blockers.append("experiment_candidate_artifact_unavailable")
        if candidate_hash != str(receipt.get("candidate_file_sha256") or ""):
            blockers.append("experiment_candidate_artifact_hash_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "receipt_verification": receipt_verification,
        "report_path": str(report_path),
        "candidate_path": str(recorded_candidate_path) if str(receipt.get("candidate_file") or "") else "",
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_completion_against_candidate(
    receipt: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    receipt_verification = verify_experiment_completion_receipt(receipt)
    blockers = list(receipt_verification.get("blockers") or [])
    governance = candidate.get("research_governance") if isinstance(candidate.get("research_governance"), dict) else {}
    binding = governance.get("experiment_binding") if isinstance(governance.get("experiment_binding"), dict) else {}
    binding_verification = verify_experiment_binding(binding)
    if binding_verification.get("status") != "PASS":
        blockers.extend(
            f"candidate_experiment_binding:{item}"
            for item in binding_verification.get("blockers") or ["binding_blocked"]
        )
    comparisons = {
        "experiment_id": str(binding.get("experiment_id") or ""),
        "intent_hash": str(binding.get("intent_hash") or ""),
        "protocol_hash": str(binding.get("protocol_hash") or ""),
        "binding_hash": str(binding.get("binding_hash") or ""),
        "batch_run_hash": str(candidate.get("research_report_hash") or ""),
        "dataset_hash": str(candidate.get("dataset_hash") or ""),
        "candidate_hash": str(candidate.get("candidate_hash") or ""),
    }
    for field, expected in comparisons.items():
        if str(receipt.get(field) or "") != expected:
            blockers.append(f"experiment_completion_candidate_{field}_mismatch")
    if int(receipt.get("completed_at") or 0) + 5_000 < int(binding.get("started_at") or 0):
        blockers.append("experiment_completed_before_start")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "receipt_verification": receipt_verification,
        "binding_verification": binding_verification,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class PortfolioExperimentRegistry:
    def __init__(
        self,
        *,
        db_path: Path | str,
        now_ms: Callable[[], int] = _now_ms,
        read_only: bool = False,
    ) -> None:
        self.db_path = Path(db_path)
        self.now_ms = now_ms
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
            connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        try:
            yield connection
            if not self.read_only:
                connection.commit()
        except Exception:
            if not self.read_only:
                connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS portfolio_experiments (
                    experiment_id TEXT PRIMARY KEY,
                    intent_hash TEXT UNIQUE NOT NULL,
                    protocol_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    intent_json TEXT NOT NULL,
                    binding_json TEXT NOT NULL DEFAULT '{}',
                    completion_json TEXT NOT NULL DEFAULT '{}',
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_portfolio_experiments_status
                    ON portfolio_experiments(status, updated_at DESC);
                CREATE TABLE IF NOT EXISTS portfolio_experiment_events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    experiment_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_time INTEGER NOT NULL,
                    previous_event_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    event_hash TEXT UNIQUE NOT NULL,
                    FOREIGN KEY(experiment_id) REFERENCES portfolio_experiments(experiment_id)
                );
                CREATE INDEX IF NOT EXISTS idx_portfolio_experiment_events_experiment
                    ON portfolio_experiment_events(experiment_id, seq);
                """
            )

    @staticmethod
    def _event_base(
        *,
        experiment_id: str,
        event_type: str,
        event_time: int,
        previous_event_hash: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "schema_version": PORTFOLIO_EXPERIMENT_REGISTRY_VERSION,
            "experiment_id": experiment_id,
            "event_type": event_type,
            "event_time": int(event_time),
            "previous_event_hash": previous_event_hash,
            "payload": payload,
        }

    def _append_event(
        self,
        connection: sqlite3.Connection,
        *,
        experiment_id: str,
        event_type: str,
        event_time: int,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        previous = connection.execute(
            "SELECT event_hash FROM portfolio_experiment_events ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        previous_hash = str(previous["event_hash"] or "") if previous else ""
        base = self._event_base(
            experiment_id=experiment_id,
            event_type=event_type,
            event_time=event_time,
            previous_event_hash=previous_hash,
            payload=payload,
        )
        event_hash = _canonical_hash(base)
        cursor = connection.execute(
            """
            INSERT INTO portfolio_experiment_events(
                experiment_id, event_type, event_time, previous_event_hash,
                payload_json, event_hash
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                experiment_id,
                event_type,
                int(event_time),
                previous_hash,
                json.dumps(payload, ensure_ascii=False, sort_keys=True),
                event_hash,
            ),
        )
        return {
            **base,
            "seq": int(cursor.lastrowid),
            "event_hash": event_hash,
        }

    def _audit_connection(self, connection: sqlite3.Connection) -> dict[str, Any]:
        blockers: list[str] = []
        previous_hash = ""
        last_event_by_experiment: dict[str, str] = {}
        event_rows = connection.execute(
            "SELECT * FROM portfolio_experiment_events ORDER BY seq"
        ).fetchall()
        for row in event_rows:
            try:
                payload = json.loads(str(row["payload_json"] or "{}"))
            except json.JSONDecodeError:
                payload = {}
                blockers.append(f"event_payload_invalid:{row['seq']}")
            base = self._event_base(
                experiment_id=str(row["experiment_id"] or ""),
                event_type=str(row["event_type"] or ""),
                event_time=int(row["event_time"] or 0),
                previous_event_hash=str(row["previous_event_hash"] or ""),
                payload=payload,
            )
            if str(row["previous_event_hash"] or "") != previous_hash:
                blockers.append(f"event_chain_previous_hash_mismatch:{row['seq']}")
            if _canonical_hash(base) != str(row["event_hash"] or ""):
                blockers.append(f"event_hash_mismatch:{row['seq']}")
            previous_hash = str(row["event_hash"] or "")
            last_event_by_experiment[str(row["experiment_id"] or "")] = str(row["event_type"] or "")

        status_event = {
            "REGISTERED": "REGISTERED",
            "RUNNING": "CLAIMED",
            "COMPLETED": "COMPLETED",
            "ABORTED": "ABORTED",
        }
        experiment_rows = connection.execute(
            "SELECT * FROM portfolio_experiments ORDER BY created_at, experiment_id"
        ).fetchall()
        for row in experiment_rows:
            experiment_id = str(row["experiment_id"] or "")
            try:
                intent = json.loads(str(row["intent_json"] or "{}"))
            except json.JSONDecodeError:
                intent = {}
                blockers.append(f"experiment_intent_invalid:{experiment_id}")
            intent_payload = dict(intent)
            expected_intent_hash = str(intent_payload.pop("intent_hash", "") or "")
            if expected_intent_hash != str(row["intent_hash"] or "") or _canonical_hash(intent_payload) != expected_intent_hash:
                blockers.append(f"experiment_intent_hash_mismatch:{experiment_id}")
            if str(intent.get("experiment_id") or "") != experiment_id:
                blockers.append(f"experiment_intent_id_mismatch:{experiment_id}")
            if str(intent.get("protocol_hash") or "") != str(row["protocol_hash"] or ""):
                blockers.append(f"experiment_protocol_hash_mismatch:{experiment_id}")
            if str(intent.get("schema_version") or "") != PORTFOLIO_EXPERIMENT_INTENT_VERSION:
                blockers.append(f"experiment_intent_schema_invalid:{experiment_id}")
            protocol = intent.get("protocol") if isinstance(intent.get("protocol"), dict) else {}
            protocol_verification = verify_research_protocol(protocol)
            if protocol_verification.get("status") != "PASS":
                blockers.extend(
                    f"experiment_protocol:{experiment_id}:{item}"
                    for item in protocol_verification.get("blockers") or ["protocol_blocked"]
                )
            registration_clock = (
                intent.get("registration_clock_attestation")
                if isinstance(intent.get("registration_clock_attestation"), dict)
                else {}
            )
            registration_clock_verification = verify_trusted_clock_attestation(registration_clock)
            if registration_clock_verification.get("status") != "PASS":
                blockers.extend(
                    f"experiment_registration_clock:{experiment_id}:{item}"
                    for item in registration_clock_verification.get("blockers") or ["attestation_blocked"]
                )
            if str(intent.get("registration_clock_attestation_hash") or "") != str(registration_clock.get("attestation_hash") or ""):
                blockers.append(f"experiment_registration_clock_hash_mismatch:{experiment_id}")
            if int(intent.get("registered_at") or 0) != int(registration_clock.get("attested_now_ms") or 0):
                blockers.append(f"experiment_registration_clock_timestamp_mismatch:{experiment_id}")
            if (
                intent.get("research_only") is not True
                or intent.get("paper_authorized") is not False
                or intent.get("live_order_allowed") is not False
            ):
                blockers.append(f"experiment_intent_execution_authority_invalid:{experiment_id}")
            status = str(row["status"] or "")
            if status_event.get(status) != last_event_by_experiment.get(experiment_id):
                blockers.append(f"experiment_status_event_mismatch:{experiment_id}")
            if status in {"RUNNING", "COMPLETED"}:
                try:
                    binding = json.loads(str(row["binding_json"] or "{}"))
                except json.JSONDecodeError:
                    binding = {}
                verification = verify_experiment_binding(binding)
                if verification.get("status") != "PASS":
                    blockers.extend(
                        f"experiment_binding:{experiment_id}:{item}"
                        for item in verification.get("blockers") or ["binding_blocked"]
                    )
            if status == "COMPLETED":
                try:
                    receipt = json.loads(str(row["completion_json"] or "{}"))
                except json.JSONDecodeError:
                    receipt = {}
                verification = verify_experiment_completion_receipt(receipt)
                if verification.get("status") != "PASS":
                    blockers.extend(
                        f"experiment_completion:{experiment_id}:{item}"
                        for item in verification.get("blockers") or ["receipt_blocked"]
                    )
                report_path = Path(str(receipt.get("report_path") or ""))
                try:
                    report_hash = hashlib.sha256(report_path.read_bytes()).hexdigest()
                except OSError:
                    report_hash = ""
                    blockers.append(f"experiment_report_artifact_unavailable:{experiment_id}")
                if report_hash != str(receipt.get("report_file_sha256") or ""):
                    blockers.append(f"experiment_report_artifact_hash_mismatch:{experiment_id}")
                candidate_path_text = str(receipt.get("candidate_path") or "")
                if candidate_path_text:
                    try:
                        candidate_hash = hashlib.sha256(Path(candidate_path_text).read_bytes()).hexdigest()
                    except OSError:
                        candidate_hash = ""
                        blockers.append(f"experiment_candidate_artifact_unavailable:{experiment_id}")
                    if candidate_hash != str(receipt.get("candidate_file_sha256") or ""):
                        blockers.append(f"experiment_candidate_artifact_hash_mismatch:{experiment_id}")
        summary = {
            "schema_version": PORTFOLIO_EXPERIMENT_REGISTRY_VERSION,
            "status": "PASS" if not blockers else "BLOCK",
            "blockers": list(dict.fromkeys(blockers)),
            "experiment_count": len(experiment_rows),
            "event_count": len(event_rows),
            "last_event_hash": previous_hash,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        summary["audit_hash"] = _canonical_hash(summary)
        return summary

    def register(
        self,
        *,
        protocol: dict[str, Any],
        source_files: list[Path | str],
        clock_attestation: dict[str, Any],
    ) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="portfolio_experiment_registry")
        protocol_verification = verify_research_protocol(protocol)
        clock_verification = verify_trusted_clock_attestation(clock_attestation)
        blockers = list(protocol_verification.get("blockers") or [])
        if clock_verification.get("status") != "PASS":
            blockers.extend(
                f"registration_clock:{item}"
                for item in clock_verification.get("blockers") or ["attestation_blocked"]
            )
        try:
            implementation = fingerprint_source_files(source_files)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            implementation = {"files": [], "fingerprint": ""}
            blockers.append(f"registration_source_unavailable:{type(exc).__name__}")
        if not implementation.get("files") or not implementation.get("fingerprint"):
            blockers.append("registration_implementation_fingerprint_missing")
        registered_at = int(clock_attestation.get("attested_now_ms") or 0)
        if registered_at <= 0:
            blockers.append("registration_timestamp_invalid")
        if blockers:
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": list(dict.fromkeys(blockers)),
                "protocol_verification": protocol_verification,
                "clock_verification": clock_verification,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        identity_seed = {
            "protocol_hash": str(protocol.get("protocol_hash") or ""),
            "implementation_fingerprint": str(implementation.get("fingerprint") or ""),
            "registered_at": registered_at,
        }
        experiment_id = f"pexp-{registered_at}-{_canonical_hash(identity_seed)[:12]}"
        intent = {
            "schema_version": PORTFOLIO_EXPERIMENT_INTENT_VERSION,
            "experiment_id": experiment_id,
            "status": "REGISTERED",
            "protocol_hash": str(protocol.get("protocol_hash") or ""),
            "protocol": protocol,
            "implementation": implementation,
            "registered_at": registered_at,
            "registration_clock_attestation_hash": str(clock_attestation.get("attestation_hash") or ""),
            "registration_clock_attestation": clock_attestation,
            "consumption_policy": "SINGLE_CLAIM_NO_REPLAY",
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        intent["intent_hash"] = _canonical_hash(intent)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            audit = self._audit_connection(connection)
            if audit.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [f"registry_integrity:{item}" for item in audit.get("blockers") or []],
                    "registry_audit": audit,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            try:
                connection.execute(
                    """
                    INSERT INTO portfolio_experiments(
                        experiment_id, intent_hash, protocol_hash, status,
                        intent_json, created_at, updated_at
                    ) VALUES (?, ?, ?, 'REGISTERED', ?, ?, ?)
                    """,
                    (
                        experiment_id,
                        str(intent["intent_hash"]),
                        str(protocol.get("protocol_hash") or ""),
                        json.dumps(intent, ensure_ascii=False, sort_keys=True),
                        registered_at,
                        registered_at,
                    ),
                )
            except sqlite3.IntegrityError:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["experiment_registration_conflict"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            event = self._append_event(
                connection,
                experiment_id=experiment_id,
                event_type="REGISTERED",
                event_time=registered_at,
                payload={
                    "intent_hash": str(intent["intent_hash"]),
                    "protocol_hash": str(protocol.get("protocol_hash") or ""),
                    "implementation_fingerprint": str(implementation.get("fingerprint") or ""),
                },
            )
        return {
            "ok": True,
            "status": "REGISTERED",
            "experiment_id": experiment_id,
            "intent": intent,
            "event": event,
            "registry_path": str(self.db_path.resolve()),
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def claim(
        self,
        *,
        experiment_id: str,
        protocol: dict[str, Any],
        source_files: list[Path | str],
        clock_attestation: dict[str, Any],
    ) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="portfolio_experiment_registry")
        clean_id = str(experiment_id or "").strip()
        protocol_verification = verify_research_protocol(protocol)
        clock_verification = verify_trusted_clock_attestation(clock_attestation)
        blockers = list(protocol_verification.get("blockers") or [])
        if not clean_id:
            blockers.append("experiment_id_missing")
        if clock_verification.get("status") != "PASS":
            blockers.extend(
                f"start_clock:{item}"
                for item in clock_verification.get("blockers") or ["attestation_blocked"]
            )
        try:
            implementation = fingerprint_source_files(source_files)
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            implementation = {"files": [], "fingerprint": ""}
            blockers.append(f"start_source_unavailable:{type(exc).__name__}")
        if blockers:
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": list(dict.fromkeys(blockers)),
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        started_at = int(clock_attestation.get("attested_now_ms") or 0)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            audit = self._audit_connection(connection)
            if audit.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [f"registry_integrity:{item}" for item in audit.get("blockers") or []],
                    "registry_audit": audit,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            row = connection.execute(
                "SELECT * FROM portfolio_experiments WHERE experiment_id = ?",
                (clean_id,),
            ).fetchone()
            if not row:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["experiment_not_registered"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            if str(row["status"] or "") != "REGISTERED":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [f"experiment_not_claimable:{row['status']}"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            intent = json.loads(str(row["intent_json"] or "{}"))
            stored_protocol = intent.get("protocol") if isinstance(intent.get("protocol"), dict) else {}
            if stored_protocol != protocol or str(row["protocol_hash"] or "") != str(protocol.get("protocol_hash") or ""):
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["experiment_protocol_drift"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            stored_implementation = intent.get("implementation") if isinstance(intent.get("implementation"), dict) else {}
            if stored_implementation != implementation:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["experiment_implementation_drift"],
                    "registered_fingerprint": str(stored_implementation.get("fingerprint") or ""),
                    "current_fingerprint": str(implementation.get("fingerprint") or ""),
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            registered_at = int(intent.get("registered_at") or 0)
            if started_at + 5_000 < registered_at:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["experiment_started_before_registration"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            binding_core = {
                "schema_version": PORTFOLIO_EXPERIMENT_BINDING_VERSION,
                "status": "CLAIMED_FOR_SINGLE_RUN",
                "experiment_id": clean_id,
                "intent_hash": str(row["intent_hash"] or ""),
                "protocol_hash": str(row["protocol_hash"] or ""),
                "implementation_fingerprint": str(implementation.get("fingerprint") or ""),
                "registered_at": registered_at,
                "started_at": started_at,
                "start_clock_attestation_hash": str(clock_attestation.get("attestation_hash") or ""),
                "start_clock_attestation": clock_attestation,
                "consumption_policy": "SINGLE_CLAIM_NO_REPLAY",
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            binding_core_hash = _canonical_hash(binding_core)
            event = self._append_event(
                connection,
                experiment_id=clean_id,
                event_type="CLAIMED",
                event_time=started_at,
                payload={
                    "intent_hash": str(row["intent_hash"] or ""),
                    "binding_core_hash": binding_core_hash,
                },
            )
            binding = {
                **binding_core,
                "start_event_hash": str(event["event_hash"]),
            }
            binding["binding_hash"] = _canonical_hash(binding)
            connection.execute(
                """
                UPDATE portfolio_experiments
                SET status = 'RUNNING', binding_json = ?, updated_at = ?
                WHERE experiment_id = ? AND status = 'REGISTERED'
                """,
                (json.dumps(binding, ensure_ascii=False, sort_keys=True), started_at, clean_id),
            )
        return {
            "ok": True,
            "status": "CLAIMED",
            "experiment_id": clean_id,
            "binding": binding,
            "event": event,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def complete(
        self,
        *,
        experiment_id: str,
        report_path: Path | str,
        candidate_path: Path | str | None,
        clock_attestation: dict[str, Any],
    ) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="portfolio_experiment_registry")
        clean_id = str(experiment_id or "").strip()
        clock_verification = verify_trusted_clock_attestation(clock_attestation)
        blockers: list[str] = []
        if not clean_id:
            blockers.append("experiment_id_missing")
        if clock_verification.get("status") != "PASS":
            blockers.extend(
                f"completion_clock:{item}"
                for item in clock_verification.get("blockers") or ["attestation_blocked"]
            )
        report_file = Path(report_path).resolve()
        candidate_file = Path(candidate_path).resolve() if candidate_path else None
        report: dict[str, Any] = {}
        candidate: dict[str, Any] = {}
        try:
            report_bytes = report_file.read_bytes()
            report = json.loads(report_bytes.decode("utf-8"))
            if not isinstance(report, dict):
                raise ValueError("report_payload_invalid")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            report_bytes = b""
            blockers.append(f"experiment_report_unavailable:{type(exc).__name__}")
        candidate_bytes = b""
        if candidate_file:
            try:
                candidate_bytes = candidate_file.read_bytes()
                candidate = json.loads(candidate_bytes.decode("utf-8"))
                if not isinstance(candidate, dict):
                    raise ValueError("candidate_payload_invalid")
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                blockers.append(f"experiment_candidate_unavailable:{type(exc).__name__}")
        evidence_bundle_verification = verify_portfolio_evidence_bundle(
            report,
            require_bundle=bool((report.get("spec") or {}).get("evidence_bundle_required") is True),
        )
        if evidence_bundle_verification.get("status") != "PASS":
            blockers.extend(
                f"experiment_report_evidence_bundle:{item}"
                for item in evidence_bundle_verification.get("blockers") or ["verification_failed"]
            )
        binding = report.get("experiment_governance") if isinstance(report.get("experiment_governance"), dict) else {}
        binding_verification = verify_experiment_binding(binding)
        if binding_verification.get("status") != "PASS":
            blockers.extend(
                f"experiment_report_binding:{item}"
                for item in binding_verification.get("blockers") or ["binding_blocked"]
            )
        if str(binding.get("experiment_id") or "") != clean_id:
            blockers.append("experiment_report_id_mismatch")
        if (
            report.get("research_only") is not True
            or report.get("paper_authorized") is not False
            or report.get("live_order_allowed") is not False
        ):
            blockers.append("experiment_report_has_execution_authority")
        if not str(report.get("batch_run_hash") or ""):
            blockers.append("experiment_report_batch_hash_missing")
        if not str((report.get("dataset_manifest") or {}).get("data_hash") or ""):
            blockers.append("experiment_report_dataset_hash_missing")
        if candidate:
            candidate_governance = candidate.get("research_governance") if isinstance(candidate.get("research_governance"), dict) else {}
            candidate_binding = candidate_governance.get("experiment_binding") if isinstance(candidate_governance.get("experiment_binding"), dict) else {}
            if candidate_binding != binding:
                blockers.append("experiment_candidate_binding_mismatch")
            if str(candidate.get("research_report_hash") or "") != str(report.get("batch_run_hash") or ""):
                blockers.append("experiment_candidate_report_hash_mismatch")
            if str(candidate.get("dataset_hash") or "") != str((report.get("dataset_manifest") or {}).get("data_hash") or ""):
                blockers.append("experiment_candidate_dataset_hash_mismatch")
            if (
                candidate.get("research_only") is not True
                or candidate.get("paper_authorized") is not False
                or candidate.get("live_order_allowed") is not False
            ):
                blockers.append("experiment_candidate_has_execution_authority")
        if blockers:
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": list(dict.fromkeys(blockers)),
                "binding_verification": binding_verification,
                "evidence_bundle_verification": evidence_bundle_verification,
                "clock_verification": clock_verification,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        completed_at = int(clock_attestation.get("attested_now_ms") or 0)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            audit = self._audit_connection(connection)
            if audit.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [f"registry_integrity:{item}" for item in audit.get("blockers") or []],
                    "registry_audit": audit,
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            row = connection.execute(
                "SELECT * FROM portfolio_experiments WHERE experiment_id = ?",
                (clean_id,),
            ).fetchone()
            if not row:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["experiment_not_registered"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            if str(row["status"] or "") != "RUNNING":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [f"experiment_not_completable:{row['status']}"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            stored_binding = json.loads(str(row["binding_json"] or "{}"))
            if stored_binding != binding:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["experiment_stored_binding_mismatch"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            receipt_core = {
                "schema_version": PORTFOLIO_EXPERIMENT_COMPLETION_VERSION,
                "status": "COMPLETED",
                "experiment_id": clean_id,
                "intent_hash": str(row["intent_hash"] or ""),
                "protocol_hash": str(row["protocol_hash"] or ""),
                "binding_hash": str(binding.get("binding_hash") or ""),
                "batch_run_hash": str(report.get("batch_run_hash") or ""),
                "dataset_hash": str((report.get("dataset_manifest") or {}).get("data_hash") or ""),
                "report_file": report_file.name,
                "report_path": str(report_file),
                "report_file_sha256": hashlib.sha256(report_bytes).hexdigest(),
                "candidate_file": candidate_file.name if candidate_file else "",
                "candidate_path": str(candidate_file) if candidate_file else "",
                "candidate_file_sha256": hashlib.sha256(candidate_bytes).hexdigest() if candidate_bytes else "",
                "candidate_hash": str(candidate.get("candidate_hash") or ""),
                "completed_at": completed_at,
                "completion_clock_attestation_hash": str(clock_attestation.get("attestation_hash") or ""),
                "completion_clock_attestation": clock_attestation,
                "artifact_policy": "CONTENT_ADDRESSED_LOCAL_REPORTS",
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
            receipt_core_hash = _canonical_hash(receipt_core)
            event = self._append_event(
                connection,
                experiment_id=clean_id,
                event_type="COMPLETED",
                event_time=completed_at,
                payload={
                    "binding_hash": str(binding.get("binding_hash") or ""),
                    "receipt_core_hash": receipt_core_hash,
                    "batch_run_hash": str(report.get("batch_run_hash") or ""),
                },
            )
            receipt = {
                **receipt_core,
                "completion_event_hash": str(event["event_hash"]),
            }
            receipt["receipt_hash"] = _canonical_hash(receipt)
            connection.execute(
                """
                UPDATE portfolio_experiments
                SET status = 'COMPLETED', completion_json = ?, updated_at = ?
                WHERE experiment_id = ? AND status = 'RUNNING'
                """,
                (json.dumps(receipt, ensure_ascii=False, sort_keys=True), completed_at, clean_id),
            )
        return {
            "ok": True,
            "status": "COMPLETED",
            "experiment_id": clean_id,
            "receipt": receipt,
            "event": event,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def abort(
        self,
        *,
        experiment_id: str,
        reason: str,
        clock_attestation: dict[str, Any],
    ) -> dict[str, Any]:
        require_runtime_writable(read_only=self.read_only, service="portfolio_experiment_registry")
        clean_id = str(experiment_id or "").strip()
        clean_reason = str(reason or "").strip()
        clock_verification = verify_trusted_clock_attestation(clock_attestation)
        blockers: list[str] = []
        if not clean_id:
            blockers.append("experiment_id_missing")
        if len(clean_reason) < 8:
            blockers.append("abort_reason_too_short")
        if clock_verification.get("status") != "PASS":
            blockers.extend(
                f"abort_clock:{item}"
                for item in clock_verification.get("blockers") or ["attestation_blocked"]
            )
        if blockers:
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": list(dict.fromkeys(blockers)),
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        aborted_at = int(clock_attestation.get("attested_now_ms") or 0)
        with self._lock, self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            audit = self._audit_connection(connection)
            if audit.get("status") != "PASS":
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": [f"registry_integrity:{item}" for item in audit.get("blockers") or []],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            row = connection.execute(
                "SELECT status FROM portfolio_experiments WHERE experiment_id = ?",
                (clean_id,),
            ).fetchone()
            if not row or str(row["status"] or "") not in {"REGISTERED", "RUNNING"}:
                return {
                    "ok": False,
                    "status": "BLOCK",
                    "blockers": ["experiment_not_abortable"],
                    "paper_authorized": False,
                    "live_order_allowed": False,
                }
            event = self._append_event(
                connection,
                experiment_id=clean_id,
                event_type="ABORTED",
                event_time=aborted_at,
                payload={
                    "reason": clean_reason,
                    "clock_attestation_hash": str(clock_attestation.get("attestation_hash") or ""),
                },
            )
            connection.execute(
                """
                UPDATE portfolio_experiments
                SET status = 'ABORTED', updated_at = ?
                WHERE experiment_id = ?
                """,
                (aborted_at, clean_id),
            )
        return {
            "ok": True,
            "status": "ABORTED",
            "experiment_id": clean_id,
            "event": event,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def get(self, experiment_id: str) -> dict[str, Any]:
        clean_id = str(experiment_id or "").strip()
        with self._lock, self._connect() as connection:
            audit = self._audit_connection(connection)
            row = connection.execute(
                "SELECT * FROM portfolio_experiments WHERE experiment_id = ?",
                (clean_id,),
            ).fetchone()
        if not row:
            return {
                "ok": False,
                "status": "NOT_FOUND",
                "experiment_id": clean_id,
                "registry_audit": audit,
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        try:
            intent = json.loads(str(row["intent_json"] or "{}"))
            binding = json.loads(str(row["binding_json"] or "{}"))
            completion = json.loads(str(row["completion_json"] or "{}"))
        except json.JSONDecodeError:
            intent = {}
            binding = {}
            completion = {}
        record_status = str(row["status"] or "")
        return {
            "ok": audit.get("status") == "PASS",
            "status": record_status if audit.get("status") == "PASS" else "BLOCK",
            "record_status": record_status,
            "experiment_id": clean_id,
            "intent": intent,
            "binding": binding,
            "completion": completion,
            "registry_audit": audit,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def audit(self) -> dict[str, Any]:
        with self._lock, self._connect() as connection:
            return self._audit_connection(connection)

    def summary(self, limit: int = 10) -> dict[str, Any]:
        clean_limit = max(1, min(int(limit or 10), 100))
        with self._lock, self._connect() as connection:
            audit = self._audit_connection(connection)
            counts = connection.execute(
                "SELECT status, COUNT(*) AS count FROM portfolio_experiments GROUP BY status"
            ).fetchall()
            rows = connection.execute(
                "SELECT * FROM portfolio_experiments ORDER BY created_at DESC, experiment_id DESC LIMIT ?",
                (clean_limit,),
            ).fetchall()
        experiments: list[dict[str, Any]] = []
        for row in rows:
            try:
                intent = json.loads(str(row["intent_json"] or "{}"))
            except json.JSONDecodeError:
                intent = {}
            try:
                binding = json.loads(str(row["binding_json"] or "{}"))
            except json.JSONDecodeError:
                binding = {}
            try:
                completion = json.loads(str(row["completion_json"] or "{}"))
            except json.JSONDecodeError:
                completion = {}
            protocol = intent.get("protocol") if isinstance(intent.get("protocol"), dict) else {}
            experiments.append({
                "experiment_id": str(row["experiment_id"] or ""),
                "status": str(row["status"] or ""),
                "research_generation": str(protocol.get("research_generation") or ""),
                "protocol_hash": str(row["protocol_hash"] or ""),
                "intent_hash": str(row["intent_hash"] or ""),
                "registered_at": int(intent.get("registered_at") or row["created_at"] or 0),
                "started_at": int(binding.get("started_at") or 0),
                "completed_at": int(completion.get("completed_at") or 0),
                "batch_run_hash": str(completion.get("batch_run_hash") or ""),
                "dataset_hash": str(completion.get("dataset_hash") or ""),
                "report_file": str(completion.get("report_file") or ""),
                "candidate_file": str(completion.get("candidate_file") or ""),
                "receipt_hash": str(completion.get("receipt_hash") or ""),
                "research_only": True,
                "paper_authorized": False,
                "live_order_allowed": False,
            })
        return {
            "schema_version": PORTFOLIO_EXPERIMENT_REGISTRY_VERSION,
            "status": audit.get("status"),
            "registry_audit": audit,
            "counts": {str(row["status"]): int(row["count"]) for row in counts},
            "experiments": experiments,
            "read_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
