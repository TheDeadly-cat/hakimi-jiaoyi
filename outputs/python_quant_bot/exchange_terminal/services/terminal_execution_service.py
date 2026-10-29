"""Current-workspace access to new, explicitly synthetic execution accounts.

The resolver is trusted application code and must verify a saved native/core run.
Clients provide only its kind/id reference, never completion/engine/hash/owner
assertions. This adapter owns no broker, source reader, model or old-account import.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import secrets
import stat
from threading import RLock

from .execution_authority import canonical_authority_key, EXECUTION_AUTHORITY_FIELD_KEYS
from .offline_execution import (OfflineExecutionStore, PERMISSIONS, SCHEMA, BINDING_SCHEMA,
                                compare_research_context, _binding)


VIEW_SCHEMA = "hakimi-terminal-execution-view-v1"
MANIFEST_SCHEMA = "hakimi-terminal-execution-account-v1"
READ_RESOURCES = frozenset({"terminal_execution_accounts", "terminal_execution_account",
                            "terminal_execution_receipt", "terminal_execution_history", "terminal_execution_compare",
                            "terminal_execution_research"})
MUTATION_ACTIONS = frozenset({"terminal_execution_create_account", "terminal_execution_create_plan",
    "terminal_execution_submit", "terminal_execution_observe", "terminal_execution_cancel",
    "terminal_execution_mark_quotes", "terminal_execution_reconcile", "terminal_execution_stop", "terminal_execution_resume"})
_ACCOUNT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}\Z")
_REQUEST = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{7,119}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_EXTERNAL_KEYS = EXECUTION_AUTHORITY_FIELD_KEYS | frozenset(map(canonical_authority_key, (
    "paper_allowed", "live_allowed", "external_order_allowed", "broker_connection_allowed", "model_calls_allowed")))


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _copy(value):
    return json.loads(_json(value))


def _hash(value):
    return sha256(_json(value).encode()).hexdigest()


def _fields(value, required, optional=()):
    if type(value) is not dict or set(required) - value.keys() or value.keys() - set(required) - set(optional):
        raise ValueError("terminal_execution_fields_invalid")


def _text(value, maximum=200):
    if type(value) is not str or not value.strip() or len(value) > maximum or "\0" in value:
        raise ValueError("terminal_execution_text_invalid")
    return value


def _key(value, pattern, name):
    if type(value) is not str or not pattern.fullmatch(value):
        raise ValueError("terminal_execution_" + name + "_invalid")
    return value


def _no_authority(value):
    if type(value) is dict:
        for key, item in value.items():
            if canonical_authority_key(key) in _EXTERNAL_KEYS and item is not False:
                raise ValueError("terminal_execution_external_authority_rejected")
            _no_authority(item)
    elif type(value) is list:
        for item in value:
            _no_authority(item)


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("terminal_execution_duplicate_json_field")
        result[key] = value
    return result


class TerminalExecutionService:
    def __init__(self, workspace, resolve_research):
        if not callable(resolve_research):
            raise ValueError("terminal_execution_resolver_required")
        self.workspace = Path(workspace).absolute()
        self.directory = self.workspace / "offline-execution"
        self.resolve_research = resolve_research
        self._lock = RLock()
        self._stores = {}
        self._closed = False
        self._workspace_identity = None
        self._safe(self.workspace)

    @staticmethod
    def _identity(path):
        info = path.stat()
        return (info.st_dev, info.st_ino)

    def _safe(self, path):
        path = Path(path).absolute()
        if path != self.workspace and not path.is_relative_to(self.workspace):
            raise ValueError("terminal_execution_path_outside_current_workspace")
        for candidate in (path, *path.parents):
            try:
                info = candidate.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
                raise ValueError("terminal_execution_link_path_rejected")
        if self.workspace.exists():
            identity = self._identity(self.workspace)
            if self._workspace_identity is None:
                self._workspace_identity = identity
            elif identity != self._workspace_identity:
                raise ValueError("terminal_execution_stale_workspace_context")
        return path

    def _active(self):
        if self._closed:
            raise ValueError("terminal_execution_service_closed")
        self._safe(self.workspace)

    def _folder(self, account_id):
        return self._safe(self.directory / _key(account_id, _ACCOUNT, "account_id"))

    def _read_json(self, path):
        path = self._safe(path)
        if not path.is_file() or path.stat().st_size > 512000:
            raise ValueError("terminal_execution_record_missing_or_too_large")
        value = json.loads(path.read_bytes(), object_pairs_hook=_pairs)
        return _copy(value)

    def _write_new(self, path, value):
        path = self._safe(path)
        with path.open("xb") as output:
            output.write(_json(value).encode())
            output.flush()
            os.fsync(output.fileno())

    def _manifest(self, account_id):
        folder = self._folder(account_id)
        manifest = self._read_json(folder / "account.json")
        required = {"schema_version", "account_id", "label", "created_at", "creation_id", "request_id",
                    "creation_request_hash", "config_hash", "evidence_kind", "database", "permissions"}
        _fields(manifest, required)
        if (manifest["schema_version"] != MANIFEST_SCHEMA or manifest["account_id"] != account_id
                or manifest["database"] != "account.sqlite" or manifest["evidence_kind"] != "SYNTHETIC_TEST"
                or manifest["permissions"] != PERMISSIONS or type(manifest["config_hash"]) is not str
                or not _HASH.fullmatch(manifest["config_hash"])):
            raise ValueError("terminal_execution_managed_account_manifest_invalid")
        intent = self._read_json(folder / "creation-intent.json")
        if (intent.get("schema_version") != "hakimi-terminal-execution-create-v1" or intent.get("creation_id") != manifest["creation_id"]
                or intent.get("request_id") != manifest["request_id"] or intent.get("request_hash") != manifest["creation_request_hash"]
                or _hash(intent.get("request")) != manifest["creation_request_hash"]):
            raise ValueError("terminal_execution_creation_identity_mismatch")
        return manifest

    def _entry(self, account_id, context=None):
        if context is not None and account_id not in self._stores:
            raise ValueError("terminal_execution_stale_account_context")
        manifest = self._manifest(account_id)
        folder = self._folder(account_id)
        path = self._safe(folder / "account.sqlite")
        if not path.is_file():
            raise ValueError("terminal_execution_account_database_missing")
        entry = self._stores.get(account_id)
        identity = (self._identity(folder), self._identity(path))
        if entry is None:
            store = OfflineExecutionStore.open(path, account_id=account_id)
            if _hash(store.config) != manifest["config_hash"]:
                store.close()
                raise ValueError("terminal_execution_account_config_mismatch")
            entry = dict(store=store, manifest=manifest, identity=identity,
                         context=secrets.token_urlsafe(32), head=None)
            self._stores[account_id] = entry
        elif entry["identity"] != identity or entry["manifest"] != manifest:
            raise ValueError("terminal_execution_stale_account_context")
        if entry["head"] is not None:
            sequence, expected = entry["head"]
            with entry["store"]._lock:
                row = entry["store"].db.execute("SELECT event_hash FROM events WHERE sequence=?", (sequence,)).fetchone()
            if row is None or row[0] != expected:
                raise ValueError("terminal_execution_account_history_replaced")
        if context is not None and (type(context) is not str or not secrets.compare_digest(context, entry["context"])):
            raise ValueError("terminal_execution_stale_account_context")
        return entry

    def _view(self, account_id, entry):
        snapshot = entry["store"].snapshot()
        latest = entry["store"].history(1)
        if latest:
            entry["head"] = (latest[0]["sequence"], latest[0]["event_hash"])
        unknown = sum(row["state"] == "TIMEOUT_UNCONFIRMED" for row in snapshot["orders"])
        deficiencies = deepcopy(snapshot["account_deficits"])
        if unknown:
            deficiencies.append({"kind": "UNCONFIRMED_ORDERS", "count": unknown})
        if snapshot["reconciliation_required"]:
            deficiencies.append({"kind": "EXPLICIT_RECONCILIATION_REQUIRED"})
        status = ("ACCOUNT_DEFICIT" if snapshot["account_deficits"] else "OUTCOME_UNCONFIRMED" if unknown
                  else "RECONCILIATION_REQUIRED" if snapshot["reconciliation_required"] else "PAUSED" if snapshot["stop_reason"]
                  else "READY_FOR_SYNTHETIC_EXECUTION")
        value = dict(view_schema_version=VIEW_SCHEMA, account_id=account_id, account_context=entry["context"],
                     creation_request_id=entry["manifest"]["request_id"],
                     label=entry["manifest"]["label"], status=status, paused=bool(snapshot["stop_reason"]),
                     reconciliation_required=snapshot["reconciliation_required"], deficiencies=deficiencies,
                     ledger=snapshot, permissions=dict(PERMISSIONS), external_calls=0)
        links = []
        for plan in snapshot["plans"]:
            link_path = self._folder(account_id) / "plan-links" / (plan["plan_id"] + ".json")
            if link_path.exists():
                link = self._read_json(link_path)
                _fields(link, {"schema_version", "plan_id", "reference", "binding_hash", "scoped_owner_id", "owner_source", "owner_continuity"})
                self._reference(link["reference"])
                source_owner = _text(link["owner_source"], 240)
                continuity = ("VERIFIED_TASK_FAMILY" if source_owner.startswith("family:") and source_owner[7:].strip()
                              else "IMMUTABLE_TASK_ONLY_NO_CROSS_VERSION_CONTINUITY" if source_owner == "task:"+plan["research_binding"]["task_id"] else None)
                owner = _hash(dict(account_id=account_id, engine_id=plan["research_binding"]["engine_id"], owner=source_owner))
                if (link.get("plan_id") != plan["plan_id"] or link.get("binding_hash") != plan["binding_hash"]
                        or link.get("scoped_owner_id") != plan["owner_id"] or owner != plan["owner_id"]
                        or continuity is None or continuity != link["owner_continuity"]
                        or link["schema_version"] != "hakimi-terminal-execution-plan-link-v1"):
                    raise ValueError("terminal_execution_plan_link_mismatch")
                links.append(link)
            else:
                links.append(dict(plan_id=plan["plan_id"], owner_continuity="UNKNOWN", status="DISPLAY_LINK_NOT_RECORDED"))
        value["plan_links"] = links
        _no_authority(value)
        return value

    def _reference(self, value):
        _fields(value, {"kind", "id"})
        if type(value["kind"]) is not str or value["kind"] not in {"terminal_run", "core_run"}:
            raise ValueError("terminal_execution_saved_run_reference_required")
        _text(value["id"])
        return _copy(value)

    def _resolve(self, reference):
        reference = self._reference(reference)
        resolved = _copy(self.resolve_research(deepcopy(reference)))
        _fields(resolved, {"binding", "owner_id"}, {"assumptions", "display"})
        binding = _binding(resolved["binding"])
        _no_authority(binding)
        owner = _text(resolved["owner_id"], 240)
        if owner.startswith("family:") and owner[7:].strip():
            continuity = "VERIFIED_TASK_FAMILY"
        elif owner == "task:" + binding["task_id"]:
            continuity = "IMMUTABLE_TASK_ONLY_NO_CROSS_VERSION_CONTINUITY"
        else:
            raise ValueError("terminal_execution_verified_owner_identity_required")
        assumptions = resolved.get("assumptions", {})
        # The pure comparator also validates the assumptions allowlist.
        compare_research_context(binding, {"research_binding": binding}, assumptions)
        display = resolved.get("display", {})
        _fields(display, set(), {"symbol", "security_id", "display_name", "asset_class", "currency", "quantity_unit"})
        for item in display.values():
            _text(item)
        return dict(reference=reference, binding=binding, owner_id=owner,
                    owner_continuity=continuity, assumptions=assumptions, display=display)

    def _identity_payload(self, value):
        if type(value) is str:
            if len(value) > 16000:
                raise ValueError("terminal_execution_identity_too_large")
            return json.loads(value, object_pairs_hook=_pairs)
        return _copy(value)

    def read(self, resource, identity=None):
        with self._lock:
            self._active()
            if resource not in READ_RESOURCES:
                raise ValueError("terminal_execution_unknown_resource")
            if resource == "terminal_execution_accounts":
                if identity is not None:
                    raise ValueError("terminal_execution_accounts_identity_not_allowed")
                root = self._safe(self.directory)
                items, warnings = [], []
                if root.exists():
                    for folder in sorted(root.iterdir()):
                        if not _ACCOUNT.fullmatch(folder.name):
                            continue
                        try:
                            manifest = self._manifest(folder.name)
                            items.append({key: manifest[key] for key in ("account_id", "label", "created_at", "evidence_kind")})
                        except (ValueError, OSError, KeyError, TypeError):
                            warnings.append(dict(account_id=folder.name, code="ACCOUNT_RECORD_UNAVAILABLE", original_retained=True))
                return dict(view_schema_version=VIEW_SCHEMA, items=items, warnings=warnings,
                            permissions=dict(PERMISSIONS), new_accounts_created=0, external_calls=0)
            if resource == "terminal_execution_account":
                account_id = _key(identity, _ACCOUNT, "account_id")
                return self._view(account_id, self._entry(account_id))
            payload = self._identity_payload(identity)
            if resource == "terminal_execution_research":
                _fields(payload, {"reference"})
                resolved = self._resolve(payload["reference"])
                return dict(view_schema_version=VIEW_SCHEMA, reference=resolved["reference"], binding=resolved["binding"],
                            owner_continuity=resolved["owner_continuity"], assumptions=resolved["assumptions"], display=resolved["display"],
                            permissions=dict(PERMISSIONS), external_calls=0)
            if resource == "terminal_execution_receipt":
                _fields(payload, {"account_id", "request_id"})
            elif resource == "terminal_execution_history":
                _fields(payload, {"account_id"}, {"limit"})
            else:
                _fields(payload, {"account_id", "plan_id", "reference"})
            account_id = _key(payload["account_id"], _ACCOUNT, "account_id")
            entry = self._entry(account_id)
            if resource == "terminal_execution_receipt":
                result = entry["store"].receipt(_key(payload["request_id"], _REQUEST, "request_id"))
            elif resource == "terminal_execution_history":
                result = {"events": entry["store"].history(payload.get("limit", 50))}
            else:
                resolved = self._resolve(payload["reference"])
                plan = next((item for item in entry["store"].snapshot()["plans"] if item["plan_id"] == payload["plan_id"]), None)
                if plan is None:
                    raise ValueError("terminal_execution_plan_not_found")
                result = compare_research_context(resolved["binding"], plan, resolved["assumptions"])
            _no_authority(result)
            return {**result, "view_schema_version": VIEW_SCHEMA, "account_id": account_id,
                    "account_context": entry["context"], "permissions": dict(PERMISSIONS), "external_calls": 0}

    def _create_account(self, payload):
        _fields(payload, {"client_request_id", "account_id", "label", "evidence_kind", "initial_cash", "securities", "rules"})
        request_id = _key(payload["client_request_id"], _REQUEST, "request_id")
        account_id = _key(payload["account_id"], _ACCOUNT, "account_id")
        _text(payload["label"], 100)
        if payload["evidence_kind"] != "SYNTHETIC_TEST":
            raise ValueError("terminal_execution_explicit_synthetic_account_required")
        _no_authority(payload)
        request_hash = _hash(payload)
        folder = self._folder(account_id)
        if folder.exists():
            manifest = self._manifest(account_id)
            if manifest["request_id"] != request_id or manifest["creation_request_hash"] != request_hash:
                raise ValueError("terminal_execution_account_creation_conflict")
            entry = self._entry(account_id)
            return self._created_view(account_id, entry, reused=True)
        self._safe(self.directory).mkdir(parents=True, exist_ok=True)
        self._safe(self.workspace)
        folder.mkdir(exist_ok=False)
        creation_id = secrets.token_hex(24)
        self._write_new(folder / "creation-intent.json", dict(schema_version="hakimi-terminal-execution-create-v1",
                        creation_id=creation_id, request_id=request_id, request_hash=request_hash, request=payload))
        store = OfflineExecutionStore.create(folder / "account.sqlite", account_id=account_id, initial_cash=payload["initial_cash"],
                                              securities=payload["securities"], rules=payload["rules"])
        manifest = dict(schema_version=MANIFEST_SCHEMA, account_id=account_id, label=payload["label"],
                        created_at=datetime.now(timezone.utc).isoformat(), creation_id=creation_id, request_id=request_id,
                        creation_request_hash=request_hash, config_hash=_hash(store.config), evidence_kind="SYNTHETIC_TEST",
                        database="account.sqlite", permissions=dict(PERMISSIONS))
        try:
            self._write_new(folder / "account.json", manifest)
        except BaseException:
            store.close()
            raise
        entry = dict(store=store, manifest=manifest, identity=(self._identity(folder), self._identity(folder / "account.sqlite")),
                     context=secrets.token_urlsafe(32), head=None)
        self._stores[account_id] = entry
        return self._created_view(account_id, entry, reused=False)

    def _created_view(self, account_id, entry, *, reused):
        result = dict(view_schema_version=VIEW_SCHEMA, status="ACCOUNT_CREATED", reused=reused,
                      account_id=account_id, account_context=entry["context"], permissions=dict(PERMISSIONS), external_calls=0)
        try:
            result["account"] = self._view(account_id, entry)
        except Exception as error:
            result.update(account=None, read_warning=str(error))
        return result

    def mutate(self, action, payload):
        with self._lock:
            self._active()
            if action not in MUTATION_ACTIONS:
                raise ValueError("terminal_execution_unknown_action")
            payload = _copy(payload)
            if action == "terminal_execution_create_account":
                return self._create_account(payload)
            common = {"client_request_id", "account_id", "account_context"}
            required = {
                "terminal_execution_create_plan": {"reference", "stage"},
                "terminal_execution_submit": {"plan_id", "security_id", "side", "quantity", "limit_price", "quote", "signal_at", "execution_at", "now_ms", "outcome"},
                "terminal_execution_observe": {"observation", "now_ms"},
                "terminal_execution_cancel": {"order_id", "now_ms", "outcome"},
                "terminal_execution_mark_quotes": {"quotes", "now_ms"},
                "terminal_execution_reconcile": {"complete_snapshot", "now_ms"},
                "terminal_execution_stop": {"reason"}, "terminal_execution_resume": {"reason"},
            }[action]
            _fields(payload, common | required)
            request_id = _key(payload["client_request_id"], _REQUEST, "request_id")
            account_id = _key(payload["account_id"], _ACCOUNT, "account_id")
            entry = self._entry(account_id, payload["account_context"])
            store = entry["store"]
            extra = {}
            if action == "terminal_execution_create_plan":
                resolved = self._resolve(payload["reference"])
                display = resolved["display"]
                security_id = resolved["binding"].get("security_id")
                security = store.config["securities"].get(security_id) if type(security_id) is str else None
                if (not security_id or display.get("security_id") != security_id or security is None
                        or display.get("symbol") != security["symbol"] or display.get("currency") != "USD"
                        or display.get("asset_class") != "US_EQUITY"):
                    raise ValueError("terminal_execution_verified_us_equity_account_security_required")
                owner_id = _hash(dict(account_id=account_id, engine_id=resolved["binding"]["engine_id"], owner=resolved["owner_id"]))
                receipt = store.create_plan(request_id, account_id=account_id, owner_id=owner_id,
                                            research_binding=resolved["binding"], stage=payload["stage"])
                plan_id = receipt["outcome"]["plan_id"]
                link = dict(schema_version="hakimi-terminal-execution-plan-link-v1", plan_id=plan_id,
                            reference=resolved["reference"], binding_hash=_hash(resolved["binding"]),
                            scoped_owner_id=owner_id, owner_source=resolved["owner_id"], owner_continuity=resolved["owner_continuity"])
                path = self._folder(account_id) / "plan-links" / (plan_id + ".json")
                try:
                    if path.exists():
                        if self._read_json(path) != link:
                            raise ValueError("terminal_execution_plan_display_link_conflict")
                    else:
                        self._safe(path.parent).mkdir(exist_ok=True)
                        self._write_new(path, link)
                except (ValueError, OSError):
                    extra["display_warning"] = "PLAN_SAVED_DISPLAY_LINK_UNAVAILABLE"
            else:
                name = action.removeprefix("terminal_execution_")
                if name == "submit":
                    plan = store._plan(payload["plan_id"])
                    bound_security = plan["research_binding"].get("security_id")
                    if not bound_security or bound_security != payload["security_id"]:
                        raise ValueError("terminal_execution_plan_security_identity_required")
                method = {"submit": store.submit, "observe": store.observe, "cancel": store.cancel,
                          "mark_quotes": store.mark_quotes, "reconcile": store.reconcile,
                          "stop": store.stop, "resume": store.resume}[name]
                arguments = {key: payload[key] for key in required}
                receipt = method(request_id, account_id=account_id, **arguments)
            _no_authority(receipt)
            # A successful ledger receipt remains the authoritative fact if an
            # auxiliary projection cannot be read after the commit.
            try:
                account = self._view(account_id, entry)
            except Exception as error:
                account = None
                extra["read_warning"] = str(error)
            return dict(view_schema_version=VIEW_SCHEMA, receipt=receipt, account=account,
                        account_id=account_id, account_context=entry["context"], permissions=dict(PERMISSIONS), external_calls=0, **extra)

    def close(self):
        with self._lock:
            if self._closed:
                return
            self._closed = True
            errors = []
            for entry in self._stores.values():
                try:
                    entry["store"].close()
                except Exception as error:
                    errors.append(error)
            self._stores.clear()
            if errors:
                raise RuntimeError("terminal_execution_close_failed") from errors[0]
