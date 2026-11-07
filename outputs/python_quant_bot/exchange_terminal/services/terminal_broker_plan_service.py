"""Persist offline acceptance plans, never dispatch an external action.

Only trusted callbacks load package identity and saved research. Renderer input
is six bounded fields. A durable PREPARING claim is never retried or resumed;
old receipt reads need neither the current package nor the current research.
The plan database owns the atomic plan/receipt commit. Candidate control is a
short publication barrier, acquired AFTER the plan database writer lock.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat

from . import terminal_broker_candidate_service as candidate
from . import terminal_broker_execution_plan as contract
from .terminal_broker_package_loader import BrokerRuntimeLoad, PackageLoaderError

SCHEMA = "hakimi-broker-plan-service-v1"
STORE_SCHEMA = "hakimi-broker-plan-store-v1"
CLAIM_SCHEMA = "hakimi-broker-plan-claim-v1"
RECEIPT_SCHEMA = "hakimi-broker-plan-receipt-v1"
ACTION = "terminal_broker_prepare_plan"
READ_RESOURCES = frozenset({"terminal_broker_plan_capabilities", "terminal_broker_plans",
                            "terminal_broker_plan", "terminal_broker_plan_receipt"})
PAYLOAD_FIELDS = frozenset({"mode", "request_id", "config_id", "intent_id", "expected_control_revision", "bounds"})
MAX_RECORDS = 1000
PERMISSIONS = dict(contract.PERMISSIONS)


class BrokerPlanError(ValueError):
    pass


def _require(condition, message):
    if not condition:
        raise BrokerPlanError(message)


def _bytes(value):
    return contract.canonical_bytes(value)


def _seal(value):
    return {**value, "id": contract.digest(value)}


def _fields(value, required):
    _require(type(value) is dict and set(value) == set(required), "broker_plan_fields_invalid")


def _mode(value):
    _require(type(value) is str and value in candidate.MODES, "broker_plan_mode_required")
    return value


def _request_id(value):
    _require(type(value) is str and candidate.REQUEST.fullmatch(value) is not None, "broker_plan_request_id_invalid")
    return value


def _payload(value):
    _fields(value, PAYLOAD_FIELDS)
    _mode(value["mode"]); _request_id(value["request_id"])
    contract._hash(value["config_id"]); contract._hash(value["intent_id"])
    contract._integer(value["expected_control_revision"], 0, candidate.MAX_RECORDS)
    _require(type(value["bounds"]) is dict and len(_bytes(value)) <= 16384, "broker_plan_bounds_invalid")
    return deepcopy(value)


def _decode(raw):
    _require(type(raw) is bytes and 0 < len(raw) <= contract.MAX_DOCUMENT_BYTES, "broker_plan_record_size_invalid")
    value = contract._json_document(raw, contract.MAX_DOCUMENT_BYTES)
    _require(_bytes(value) == raw and value.get("id") == contract.digest({k: v for k, v in value.items() if k != "id"}),
             "broker_plan_record_changed")
    return value


class BrokerPlanService:
    def __init__(self, workspace, *, candidates, research_resolver, runtime_loader, clock=None):
        _require(callable(research_resolver) and callable(runtime_loader), "broker_plan_trusted_callbacks_required")
        workspace = Path(workspace).absolute()
        self.root = workspace / "broker-plans-v1"
        self._safe(self.root)  # Reject existing aliases before resolving paths.
        workspace = workspace.resolve()
        self.root = workspace / "broker-plans-v1"
        self.workspace_context = sha256((STORE_SCHEMA + ":" + os.path.normcase(str(workspace))).encode()).hexdigest()
        self.candidates = candidates
        self._resolver, self._loader = research_resolver, runtime_loader
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._closed = False
        self._safe(self.root)

    def close(self):
        # Every operation uses a bounded connection context; nothing is resumed,
        # repaired or reclassified when the normal service lifetime ends.
        self._closed = True

    def _safe(self, path):
        path = Path(path).absolute()
        _require(path == self.root or path.is_relative_to(self.root), "broker_plan_path_outside_store")
        for item in (path, *path.parents):
            try:
                info = item.lstat()
            except FileNotFoundError:
                continue
            _require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                     "broker_plan_reparse_path_rejected")
        return path

    def _now(self):
        return contract._now(self._clock())

    def _path(self, mode):
        return self._safe(self.root / candidate.MODES[_mode(mode)] / "plans.sqlite3")

    def _meta(self, mode):
        return _seal({"schema_version": STORE_SCHEMA, "mode": mode, "workspace_context": self.workspace_context,
                      "permissions": dict(PERMISSIONS)})

    def _check_store_file(self, path):
        """Reject unsupported WAL/aliased stores BEFORE SQLite can open them.

        Read-only SQLite may create coordination files for WAL databases. This
        new v1 store deliberately supports DELETE journal format only; do not
        use immutable=1 to conceal pending WAL contents or perform recovery.
        """
        self._safe(path)
        before = path.lstat()
        signature = lambda info: (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_nlink)
        _require(stat.S_ISREG(before.st_mode) and before.st_nlink == 1, "broker_plan_unaliased_regular_store_required")
        for suffix in ("-wal", "-shm"):
            _require(not os.path.lexists(str(path) + suffix), "broker_plan_wal_store_unsupported")
        with path.open("rb") as stream:
            _require(signature(os.fstat(stream.fileno())) == signature(before), "broker_plan_store_replaced_before_read")
            header = stream.read(100)
            after = os.fstat(stream.fileno())
        self._safe(path)
        _require(signature(before) == signature(after) == signature(path.lstat()), "broker_plan_store_changed_during_read")
        _require(len(header) == 100 and header[:16] == b"SQLite format 3\x00" and header[18:20] == b"\x01\x01",
                 "broker_plan_delete_journal_store_required")

    def _create_store(self, mode, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._safe(path.with_name(".plans." + secrets.token_hex(8) + ".pending"))
        connection = sqlite3.connect(str(temporary))
        try:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("CREATE TABLE metadata (singleton INTEGER PRIMARY KEY CHECK(singleton=1), body BLOB NOT NULL)")
            connection.execute("CREATE TABLE requests (request_id TEXT PRIMARY KEY, request_hash TEXT NOT NULL, "
                               "state TEXT NOT NULL, claim BLOB NOT NULL, receipt BLOB, plan_id TEXT)")
            connection.execute("CREATE TABLE plans (plan_id TEXT PRIMARY KEY, body BLOB NOT NULL)")
            connection.execute("INSERT INTO metadata VALUES(1,?)", (_bytes(self._meta(mode)),))
            connection.commit()
        finally:
            connection.close()
        try:
            try:
                os.link(temporary, path)
            except FileExistsError:
                pass  # Another instance published the complete empty schema.
        finally:
            temporary.unlink(missing_ok=True)

    @contextmanager
    def _database(self, mode, *, write=False):
        _require(not self._closed, "broker_plan_service_closed")
        path = self._path(mode)
        if not path.exists():
            if not write:
                yield None
                return
            self._create_store(mode, path)
        self._check_store_file(path)
        connection = sqlite3.connect(str(path) if write else path.as_uri() + "?mode=ro",
                                     uri=not write, isolation_level=None, timeout=2)
        try:
            if write:
                connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            rows = connection.execute("SELECT singleton,body FROM metadata").fetchall()
            _require(len(rows) == 1 and rows[0][0] == 1 and rows[0][1] == _bytes(self._meta(mode)),
                     "broker_plan_store_context_changed")
            for table in ("requests", "plans"):
                _require(connection.execute("SELECT COUNT(*) FROM " + table).fetchone()[0] <= MAX_RECORDS,
                         "broker_plan_store_capacity_invalid")
            yield connection
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    def _base(self, mode, **fields):
        return {"schema_version": SCHEMA, "workspace_context": self.workspace_context, "mode": mode,
                **fields, "permissions": dict(PERMISSIONS), "automatic_retry": False}

    def _plan_document(self, connection, mode, identity):
        contract._hash(identity)
        row = connection.execute("SELECT body FROM plans WHERE plan_id=?", (identity,)).fetchone() if connection else None
        if row is None:
            return None
        plan = _decode(row[0])
        _require(plan.get("schema_version") == contract.SCHEMA and plan.get("id") == identity and plan.get("mode") == mode
                 and _bytes(plan.get("permissions")) == _bytes(PERMISSIONS)
                 and (plan.get("sdk_environment"), plan.get("contract_id")) == contract.MODE_CONTRACTS[mode],
                 "broker_plan_saved_identity_changed")
        return plan

    def _row(self, connection, mode, request_id):
        if connection is None:
            return None
        row = connection.execute("SELECT request_id,request_hash,state,claim,receipt,plan_id FROM requests WHERE request_id=?",
                                 (request_id,)).fetchone()
        if row is None:
            return None
        identity, fingerprint, state, raw_claim, raw_receipt, plan_id = row
        claim = _decode(raw_claim)
        _fields(claim, {"schema_version", "action", "mode", "workspace_context", "request_id", "request_hash",
                        "payload", "created_at", "permissions", "id"})
        payload = _payload(claim["payload"])
        expected_hash = contract.digest({"action": ACTION, "payload": payload})
        _require(claim["schema_version"] == CLAIM_SCHEMA and claim["action"] == ACTION and claim["mode"] == mode
                 and claim["workspace_context"] == self.workspace_context and claim["request_id"] == identity == request_id
                 and payload["mode"] == mode and payload["request_id"] == request_id
                 and claim["request_hash"] == fingerprint == expected_hash
                 and _bytes(claim["permissions"]) == _bytes(PERMISSIONS), "broker_plan_claim_changed")
        contract._time(claim["created_at"])
        if state == "PREPARING":
            _require(raw_receipt is None and plan_id is None, "broker_plan_preparing_row_changed")
            return {"claim": claim, "receipt": None, "state": state, "plan_id": None}
        _require(state in {"COMPLETED", "REFUSED"} and raw_receipt is not None, "broker_plan_request_state_changed")
        receipt = _decode(raw_receipt)
        _fields(receipt, {"schema_version", "action", "mode", "workspace_context", "request_id", "request_hash", "payload",
                          "claim_id", "created_at", "result", "permissions", "id"})
        _require(receipt["schema_version"] == RECEIPT_SCHEMA and receipt["action"] == ACTION and receipt["mode"] == mode
                 and receipt["workspace_context"] == self.workspace_context and receipt["request_id"] == request_id
                 and receipt["request_hash"] == fingerprint and receipt["claim_id"] == claim["id"]
                 and _bytes(receipt["payload"]) == _bytes(payload)
                 and _bytes(receipt["permissions"]) == _bytes(PERMISSIONS), "broker_plan_receipt_envelope_changed")
        contract._time(receipt["created_at"])
        result = receipt["result"]
        _fields(result, {"mode", "request_id", "config_id", "intent_id", "status", "plan_id", "plan_status", "reason", "permissions"})
        _require(all(result[key] == payload[key] for key in ("mode", "request_id", "config_id", "intent_id"))
                 and result["plan_id"] == plan_id and _bytes(result["permissions"]) == _bytes(PERMISSIONS),
                 "broker_plan_receipt_result_changed")
        if state == "COMPLETED":
            _require(result["status"] == "PLAN_SAVED" and result["reason"] is None, "broker_plan_saved_result_changed")
            plan = self._plan_document(connection, mode, plan_id)
            _require(plan is not None and result["plan_status"] == plan["status"]
                     and plan["candidate_config"]["id"] == payload["config_id"]
                     and plan["candidate_intent"]["id"] == payload["intent_id"]
                     and _bytes(plan["bounds"]) == _bytes(payload["bounds"])
                     and plan["control"]["control"]["revision"] == payload["expected_control_revision"],
                     "broker_plan_receipt_plan_changed")
        else:
            _require(result["status"] == "PLAN_NOT_CREATED" and plan_id is None and result["plan_status"] is None
                     and type(result["reason"]) is str and 0 < len(result["reason"]) <= 500,
                     "broker_plan_refusal_changed")
        return {"claim": claim, "receipt": receipt, "state": state, "plan_id": plan_id}

    def _view(self, mode, request_id, row, *, mutation=False):
        if row is None:
            return self._base(mode, status="NOT_RECORDED", request_id=request_id, result=None, claim=None, receipt=None,
                              retry_allowed=False, read_only=True)
        receipt = row["receipt"]
        status = (receipt["result"]["status"] if mutation else "FOUND") if receipt else "PREPARING_UNCONFIRMED"
        return self._base(mode, status=status, request_id=request_id, result=deepcopy(receipt["result"]) if receipt else None,
                          claim=deepcopy(row["claim"]), receipt=deepcopy(receipt), retry_allowed=False, read_only=not mutation)

    def _claim(self, payload):
        mode, request_id = payload["mode"], payload["request_id"]
        fingerprint = contract.digest({"action": ACTION, "payload": payload})
        with self._database(mode, write=True) as connection:
            existing = self._row(connection, mode, request_id)
            if existing is not None:
                _require(existing["claim"]["request_hash"] == fingerprint, "broker_plan_request_payload_conflict")
                return existing, False
            _require(connection.execute("SELECT COUNT(*) FROM requests").fetchone()[0] < MAX_RECORDS,
                     "broker_plan_request_capacity_exceeded")
            claim = _seal({"schema_version": CLAIM_SCHEMA, "action": ACTION, "mode": mode,
                           "workspace_context": self.workspace_context, "request_id": request_id, "request_hash": fingerprint,
                           "payload": deepcopy(payload), "created_at": self._now().isoformat(), "permissions": dict(PERMISSIONS)})
            connection.execute("INSERT INTO requests VALUES(?,?,?,?,NULL,NULL)",
                               (request_id, fingerprint, "PREPARING", _bytes(claim)))
            connection.commit()
        return {"claim": claim, "receipt": None, "state": "PREPARING", "plan_id": None}, True

    def _receipt(self, claim, plan=None, reason=None):
        payload = claim["payload"]
        result = {**{key: payload[key] for key in ("mode", "request_id", "config_id", "intent_id")},
                  "status": "PLAN_SAVED" if plan is not None else "PLAN_NOT_CREATED", "plan_id": plan["id"] if plan else None,
                  "plan_status": plan["status"] if plan else None, "reason": reason, "permissions": dict(PERMISSIONS)}
        return _seal({"schema_version": RECEIPT_SCHEMA, "action": ACTION, "mode": payload["mode"],
                      "workspace_context": self.workspace_context, "request_id": payload["request_id"], "request_hash": claim["request_hash"],
                      "payload": deepcopy(payload), "claim_id": claim["id"], "created_at": self._now().isoformat(),
                      "result": result, "permissions": dict(PERMISSIONS)})

    def _write_final(self, connection, claim, receipt, plan=None):
        if plan is not None:
            existing = connection.execute("SELECT body FROM plans WHERE plan_id=?", (plan["id"],)).fetchone()
            if existing:
                _require(existing[0] == _bytes(plan), "broker_plan_content_conflict")
            else:
                _require(connection.execute("SELECT COUNT(*) FROM plans").fetchone()[0] < MAX_RECORDS, "broker_plan_capacity_exceeded")
                connection.execute("INSERT INTO plans VALUES(?,?)", (plan["id"], _bytes(plan)))
        changed = connection.execute("UPDATE requests SET state=?,receipt=?,plan_id=? WHERE request_id=? AND state='PREPARING' AND request_hash=?",
            ("COMPLETED" if plan else "REFUSED", _bytes(receipt), plan["id"] if plan else None,
             claim["request_id"], claim["request_hash"])).rowcount
        _require(changed == 1, "broker_plan_claim_changed_before_commit")
        connection.commit()  # The only final publication point: plan + receipt.

    def _refuse(self, claim, reason):
        mode, identity = claim["mode"], claim["request_id"]
        with self._database(mode, write=True) as connection:
            row = self._row(connection, mode, identity)
            _require(row is not None and row["claim"]["id"] == claim["id"], "broker_plan_claim_missing")
            if row["receipt"] is not None:
                return self._view(mode, identity, row, mutation=True)
            receipt = self._receipt(claim, reason=str(reason)[:500])
            self._write_final(connection, claim, receipt)
        return self._view(mode, identity, {"claim": claim, "receipt": receipt}, mutation=True)

    def _runtime(self, mode):
        loaded = self._loader(mode)
        _require(type(loaded) is BrokerRuntimeLoad and loaded.mode == mode, "broker_plan_trusted_runtime_load_required")
        _require((loaded.status == "NOT_PACKAGED" and loaded.runtime_identity is None)
                 or (loaded.status == "PACKAGED_IDENTITY_MATCHED" and type(loaded.runtime_identity) is contract.VerifiedRuntimeIdentity),
                 "broker_plan_runtime_status_invalid")
        return loaded

    def _recover_mutation(self, mode, request_id):
        with self._database(mode) as connection:
            row = self._row(connection, mode, request_id)
        return self._view(mode, request_id, row, mutation=True)

    def prepare(self, value):
        payload = _payload(value)
        mode, identity = payload["mode"], payload["request_id"]
        # Existing requests use only retained bytes, even if today's package or
        # research is unavailable. PREPARING never restarts the slow callbacks.
        with self._database(mode) as connection:
            existing = self._row(connection, mode, identity)
        if existing:
            _require(existing["claim"]["request_hash"] == contract.digest({"action": ACTION, "payload": payload}),
                     "broker_plan_request_payload_conflict")
            return self._view(mode, identity, existing, mutation=True)
        row, claimed = self._claim(payload)
        if not claimed:
            return self._view(mode, identity, row, mutation=True)
        claim = row["claim"]
        try:
            initial_control = self.candidates.read_plan_control(mode)
            _require(initial_control["control"]["revision"] == payload["expected_control_revision"]
                     and initial_control["control"]["new_intents_blocked"] is False, "candidate_plan_control_changed_or_stopped")
            saved, intent = self.candidates.read_plan_records(mode, payload["config_id"], payload["intent_id"])
            research = self._resolver(deepcopy(saved["research"]["reference"]))
            # Last original read is outside both database write locks and the
            # stop barrier. Immutable IDs must still name precisely these bytes.
            current_saved, current_intent = self.candidates.read_plan_records(mode, payload["config_id"], payload["intent_id"])
            _require(_bytes(current_saved) == _bytes(saved) and _bytes(current_intent) == _bytes(intent), "broker_plan_originals_changed")
            # The unique fresh package read comes AFTER the potentially slow
            # resolver/original reads, never under the stop publication lock.
            loaded = self._runtime(mode)
            if loaded.status == "NOT_PACKAGED":
                return self._refuse(claim, "NOT_PACKAGED")
            plan = contract.prepare_acceptance_plan(candidate_config=saved, candidate_intent=intent,
                research_resolution=research, runtime_identity=loaded.runtime_identity, control=initial_control,
                bounds=payload["bounds"], now=self._now())
        except (ValueError, OSError) as error:
            return self._refuse(claim, getattr(error, "code", None) or str(error) or type(error).__name__)

        committed_receipt = None
        try:
            # Waiting for the plan writer happens before acquiring the control
            # writer. Stop bypasses this store and all preparation callbacks.
            with self._database(mode, write=True) as connection:
                current = self._row(connection, mode, identity)
                _require(current is not None and current["claim"]["id"] == claim["id"], "broker_plan_claim_changed")
                if current["receipt"]:
                    return self._view(mode, identity, current, mutation=True)
                with self.candidates.plan_commit_barrier(mode, payload["expected_control_revision"]) as control:
                    _require(_bytes(control) == _bytes(initial_control), "broker_plan_control_changed")
                    contract._bounds(plan["bounds"], self._now(), contract._time(plan["order"]["expires_at"]))
                    receipt = self._receipt(claim, plan=plan)
                    self._write_final(connection, claim, receipt, plan)
                    committed_receipt = receipt
        except (candidate.CandidateError, contract.PlanError, BrokerPlanError) as error:
            if committed_receipt is None:
                return self._refuse(claim, str(error))
        except Exception:
            if committed_receipt is None:
                # Commit result may be unknown. Read the original operation;
                # never classify an uncertain write as a safe new attempt.
                return self._recover_mutation(mode, identity)
        if committed_receipt is not None:
            return self._view(mode, identity, {"claim": claim, "receipt": committed_receipt}, mutation=True)
        return self._recover_mutation(mode, identity)

    def receipt(self, mode, request_id):
        _mode(mode); _request_id(request_id)
        with self._database(mode) as connection:
            row = self._row(connection, mode, request_id)
        return self._view(mode, request_id, row)

    def plans(self, mode):
        _mode(mode)
        items, requests = [], []
        with self._database(mode) as connection:
            if connection is not None:
                seen = set()
                for (identity,) in connection.execute("SELECT request_id FROM requests ORDER BY request_id"):
                    row = self._row(connection, mode, identity)
                    claim, receipt = row["claim"], row["receipt"]
                    result = receipt["result"] if receipt else {}
                    requests.append({"request_id": identity, "request_hash": claim["request_hash"], "state": row["state"],
                        "status": result.get("status", "PREPARING_UNCONFIRMED"), "plan_id": row["plan_id"],
                        "config_id": claim["payload"]["config_id"], "intent_id": claim["payload"]["intent_id"],
                        "created_at": claim["created_at"], "reason": result.get("reason")})
                    if row["plan_id"] and row["plan_id"] not in seen:
                        plan = self._plan_document(connection, mode, row["plan_id"]); seen.add(row["plan_id"])
                        research = plan["research"]["resolution"]
                        items.append({"plan_id": plan["id"], "status": plan["status"], "created_at": plan["created_at"],
                            "config_id": plan["candidate_config"]["id"], "intent_id": plan["candidate_intent"]["id"],
                            "account_id": plan["order"]["account_id"], "symbol": research["display"]["symbol"],
                            "strategy_id": research["binding"]["strategy_id"], "task_version": research["binding"]["task_version"],
                            "research_eligibility": deepcopy(plan["research_eligibility"])})
                _require(len(seen) == connection.execute("SELECT COUNT(*) FROM plans").fetchone()[0], "broker_plan_orphan_record")
        return self._base(mode, items=items, requests=requests, read_only=True, retry_allowed=False)

    def read(self, resource, payload):
        _require(resource in READ_RESOURCES, "broker_plan_read_resource_unsupported")
        fields = {"mode"} | ({"plan_id"} if resource == "terminal_broker_plan" else
                              {"request_id"} if resource == "terminal_broker_plan_receipt" else set())
        _fields(payload, fields); mode = _mode(payload["mode"])
        if resource == "terminal_broker_plan_capabilities":
            _require(not self._closed, "broker_plan_service_closed")
            loaded = self._runtime(mode)
            return self._base(mode, status=loaded.status, runtime=loaded.as_dict(), read_only=True)
        if resource == "terminal_broker_plans":
            return self.plans(mode)
        if resource == "terminal_broker_plan_receipt":
            return self.receipt(mode, payload["request_id"])
        contract._hash(payload["plan_id"])
        with self._database(mode) as connection:
            plan = self._plan_document(connection, mode, payload["plan_id"])
            if plan is not None:
                owner = connection.execute("SELECT request_id FROM requests WHERE plan_id=? AND state='COMPLETED' LIMIT 1", (plan["id"],)).fetchone()
                _require(owner is not None, "broker_plan_orphan_record")
                self._row(connection, mode, owner[0])
        return self._base(mode, status="FOUND" if plan else "NOT_RECORDED", plan=plan, read_only=True, retry_allowed=False)

    def mutate(self, action, payload):
        _require(action == ACTION, "broker_plan_action_unsupported")
        return self.prepare(payload)
