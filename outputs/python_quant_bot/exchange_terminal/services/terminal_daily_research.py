"""Explicit stock intake/update actions over the existing canonical algorithms.

The canonical records live in <the current QuantWorkspace>/daily/. They never
enter the frozen kernel's data/tasks/runs directories or reuse its record IDs.
Reads are lazy. Only explicit mutation actions initialize the canonical writer;
none of the exposed actions runs research, advances an account or places orders.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import re
from threading import RLock

from .terminal_workspace_history import _document, _guard_tree, _no_links, _safe


_PREFIX = "terminal_daily_"
_ID = re.compile(r"canon-[0-9a-f]{32}\Z")
_OP = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
_AREAS = {"inputs": "data", "intakes": "stock-intakes", "updates": "updates", "tasks": "tasks"}
_ACTIONS = {
    "check_stock": ({"operation_id", "symbol", "history_sessions"}, {"operation_id", "symbol", "history_sessions"}),
    "save_stock": ({"operation_id", "intake_id", "expected_check_hash", "confirmed_security"},
                   {"operation_id", "intake_id", "expected_check_hash", "confirmed_security"}),
    "check_update": ({"operation_id", "input_id"}, {"operation_id", "input_id"}),
    "freeze_update": ({"operation_id", "update_id", "expected_check_hash", "acknowledge_revisions"},
                      {"operation_id", "update_id", "expected_check_hash"}),
    "create_task": ({"operation_id", "input_id", "strategy", "title", "params", "risk", "score_start", "score_end",
                     "initial_cash", "fee_rate", "slippage_pct"}, {"operation_id", "input_id", "strategy"}),
    "adopt_update": ({"operation_id", "update_id", "expected_check_hash", "task_id", "expected_task_id", "score_end"},
                     {"operation_id", "update_id", "expected_check_hash", "task_id", "expected_task_id", "score_end"}),
}


class TerminalDailyResearch:
    def __init__(self, workspace, *, fetcher=None, clock=None):
        self.workspace = _no_links(Path(workspace).absolute()).resolve()
        self.root = _safe(self.workspace, self.workspace / "daily")
        self.fetcher, self.clock = fetcher, clock
        self._writer = None
        self._lock = RLock()

    def _common(self):
        return {"record_namespace": "canonical-daily-v1", "canonical_package": "hakimi_research",
                "workspace_root": str(self.workspace), "storage_root": str(self.root), "new_economic_runs": 0,
                "permissions": {"research_only": True, "paper_allowed": False, "live_allowed": False,
                                "order_allowed": False}, "automatic_retry": False}

    def _path(self, path):
        _no_links(self.workspace)
        return _safe(self.root, path)

    def _id(self, path):
        return "canon-" + sha256(self._path(path).relative_to(self.root).as_posix().encode()).hexdigest()[:32]

    def _paths(self, kind):
        if kind not in _AREAS:
            raise ValueError("daily_unknown_resource")
        directory = self._path(self.root / _AREAS[kind])
        if not directory.is_dir():
            return []
        _guard_tree(self.root, directory)
        if kind == "inputs":
            return sorted(directory.rglob("*.json"))
        if kind == "tasks":
            from hakimi_research.task_manager import list_tasks
            return list_tasks(self.root)
        return sorted(path for path in directory.iterdir() if path.is_dir() and path.name.startswith("check-"))

    def _lookup(self, kind, identity):
        if type(identity) is not str or _ID.fullmatch(identity) is None:
            raise ValueError("daily_canonical_record_id_required")
        for path in self._paths(kind):
            if self._id(path) == identity:
                return self._path(path)
        raise ValueError("daily_record_not_found")

    def _reader(self):
        # Workbench.__init__ creates directories and captures a writable runtime.
        # Read methods need only root/path/ref; skip initialization entirely.
        from hakimi_research.workbench_service import Workbench
        reader = object.__new__(Workbench)
        reader.root = self.root
        return reader

    def _view(self, kind, path):
        path = self._path(path)
        _guard_tree(self.root, path)
        ref = path.relative_to(self.root).as_posix()
        if kind == "inputs":
            from hakimi_research.input_workflow import inspect_input
            view = inspect_input(path)
        elif kind == "tasks":
            from hakimi_research.task_manager import describe_task
            for task_file in path.rglob("task.json") if path.is_dir() else [path]:
                task = _document(self.root, task_file)
                for key in ("snapshot", "event_context"):
                    if task.get(key):
                        self._path(task_file.parent / task[key])
            view = describe_task(path)
        elif kind == "intakes":
            view = self._reader().stock_intake_view(ref)
        else:
            view = self._reader().daily_update_view(ref, include_impact=False)
        result = {**view, **self._common(), "id": self._id(path), "record_resource": _PREFIX + kind}
        result["permissions"] = {**deepcopy(view.get("permissions") or {}), **self._common()["permissions"]}
        result["record_schema"] = (view.get("schema_version") if kind in {"intakes", "updates"}
            else _document(self.root, self._path(view["task_file"]) if kind == "tasks" else path).get("schema_version"))
        if kind == "updates":
            result["display_status"] = {"READY": "NEW_DAILY", "REVISION_REVIEW_REQUIRED": "REVISION",
                                        "UNCHANGED": "UNCHANGED"}.get(view.get("status"), "FAILED")
        if kind in {"intakes", "updates"}:
            receipt = view.get("freeze_receipt") or {}
            input_ref = receipt.get("input_ref")
            result["saved_input_id"] = self._id(self.root / input_ref) if input_ref else None
        return result

    def read(self, resource, identity=None):
        if resource == _PREFIX + "catalog":
            if identity is not None:
                raise ValueError("daily_catalog_has_no_record_id")
            from hakimi_research.stock_intake import first_use_catalog
            from hakimi_research.daily_updates import calendar_support
            from hakimi_research.strategy_registry import strategies
            return {**first_use_catalog(), "strategies": strategies(), "calendar": calendar_support(),
                    "supported_actions": [_PREFIX + name for name in _ACTIONS],
                    "workflow": "明确检查来源与证券 → 明确保存行情 → 明确创建任务；更新先核对，再保存并采用新版本。采用不运行。",
                    **self._common()}
        if not isinstance(resource, str) or not resource.startswith(_PREFIX):
            raise ValueError("daily_unknown_resource")
        kind = resource[len(_PREFIX):]
        if kind not in _AREAS:
            raise ValueError("daily_unknown_resource")
        if identity is not None:
            return self._view(kind, self._lookup(kind, identity))
        items, warnings = [], []
        for path in self._paths(kind):
            try:
                items.append(self._view(kind, path))
            except (ValueError, OSError, TypeError, KeyError) as exc:
                warnings.append(path.name + ": " + str(exc))
        return {"items": items, "warnings": warnings, **self._common()}

    def verified_input(self, identity):
        """Trusted in-process bridge; retain original bytes and canonical identity.

        This does not turn a canonical ID into a frozen-core ID or publish it to
        another engine. A caller must explicitly apply that engine's existing
        import/admission contract before creating a separate input reference.
        """
        from hakimi_research.documents import parse_document
        from hakimi_research.equity_dataset import verify_equity_snapshot
        path = self._lookup("inputs", identity)
        raw = self._path(path).read_bytes()
        return raw, verify_equity_snapshot(parse_document(raw))

    def _ensure_writer(self):
        if self._writer is None:
            from hakimi_research.workbench_service import Workbench
            fetcher, clock = self.fetcher, self.clock

            class ExplicitDailyWorkbench(Workbench):
                def _dispatch(self, request):
                    if request["action"] == "check_stock_import":
                        from hakimi_research.stock_intake import check_stock_import
                        directory = self.root / "stock-intakes" / ("check-" + request["operation_id"])
                        check_stock_import(request["symbol"], request["history_sessions"], directory,
                                           fetcher=fetcher, now=clock() if clock else None)
                        return self.stock_intake_view(self.ref(directory))
                    if request["action"] == "check_stock_update":
                        from hakimi_research.daily_updates import check_daily_update
                        directory = self.root / "updates" / ("check-" + request["operation_id"])
                        check_daily_update(self.path(request["snapshot"], "data"), directory,
                                           fetcher=fetcher, now=clock() if clock else None)
                        return self.daily_update_view(self.ref(directory), include_impact=False)
                    return super()._dispatch(request)

            self._path(self.root)
            self._writer = ExplicitDailyWorkbench(self.root)
        return self._writer

    def mutate(self, action, payload):
        if type(action) is not str or not action.startswith(_PREFIX) or action[len(_PREFIX):] not in _ACTIONS:
            raise ValueError("daily_action_not_supported_no_execution")
        name = action[len(_PREFIX):]
        allowed, required = _ACTIONS[name]
        if type(payload) is not dict or set(payload) - allowed or required - set(payload):
            raise ValueError("daily_action_fields_invalid")
        if type(payload["operation_id"]) is not str or _OP.fullmatch(payload["operation_id"]) is None:
            raise ValueError("daily_explicit_operation_id_required")
        with self._lock:
            return self._mutate(name, deepcopy(payload))

    def _mutate(self, name, payload):
        request = {"operation_id": payload["operation_id"]}
        target_kind = None
        ref = lambda kind, identity: self._lookup(kind, identity).relative_to(self.root).as_posix()
        if name == "check_stock":
            # Canonical validation is retained; reject obvious invalid input
            # before even initializing the explicit writer.
            if type(payload["symbol"]) is not str or re.fullmatch(r"[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z])?", payload["symbol"]) is None:
                raise ValueError("stock_symbol_invalid")
            if type(payload["history_sessions"]) is not int or payload["history_sessions"] not in (20, 60, 120):
                raise ValueError("stock_history_sessions_must_be_20_60_or_120")
            request.update(action="check_stock_import", symbol=payload["symbol"], history_sessions=payload["history_sessions"])
            target_kind = "intakes"
        elif name == "save_stock":
            request.update(action="save_stock_import", intake=ref("intakes", payload["intake_id"]),
                           expected_check_hash=payload["expected_check_hash"], confirmed_security=payload["confirmed_security"])
            target_kind = "inputs"
        elif name == "check_update":
            request.update(action="check_stock_update", snapshot=ref("inputs", payload["input_id"]))
            target_kind = "updates"
        elif name in {"freeze_update", "adopt_update"}:
            update_path = self._lookup("updates", payload["update_id"])
            update = self._view("updates", update_path)
            if payload["expected_check_hash"] != update["check_hash"]:
                raise ValueError("daily_check_changed_reload_before_adoption")
            if update["status"] == "UNCHANGED":
                return {**update, "adoption_status": "UNCHANGED_NO_NEW_VERSION", "new_input_snapshots": 0,
                        "new_task_versions": 0, "new_economic_runs": 0}
            if not update.get("can_freeze"):
                raise ValueError("daily_update_not_adoptable:" + str(update.get("status")))
            if name == "freeze_update":
                ack = payload.get("acknowledge_revisions", False)
                if type(ack) is not bool:
                    raise ValueError("revision_acknowledgment_exact_bool_required")
                request.update(action="freeze_stock_update", update=update_path.relative_to(self.root).as_posix(), acknowledge_revisions=ack)
                target_kind = "inputs"
            else:
                if not update.get("saved_input_id"):
                    raise ValueError("daily_update_must_be_explicitly_frozen_before_adoption")
                request.update(action="bind_task_input", task=ref("tasks", payload["task_id"]),
                               snapshot=ref("inputs", update["saved_input_id"]), expected_task_id=payload["expected_task_id"], score_end=payload["score_end"])
                target_kind = "tasks"
        elif name == "create_task":
            from hakimi_research.strategy_registry import definition
            definition(payload["strategy"])
            request.update({key: value for key, value in payload.items() if key != "input_id"})
            request.update(action="create_task", snapshot=ref("inputs", payload["input_id"]))
            target_kind = "tasks"
        result = self._ensure_writer().action(request)
        target = result.get("path") or (self.root / result["ref"] if result.get("ref") else None)
        view = self._view(target_kind, self._path(target)) if target is not None else {**result, **self._common()}
        return {**view, "action_status": result.get("status"), "input_update_status": result.get("input_update_status"),
                **({"suggested_task": deepcopy(result["suggested_task"])} if "suggested_task" in result else {})}
