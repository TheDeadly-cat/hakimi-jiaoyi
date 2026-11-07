"""Workspace-scoped navigation references; never a business operation or authority.

Reads do not create the preference database. Existing records are resolved through
the application's read interface. Failed/mismatched references remain visible.
"""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import stat

from .terminal_workspace_history import _no_links, _safe

SCHEMA = "hakimi-terminal-journey-v1"
PERMISSIONS = dict(research_only=True, order_allowed=False, live_allowed=False, paper_allowed=False)
OPAQUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,199}\Z")
MODES = {"OFFICIAL_SIMULATION", "LIVE_CANDIDATE"}


def _json(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":"), allow_nan=False)


def _require(value, code):
    if not value:
        raise ValueError("journey_" + code)


def _fields(value, names):
    _require(type(value) is dict and set(value) == set(names), "exact_fields_required")


def _id(value):
    _require(type(value) is str and OPAQUE.fullmatch(value), "opaque_identity_required")


def selection(value):
    _fields(value, {"task", "research", "view", "replay", "manual", "broker"})
    _require(value["view"] in {"results", "continuous", "execution", "broker"}, "view_invalid")
    for name, fields in (("task", {"kind", "id", "task_id"}), ("research", {"kind", "id"}),
                         ("replay", {"account_id"}), ("manual", {"account_id", "plan_id"}),
                         ("broker", {"mode", "config_id", "intent_id", "plan_id"})):
        node = value[name]
        if node is None:
            continue
        _fields(node, fields)
        for key, identity in node.items():
            if key in {"kind", "mode"} or key in {"plan_id", "intent_id"} and identity is None:
                continue
            _id(identity)
        if name in {"task", "research"}:
            _require(node["kind"] in ({"terminal_task", "core_task"} if name == "task" else {"terminal_run", "core_run"}), "reference_kind_invalid")
        if name == "broker":
            _require(node["mode"] in MODES and (node["plan_id"] is None or node["intent_id"] is not None), "broker_reference_invalid")
    _require(len(_json(value)) <= 4096, "selection_too_large")
    return deepcopy(value)


