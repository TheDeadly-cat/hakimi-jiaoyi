"""Read existing workspaces without opening a service, lock, journal or database.

Discovery is restricted to trusted launcher paths and known product locations.
Client-facing calls accept opaque inventory IDs, never filesystem paths. Pure
existing verifiers are reused; failure leaves an explicitly unverified metadata
view. No migration, retry, active-workspace selection or economic run is offered.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import importlib
import json
import math
import os
from pathlib import Path
import re
import stat


_MAX_BYTES = 64 * 1024 * 1024
_MAX_FILES = 10000
_ID = re.compile(r"[0-9a-f]{32}\Z")
_AREAS = {"tasks": ("tasks", "terminal-tasks"), "runs": ("runs", "terminal-runs")}
_READ_ONLY = {"read_only": True, "new_economic_runs": 0, "automatic_retry": False,
              "permissions": {"research_only": True, "paper_allowed": False,
                              "live_allowed": False, "order_allowed": False}}


def _no_links(path):
    path = Path(path).absolute()
    for current in (path, *path.parents):
        try:
            info = current.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ValueError("history_reparse_path_not_supported")
    return path


def _safe(root, path):
    path = _no_links(path)
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError("history_path_outside_workspace")
    if path.is_file() and path.stat().st_size > _MAX_BYTES:
        raise ValueError("history_file_too_large")
    return resolved


def _pairs(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("history_duplicate_json_field")
        result[key] = value
    return result


def _document(root, path):
    path = _safe(root, path)
    with path.open("rb") as stream:
        raw = stream.read(_MAX_BYTES + 1)
    if len(raw) > _MAX_BYTES:
        raise ValueError("history_file_too_large")
    value = json.loads(raw, object_pairs_hook=_pairs,
                       parse_constant=lambda value: (_ for _ in ()).throw(ValueError("history_nonfinite_json")))
    if type(value) is not dict:
        raise ValueError("history_json_object_required")
    return value


def _guard_tree(root, path):
    pending, count = [_safe(root, path)], 0
    while pending:
        current = pending.pop()
        count += 1
        if count > _MAX_FILES:
            raise ValueError("history_record_file_limit")
        _safe(root, current)
        if current.is_dir():
            pending.extend(current.iterdir())


def _opaque(value):
    return sha256(str(value).encode("utf-8")).hexdigest()[:32]


def _metadata(document):
    keys = ("schema_version", "title", "name", "state", "status", "version", "id",
            "family_id", "task_id", "run_id", "engine_id", "strategy_id", "strategy",
            "started_at", "configuration", "strategy_params", "risk", "costs", "symbol",
            "input_id", "evidence_status", "error", "execution_model")
    return {key: deepcopy(document[key]) for key in keys if key in document}


def _chart_valid(chart):
    if not isinstance(chart, dict) or not chart.get("symbol") or not chart.get("input_id"):
        return False
    if not chart.get("run_id") or not chart.get("report_hash"):
        return False
    if not chart.get("meta", {}).get("asset_class") or not chart.get("meta", {}).get("price_basis"):
        return False
    rows, trades = chart.get("rows"), chart.get("trades")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 10000 or not isinstance(trades, list) or len(trades) > 20000:
        return False
    previous = -math.inf
    for row in rows:
        if not isinstance(row, dict):
            return False
        stamp = row.get("ts_ms", row.get("ts"))
        numbers = [row.get(key) for key in ("open", "high", "low", "close", "volume")]
        if (type(stamp) not in (int, float) or not math.isfinite(stamp) or stamp <= previous
                or not row.get("date") or any(type(value) not in (int, float) or not math.isfinite(value) for value in numbers)):
            return False
        opened, high, low, closed, volume = numbers
        if min(opened, low, closed) <= 0 or volume < 0 or high < max(opened, closed, low) or low > min(opened, closed):
            return False
        previous = stamp
    return True


def _native_reader(root):
    # Reuse only exact read methods. No TerminalResearchService constructor or
    # initialization of its insights/judgment/exit services is performed.
    from .terminal_research import TerminalResearchService

    class NativeReadOnly:
        workspace = root
        _read = TerminalResearchService._read
        _family = TerminalResearchService._family
        _task_record = TerminalResearchService._task_record
        _input = TerminalResearchService._input
        _verified_core_document = staticmethod(TerminalResearchService._verified_core_document)
        _input_view = staticmethod(TerminalResearchService._input_view)
        _verified_report = TerminalResearchService._verified_report
        _report_view = TerminalResearchService._report_view

        def _safe(self, path):
            return _safe(root, path)

    return NativeReadOnly()


def msix_history_roots_for_workspace(current_workspace, *, local_app_data=None):
    """Use the selected terminal data container, not inferred OS ownership.

    The server supplies its already selected physical workspace. Only our exact
    standard data layout can authorize a same-container history candidate. This
    neither scans Packages nor accepts a renderer-provided path.
    """
    local = Path(local_app_data if local_app_data is not None
                 else os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
    try:
        packages = _no_links(local / "Packages").resolve(strict=True)
        workspace = _no_links(current_workspace).resolve(strict=True)
        relative = workspace.relative_to(packages)
        parts = relative.parts
        if (len(parts) != 8 or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}_[a-z0-9]{13}", parts[0]) is None
                or parts[1:5] != ("LocalCache", "Local", "HakimiTradeTerminal", "workspaces")
                or parts[6:] != ("runtime", "research-workspace") or not workspace.is_dir()):
            return ()
        package = _no_links(packages / parts[0]).resolve(strict=True)
        if package.parent != packages or not package.is_dir():
            return ()
        return (package,)
    except (OSError, ValueError, TypeError):
        return ()


class TerminalWorkspaceHistory:
    def __init__(self, runtime_dir=None, *, local_app_data=None, extra_roots=(), current_workspace=None,
                 known_original_root=None, msix_package_roots=()):
        self.runtime_dir = Path(runtime_dir) if runtime_dir is not None else None
        self.local_app_data = Path(local_app_data if local_app_data is not None
                                   else os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local")))
        self.extra_roots = tuple(Path(path) for path in extra_roots)
        # Trusted launcher input only, never a renderer-supplied filesystem path.
        # Empty by default: no Packages scan or inferred package ownership.
        self.msix_package_roots = tuple(Path(path) for path in msix_package_roots)
        self.current_workspace = _no_links(current_workspace).resolve() if current_workspace is not None else None
        self.known_original_root = Path(known_original_root) if known_original_root is not None else (
            Path.home() / "Documents" / "哈基米v2交易" / "outputs" / "python_quant_bot" / "runtime" / "research-workspace")

    def _msix_candidates(self, candidates, trial_root):
        """Add exact observed marker mappings as independent physical roots.

        Never redirect the logical root or change _safe. An MSIX file mapping
        can differ from its parent directory's resolve(), so only an explicitly
        allowed, same-name LocalCache mapping is eligible for separate discovery.
        """
        additions, warnings, allowed = [], [], []
        if not self.msix_package_roots:
            return additions, warnings
        try:
            packages = _no_links(self.local_app_data / "Packages").resolve()
            trial = _no_links(trial_root).resolve()
        except (OSError, ValueError) as exc:
            return additions, [str(exc)]
        for supplied in self.msix_package_roots:
            try:
                package = _no_links(supplied).resolve(strict=True)
                if (not package.is_dir() or package.parent != packages
                        or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}_[a-z0-9]{13}", package.name) is None):
                    raise ValueError("history_msix_package_root_not_exact")
                allowed.append(package)
            except (OSError, ValueError) as exc:
                warnings.append(str(supplied) + ": " + str(exc))
        for supplied, _ in candidates:
            try:
                logical = _no_links(supplied)
                if (logical.parent.resolve() != trial or not logical.is_dir()
                        or re.fullmatch(r"[0-9a-f]{20}", logical.name) is None):
                    continue
                logical_root = logical.resolve()
                if self.current_workspace is not None and logical_root == self.current_workspace:
                    continue
                marker = _no_links(logical / "trial-workspace-identity.json")
                if not marker.is_file():
                    continue
                resolved_marker = _no_links(marker.resolve(strict=True))
                if resolved_marker.is_relative_to(logical_root):
                    continue  # Ordinary in-root marker: original discovery only.
                expected = [package / "LocalCache" / "Local" / "HakimiTradeTrial" / "workspaces"
                            / logical.name / "trial-workspace-identity.json" for package in allowed]
                if resolved_marker not in expected:
                    raise ValueError("history_msix_mapping_not_allowlisted_exact")
                physical = _no_links(resolved_marker.parent).resolve(strict=True)
                if physical != resolved_marker.parent:
                    raise ValueError("history_msix_parent_mapping_not_exact")
                document = _document(physical, resolved_marker)
                bundle = document.get("bundle_id")
                if (set(document) != {"schema_version", "bundle_id"}
                        or document.get("schema_version") != "research-trial-workspace-v1"
                        or type(bundle) is not str or re.fullmatch(r"[0-9a-f]{64}", bundle) is None
                        or bundle[:20] != logical.name):
                    raise ValueError("history_msix_marker_identity_mismatch")
                additions.append((physical, "旧试用工作区 · " + logical.name + "（MSIX 物理只读）"))
            except (OSError, ValueError, TypeError) as exc:
                warnings.append(str(supplied) + ": " + str(exc))
        return additions, warnings

    def _inventory(self):
        candidates = [(self.known_original_root, "原终端历史工作区")]
        if self.runtime_dir is not None:
            candidates.append((self.runtime_dir / "research-workspace", "原终端历史工作区"))
        candidates.extend((path, "已知历史工作区") for path in self.extra_roots)
        warnings = []
        trial_root = self.local_app_data / "HakimiTradeTrial" / "workspaces"
        try:
            _no_links(trial_root)
            if trial_root.is_dir():
                candidates.extend((path, "旧试用工作区 · " + path.name) for path in sorted(trial_root.iterdir()) if not path.name.startswith("."))
        except (OSError, ValueError) as exc:
            warnings.append(str(exc))
        physical, mapping_warnings = self._msix_candidates(candidates, trial_root)
        candidates.extend(physical)
        warnings.extend(mapping_warnings)
        entries, seen = [], set()
        for supplied, label in candidates:
            try:
                path = _no_links(supplied)
                if not path.is_dir():
                    continue
                root = path.resolve()
                key = os.path.normcase(str(root))
                if key in seen or (self.current_workspace is not None and key == os.path.normcase(str(self.current_workspace))):
                    continue
                seen.add(key)
                identity, schemas = {}, []
                for filename in ("trial-workspace-identity.json", "workspace.json"):
                    marker = _safe(root, root / filename)
                    if marker.is_file():
                        document = _document(root, marker)
                        identity[filename] = document
                        if document.get("schema_version"):
                            schemas.append(document["schema_version"])
                if not identity and not any(_safe(root, root / name).is_dir() for names in _AREAS.values() for name in names):
                    continue
                entries.append({"id": _opaque(key), "label": label, "physical_root": str(root),
                    "schemas": schemas, "identity": identity, **deepcopy(_READ_ONLY)})
            except (OSError, ValueError, TypeError) as exc:
                warnings.append(str(supplied) + ": " + str(exc))
        return entries, warnings

    def list_workspaces(self):
        entries, warnings = self._inventory()
        return {"items": entries, "warnings": warnings, **deepcopy(_READ_ONLY)}

    def _workspace(self, identity):
        if type(identity) is not str or _ID.fullmatch(identity) is None:
            raise ValueError("history_unknown_workspace")
        for item in self._inventory()[0]:
            if item["id"] == identity:
                return Path(item["physical_root"])
        raise ValueError("history_unknown_workspace")

    def _records(self, root, resource):
        if resource not in _AREAS:
            raise ValueError("history_resource_not_readable")
        records, warnings = [], []
        for area in _AREAS[resource]:
            directory = _safe(root, root / area)
            if not directory.is_dir():
                continue
            for path in sorted(directory.iterdir()):
                if path.name.startswith("."):
                    continue
                try:
                    path = _safe(root, path)
                    if not path.is_dir() and not (resource == "tasks" and path.suffix == ".json"):
                        continue
                    relative = path.relative_to(root).as_posix()
                    records.append((path, area.startswith("terminal-"), _opaque(relative)))
                except (OSError, ValueError) as exc:
                    warnings.append(path.name + ": " + str(exc))
        return records, warnings

    def list_records(self, workspace_id, resource):
        root = self._workspace(workspace_id)
        records, warnings = self._records(root, resource)
        items = []
        for path, native, identity in records:
            detail = self._read_record(root, path, resource, native, identity, detail=False)
            items.append(detail)
        return {"workspace_id": workspace_id, "physical_root": str(root), "resource": resource,
                "items": items, "warnings": warnings, **deepcopy(_READ_ONLY)}

    def read_detail(self, workspace_id, resource, record_id):
        root = self._workspace(workspace_id)
        if type(record_id) is not str or _ID.fullmatch(record_id) is None:
            raise ValueError("history_unknown_record")
        for path, native, identity in self._records(root, resource)[0]:
            if identity == record_id:
                return {"workspace_id": workspace_id, **self._read_record(root, path, resource, native, identity, detail=True)}
        raise ValueError("history_unknown_record")

    def _read_record(self, root, path, resource, native, identity, *, detail):
        value = {"id": identity, "label": path.stem, "resource": resource,
                 "record_kind": "ORIGINAL_TERMINAL" if native else "EQUITY_RESEARCH",
                 "relative_path": path.relative_to(root).as_posix(), "physical_root": str(root),
                 "verification_status": "METADATA_ONLY", "chart_available": False,
                 "verification_note": "仅展示原文件信息，尚未通过适用合同校验。", **deepcopy(_READ_ONLY)}
        try:
            _guard_tree(root, path)
            if resource == "runs":
                primary = path / ("report.json" if (path / "report.json").is_file() else "started.json")
            else:
                primary = path / "family.json" if path.is_dir() else path
            document = _document(root, primary)
            value["stored_metadata"] = _metadata(document)
            value["schema_version"] = document.get("schema_version")
            value["label"] = document.get("title") or document.get("name") or path.stem
            if resource == "runs" and not (path / "report.json").is_file():
                value.update(status="UNKNOWN", verification_note="原运行没有完整结果；保留 UNKNOWN，不自动重跑。")
                return value
            if native:
                verified = self._native(root, path, resource, detail=detail)
                verifier = "original-terminal-record-contract"
            else:
                verified, verifier = self._core(root, path, resource, detail=detail)
            value.update(verified, verification_status="VERIFIED_RECORD", verified_by=verifier,
                         verification_note="原保存记录及关联输入已通过读取校验；未重新计算，不改变原证据等级。")
            value["chart_available"] = _chart_valid(value.get("chart")) if detail else bool(verified.get("chart_available"))
            if not value["chart_available"]:
                value.pop("chart", None)
        except (OSError, ValueError, TypeError, KeyError, ImportError, AttributeError) as exc:
            value["verification_error"] = str(exc)[:2000]
            value["verification_note"] = "此记录未通过当前可用的读取合同；仅展示原文件元数据，不提供图表或验收结论。"
        return value

    def _native(self, root, path, resource, *, detail):
        reader = _native_reader(root)
        if resource == "tasks":
            family = reader._family(path.name)
            task = reader._task_record(family["task_id"], family_id=path.name)
            reader._input(task["input_id"])
            return {"label": task["title"], "task_id": task["id"], "engine_id": task["engine_id"],
                    "strategy_id": task["strategy_id"], "version": task["version"], "state": family["state"],
                    **({"task": task} if detail else {})}
        report = reader._verified_report(path)
        result = {"label": report["title"], "run_id": report["id"], "task_id": report["task_id"],
                  "engine_id": report["engine_id"], "strategy_id": report["strategy_id"], "status": report["status"],
                  "version": report["version"], "evidence_status": report.get("evidence_status"),
                  "configuration": deepcopy(report["configuration"])}
        if detail:
            result["report"] = report
            if report["status"] == "COMPLETED":
                chart = reader._report_view(report, detail=True).get("chart")
                if _chart_valid(chart):
                    result["chart"] = chart
        return result

    def _guard_core_task(self, root, path):
        tasks = list(path.rglob("task.json")) if path.is_dir() else [path]
        for task in tasks:
            document = _document(root, task)
            for key in ("snapshot", "event_context"):
                reference = document.get(key)
                if reference:
                    if type(reference) is not str:
                        raise ValueError("history_input_reference_invalid")
                    _safe(root, task.parent / reference)

    def _core(self, root, path, resource, *, detail):
        if resource == "tasks":
            self._guard_core_task(root, path)
        errors = []
        for package in ("hakimi_research", "hakimi_terminal_research"):
            try:
                if resource == "tasks":
                    manager = importlib.import_module(package + ".task_manager")
                    view = manager.describe_task(path)
                    return {"label": view.get("title") or path.stem, "task_id": view["task_id"],
                            "strategy_id": view["strategy"], "state": view["state"],
                            "revisions": view["revisions"], **({"task": view} if detail else {})}, package
                offline = importlib.import_module(package + ".offline_app")
                manifest, report, snapshot = offline.verify_run(path)
                result = {"run_id": manifest["run_id"], "task_id": manifest["task_id"],
                          "strategy_id": manifest["task"]["strategy"], "status": "COMPLETED",
                          "runtime": deepcopy(manifest["runtime"]), "report_schema": report.get("schema_version"),
                          "configuration": deepcopy(report["spec"]), "report_hash": report["report_hash"],
                          "label": report["dataset"]["security"]["symbol"] + " · " + manifest["task"]["strategy"]}
                if detail:
                    result.update(manifest=manifest, report=report)
                    from .terminal_research import _core_chart
                    try:
                        chart = _core_chart(snapshot.document, report["result"]["fills"],
                                            run_id=manifest["run_id"], report_hash=report["report_hash"])
                        if _chart_valid(chart):
                            result["chart"] = chart
                    except (KeyError, TypeError, ValueError) as exc:
                        result["chart_note"] = "已核对结果，但此历史数据暂不支持原图表：" + str(exc)
                return result, package
            except (ImportError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
                errors.append(package + ": " + str(exc))
        raise ValueError("; ".join(errors))