class TerminalJourneyService:
    def __init__(self, workspace, *, reader):
        _require(callable(reader), "reader_required")
        self.workspace = Path(workspace).absolute()
        _no_links(self.workspace)
        self.path = self.workspace / "ui" / "strategy-journey-v1.sqlite3"
        self.reader = reader
        self.context = sha256((SCHEMA + ":" + os.path.normcase(str(self.workspace.resolve()))).encode()).hexdigest()
        self.anchor = next(p for p in (self.workspace, *self.workspace.parents) if p.exists())
        info = self.anchor.stat()
        self.anchor_identity = (info.st_dev, info.st_ino)

    def _safe(self):
        _safe(self.workspace, self.path)
        info = self.anchor.stat()
        _require((info.st_dev, info.st_ino) == self.anchor_identity, "workspace_replaced")
        if self.path.exists():
            info = self.path.lstat()
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size <= 64 * 1048576, "store_invalid")
        for suffix in ("-wal", "-shm", "-journal"):
            _safe(self.workspace, Path(str(self.path) + suffix))

    def _connect(self, write=False):
        self._safe()
        if not self.path.exists() and not write:
            return None
        if write:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._safe()
        connection = sqlite3.connect(self.path.as_uri() + ("?mode=rwc" if write else "?mode=ro"), uri=True, timeout=5)
        try:
            if write:
                connection.execute("PRAGMA journal_mode=DELETE")
                connection.execute("PRAGMA synchronous=FULL")
                connection.execute("BEGIN IMMEDIATE")
                connection.execute("CREATE TABLE IF NOT EXISTS selection(singleton INTEGER PRIMARY KEY CHECK(singleton=1), context TEXT NOT NULL, revision INTEGER NOT NULL, body TEXT)")
                connection.execute("CREATE TABLE IF NOT EXISTS requests(id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, receipt TEXT NOT NULL)")
                connection.execute("INSERT OR IGNORE INTO selection VALUES(1,?,0,NULL)", (self.context,))
            row = connection.execute("SELECT context,revision,body FROM selection WHERE singleton=1").fetchone()
            _require(row is not None and row[0] == self.context and type(row[1]) is int and row[1] >= 0, "workspace_or_store_mismatch")
            if row[2] is not None:
                selection(json.loads(row[2]))
            return connection
        except BaseException:
            connection.close()
            raise

    def _base(self, revision, selected, **extra):
        return dict(schema_version=SCHEMA, workspace_context=self.context, revision=revision,
                    selection=deepcopy(selected), read_only=True, new_economic_runs=0,
                    external_calls=0, automatic_retry=False, permissions=dict(PERMISSIONS), **extra)

    def read(self):
        connection = self._connect()
        try:
            row = connection.execute("SELECT revision,body FROM selection WHERE singleton=1").fetchone() if connection else (0, None)
            selected = json.loads(row[1]) if row[1] else None
        finally:
            if connection:
                connection.close()
        return self._base(row[0], selected, status="SAVED" if selected else "EMPTY", resolution=self.resolve(selected))

    def save(self, payload):
        _fields(payload, {"request_id", "workspace_context", "expected_revision", "selection"})
        _require(payload["workspace_context"] == self.context, "workspace_context_mismatch")
        _id(payload["request_id"])
        _require(len(payload["request_id"]) >= 8, "request_id_invalid")
        _require(type(payload["expected_revision"]) is int and 0 <= payload["expected_revision"] <= 2**53-1, "revision_invalid")
        selected = selection(payload["selection"])
        fingerprint = sha256(_json(payload).encode()).hexdigest()
        connection = self._connect(write=True)
        try:
            old = connection.execute("SELECT fingerprint,receipt FROM requests WHERE id=?", (payload["request_id"],)).fetchone()
            if old:
                _require(old[0] == fingerprint, "request_id_payload_conflict")
                result = json.loads(old[1]); result["replayed"] = True
            else:
                revision, body = connection.execute("SELECT revision,body FROM selection WHERE singleton=1").fetchone()
                if revision != payload["expected_revision"]:
                    return self._base(revision, json.loads(body) if body else None, status="REVISION_CONFLICT", request_id=payload["request_id"], saved=False)
                _require(connection.execute("SELECT COUNT(*) FROM requests").fetchone()[0] < 10000, "request_capacity_reached")
                changed = body != _json(selected)
                revision += int(changed)
                if changed:
                    connection.execute("UPDATE selection SET revision=?,body=? WHERE singleton=1", (revision, _json(selected)))
                result = self._base(revision, selected, status="SAVED" if changed else "UNCHANGED", request_id=payload["request_id"], saved=True, replayed=False)
                result["read_only"] = False
                connection.execute("INSERT INTO requests VALUES(?,?,?)", (payload["request_id"], fingerprint, _json(result)))
            connection.commit()
            return result
        finally:
            connection.close()

    def _get(self, resource, payload=None, *, raw=False):
        value = self.reader(resource, payload if raw or payload is None else _json(payload))
        _require(type(value) is dict, "read_object_required")
        return value

    def resolve(self, selected):
        if selected is None:
            return {}
        result, binding = {}, None

        def record(name, read):
            if selected[name] is None:
                result[name] = dict(status="NOT_SELECTED", reference=None)
                return None
            try:
                data = read()
                result[name] = dict(status="VERIFIED", reference=deepcopy(selected[name]), data=data)
                return data
            except Exception as error:
                code = str(error)
                status = "BINDING_MISMATCH" if "mismatch" in code else "VERSION_CHANGED" if "version_changed" in code else "UNAVAILABLE"
                result[name] = dict(status=status, reference=deepcopy(selected[name]), diagnostic=code[:240], original_reference_retained=True)
                return None

        def research():
            value = self._get("terminal_execution_research", {"reference": selected["research"]})
            _require(value.get("reference") == selected["research"] and value.get("binding", {}).get("status") == "COMPLETED", "research_binding_mismatch")
            return value

        source = record("research", research)
        binding = source["binding"] if source else None

        def task():
            ref = selected["task"]
            value = self._get("terminal_tasks" if ref["kind"] == "terminal_task" else "tasks", ref["id"], raw=True)
            _require(value.get("task_id") == ref["task_id"], "task_version_changed")
            if binding:
                _require(binding.get("task_id") == ref["task_id"], "task_research_binding_mismatch")
            return value

        record("task", task)

        def replay():
            ref = selected["replay"]
            value = self._get("terminal_replay_status", ref)
            _require(value.get("account_id") == ref["account_id"], "replay_account_mismatch")
            _require(selected["research"] is not None and value.get("display_summary", {}).get("reference") == selected["research"], "replay_research_binding_mismatch")
            return value

        record("replay", replay)

        def manual():
            ref = selected["manual"]
            value = self._get("terminal_execution_account", ref["account_id"], raw=True)
            _require(value.get("account_id") == ref["account_id"], "manual_account_mismatch")
            if ref["plan_id"]:
                plan = next((p for p in value.get("ledger", {}).get("plans", []) if p.get("plan_id") == ref["plan_id"]), None)
                _require(plan is not None, "manual_plan_missing")
                _require(binding is not None, "research_binding_unavailable")
                _require(plan.get("research_binding") == binding, "manual_research_binding_mismatch")
            return value

        record("manual", manual)

        def broker():
            ref = selected["broker"]
            status = self._get("terminal_broker_status")
            mode = next((m for m in status.get("modes", []) if m.get("mode") == ref["mode"]), None)
            _require(mode is not None, "broker_mode_missing")
            config = next((c for c in mode.get("configurations", []) if c.get("config_id") == ref["config_id"]), None)
            _require(config is not None, "broker_config_missing")
            _require(selected["research"] is not None and config.get("research_reference") == selected["research"], "broker_research_binding_mismatch")
            _require(source is not None, "research_binding_unavailable")
            from .terminal_broker_candidate_service import _project_research
            projected = _project_research(source, selected["research"])
            _require(config.get("research_binding_sha256") == sha256(_json(projected).encode()).hexdigest(), "broker_source_hash_mismatch")
            intent = plan = None
            if ref["intent_id"]:
                records = self._get("terminal_broker_receipts", ref["mode"], raw=True)
                intent = next((r.get("result", {}).get("intent") for r in records.get("items", []) if r.get("result", {}).get("intent", {}).get("id") == ref["intent_id"]), None)
                _require(intent is not None, "broker_intent_missing")
                _require(intent.get("mode") == ref["mode"] and intent.get("config_id") == ref["config_id"] and intent.get("research_sha256") == config.get("research_binding_sha256"), "broker_intent_binding_mismatch")
            if ref["plan_id"]:
                value = self._get("terminal_broker_plan", {"mode": ref["mode"], "plan_id": ref["plan_id"]})
                plan = value.get("plan")
                _require(value.get("status") == "FOUND" and type(plan) is dict and plan.get("id") == ref["plan_id"], "broker_plan_missing")
                resolution = plan.get("research", {}).get("resolution", {})
                _require(binding is not None, "research_binding_unavailable")
                _require(plan.get("mode") == ref["mode"] and plan.get("candidate_config", {}).get("id") == ref["config_id"] and plan.get("candidate_intent", {}).get("id") == ref["intent_id"] and resolution == projected, "broker_plan_binding_mismatch")
            return dict(mode=ref["mode"], configuration=config, intent=intent, plan=plan, connected=False, read_only=True)

        record("broker", broker)
        return result
