"""The accepted research kernel inside the existing terminal's local workspace.

Only this adapter owns HTTP routing and presentation. Historical research files,
durable once-only jobs, and economic rules remain owned by the accepted kernel.
"""
from __future__ import annotations

from hashlib import sha256
import importlib
import importlib.util
import ipaddress
import json
import logging
from pathlib import Path
import re
import secrets
import stat
import sys
from threading import RLock
from types import SimpleNamespace
from urllib.parse import unquote, urlsplit


ACCEPTED_SOURCE_SHA256 = "ca42fd0370854f65ef7fc82d654f7b9cc7b67de3f776865fbcffcae1b8f26918"
MAX_REQUEST = 24 * 1024 * 1024
_VENDOR = Path(__file__).resolve().parents[2] / "vendor" / "research"
_IMPORT_LOCK = RLock()
_READ_RESOURCES = frozenset({"status", "strategies", "tasks", "inputs", "runs", "csv_templates",
    "terminal_catalog", "terminal_market", "terminal_inputs", "terminal_tasks", "terminal_runs", "terminal_history", "terminal_reports", "terminal_core_inputs", "core_replay",
    "terminal_judgments", "terminal_judgment_replay", "terminal_exit_experiments",
    "terminal_exit_runs", "terminal_exit_replay", "terminal_structure_replay", "terminal_insights", "terminal_peers"})


def _no_links(path: Path) -> None:
    """Check before resolving, including Windows directory junctions."""
    for candidate in (path, *path.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ValueError("quant_reparse_path_not_supported")


def _verified_package_root(vendor: Path) -> Path:
    root = vendor / "hakimi_terminal_research"
    _no_links(root)
    document = json.loads((root / "runtime-files.json").read_bytes())
    if (type(document) is not dict or set(document) != {"schema_version", "files"}
            or document["schema_version"] != "research-runtime-files-v1"):
        raise ValueError("quant_runtime_manifest_invalid")
    names = document["files"]
    if (type(names) is not list or any(type(name) is not str for name in names)
            or names != sorted(set(names)) or "runtime-files.json" not in names):
        raise ValueError("quant_runtime_manifest_invalid")
    hashes = {}
    for name in names:
        relative = Path(name)
        if (relative.is_absolute() or ".." in relative.parts or "\\" in name or ":" in name
                or not (relative.suffix in {".py", ".json", ".lock"}
                        or relative.parts[0] == "resources" and relative.suffix in {".csv", ".html"})):
            raise ValueError("quant_runtime_manifest_path_invalid")
        target = root / relative
        _no_links(target)
        hashes[name] = sha256(target.read_bytes()).hexdigest()
    for target in root.rglob("*"):
        relative = target.relative_to(root)
        if "__pycache__" in relative.parts or target.name == "_build_identity.json":
            continue
        _no_links(target)
        if target.is_file() and (target.suffix in {".py", ".json", ".lock"}
                or relative.parts[0] == "resources" and target.suffix in {".csv", ".html"}):
            if relative.as_posix() not in hashes:
                raise ValueError("quant_runtime_unexpected_source")
    digest = sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if digest != ACCEPTED_SOURCE_SHA256:
        raise ValueError("quant_runtime_source_identity_mismatch")
    return root.resolve()


def _load_kernel(vendor: Path = _VENDOR):
    """Import only the verified package, without changing dependency search paths."""
    with _IMPORT_LOCK:
        root = _verified_package_root(vendor)
        for name, module in tuple(sys.modules.items()):
            if name == "hakimi_terminal_research" or name.startswith("hakimi_terminal_research."):
                source = getattr(module, "__file__", None)
                if source is None or not Path(source).resolve().is_relative_to(root):
                    raise ValueError("quant_runtime_package_already_loaded_from_another_location")
        if "hakimi_terminal_research" not in sys.modules:
            spec = importlib.util.spec_from_file_location("hakimi_terminal_research", root / "__init__.py",
                                                        submodule_search_locations=[str(root)])
            if spec is None or spec.loader is None:
                raise ValueError("quant_runtime_package_unavailable")
            package = importlib.util.module_from_spec(spec)
            sys.modules["hakimi_terminal_research"] = package
            try:
                spec.loader.exec_module(package)
            except BaseException:
                for name in tuple(sys.modules):
                    if name == "hakimi_terminal_research" or name.startswith("hakimi_terminal_research."):
                        sys.modules.pop(name, None)
                raise
        desktop = importlib.import_module("hakimi_terminal_research.desktop_app")
        service = importlib.import_module("hakimi_terminal_research.desktop_service")
        return SimpleNamespace(root=root, desktop=desktop, service=service.DesktopService,
                               version="0.5.0.dev8")


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_field")
        result[key] = value
    return result


def _finite_json(value):
    if isinstance(value, float):
        import math
        if not math.isfinite(value):
            raise ValueError("finite_json_required")
    elif isinstance(value, dict):
        for child in value.values():
            _finite_json(child)
    elif isinstance(value, list):
        for child in value:
            _finite_json(child)


_EMBEDDED_STYLE = """
.app{display:block;min-height:100vh}.workspace{grid-column:auto}
.sidebar{position:sticky;inset:auto;top:0;width:auto;padding:8px 18px;
 flex-direction:row;align-items:center;gap:12px;background:#101722;z-index:20}
.sidebar .brand,.sidebar .footnote{display:none}.nav{flex-direction:row;flex-wrap:wrap;gap:4px}
.nav button,.sidebar-bottom button{width:auto;min-height:40px;padding:8px 14px}
.nav button.active{box-shadow:inset 0 -3px #2563eb}.sidebar-bottom{margin:0 0 0 auto;padding:0}
.sidebar-bottom button{font-size:12px}.topbar{position:static;padding:0 22px;height:48px}
.topbar-version,.topbar .divider{display:none}
.main{padding:22px;min-height:calc(100vh - 108px)}.skip{left:12px}.mobile-menu{display:none!important}
.sidebar.open{transform:none}.mobile-nav-shade{display:none!important}
@media(max-width:760px){.sidebar{padding:7px;gap:4px;flex-wrap:wrap;transform:none!important}
 .nav{flex:1}.nav button,.sidebar-bottom button{padding:7px 9px;font-size:12px;gap:5px}
 .nav .icon{width:16px}.main{padding:15px}.topbar{padding:0 15px}}
"""


def render_quant_html(raw: bytes, token: str, nonce: str) -> bytes:
    """Adapt the verified resource in memory; never change accepted package bytes."""
    html = raw.decode("utf-8").replace("\r\n", "\n")
    if html.count("<script>") != 1 or html.count("let token='',pollTimer=null") != 1:
        raise ValueError("quant_html_adapter_source_mismatch")
    html = html.replace("<title>哈基米 · 离线量化</title>", "<title>量化任务与回测 · 哈基米交易 v2</title>")
    html = html.replace("</style>", _EMBEDDED_STYLE + "\n</style>", 1)
    html = html.replace('<div class="brand"><div class="brand-mark" aria-hidden="true">H</div><div><div class="brand-name">哈基米</div><div class="brand-sub">离线量化</div></div></div>', "")
    html = html.replace('aria-label="主导航"', 'aria-label="量化功能"')
    html = html.replace("fetch('/api/'+path", "fetch('/api/quant/'+path")
    html = html.replace("const unresolvedKey='hakimi-unresolved-'+location.origin", "const unresolvedKey='hakimi-quant-unresolved-'+location.origin")
    token_initialization = re.compile(r"^try\{const h=new URLSearchParams\(location\.hash\.slice\(1\)\).*?^const fmt=", re.MULTILINE | re.DOTALL)
    html, count = token_initialization.subn("const fmt=", html, count=1)
    if count != 1 or "fetch('/api/'+path" in html:
        raise ValueError("quant_html_adapter_source_mismatch")
    safe_token = json.dumps(token, ensure_ascii=True).replace("<", "\\u003c")
    html = html.replace("let token='',pollTimer=null", "document.currentScript?.remove();\nlet token=" + safe_token + ",pollTimer=null", 1)
    ui_path = Path(__file__).resolve().parents[1] / "static" / "terminal-quant-ui.js"
    judgment_path = ui_path.with_name("terminal-judgment-ui.js")
    exit_path = ui_path.with_name("terminal-exit-research-ui.js")
    insights_path = ui_path.with_name("terminal-insights-ui.js")
    ui_source = "\n".join(path.read_text(encoding="utf-8") for path in (judgment_path, exit_path, insights_path, ui_path)).replace("</script>", "<\\/script>")
    html = html.replace("程序版本", "股票回测内核版本")
    html = html.replace("共享资金演练目前通过安装目录中的", "共享资金演练保留在原命令行工具中。旧包中的")
    html = html.replace(" 使用。这里保留现有命令行能力；", " 是归档入口；日常继续使用当前交易窗口。")
    labels = "terminal_register_exit_experiment:'登记同入场出场研究',terminal_run_exit_experiment:'运行已登记出场研究',terminal_save_judgment:'保存判断与冻结依据',terminal_append_judgment_event:'追加复盘记录',terminal_import_core_input:'复用已导入行情',terminal_freeze_market:'保存当前行情快照',terminal_save_task:'保存原策略任务版本',terminal_set_task_state:'更改研究任务状态',terminal_run_task:'运行原策略回测',terminal_compare:'比较原策略结果',"
    html = html.replace("const ACTIONS={", "const ACTIONS={" + labels, 1)
    hook = ("\nwindow.installTerminalQuantUI({api,perform,esc,modal,closeDialog,showError,"
            "getSelectedCoreRun:()=>S.selectedRun,openCoreTask:async id=>{nav('tasks');await showTask(id);},"
            "openCoreRun:async id=>{S.selectedRun=id;nav('results');await loadRun(id);},"
            "openCoreTaskForm:async()=>{nav('tasks');await openTaskForm();},openCoreImport:async()=>{nav('inputs');await openImport();},"
            "initializeCoreExample:button=>dispatch('demo',button)});\n")
    ending = "})();\n</script>"
    if html.count(ending) != 1:
        raise ValueError("quant_terminal_hook_source_mismatch")
    html = html.replace(ending, hook + ending, 1)
    html = html.replace("<script>", '<script nonce="' + nonce + '">\n' + ui_source + "\n", 1)
    return html.encode("utf-8")


class QuantWorkspace:
    """Lazy same-origin routes for runtime/research-workspace.

    handle() returns False for unrelated routes. close() returns False while a
    durable operation is live, leaving ownership and the worker intact.
    """
    def __init__(self, runtime_dir, read_only=False, local_only=True, service_factory=None, mutation_guard=None):
        raw_runtime = Path(runtime_dir).expanduser().absolute()
        _no_links(raw_runtime)
        self.runtime_dir = raw_runtime.resolve()
        self.workspace = self.runtime_dir / "research-workspace"
        self.read_only = bool(read_only)
        self.local_only = bool(local_only)
        self._service_factory = service_factory
        self._mutation_guard = mutation_guard
        self._token = secrets.token_urlsafe(32)
        self._mutex = RLock()
        self._kernel = self._service = self._jobs = self._instance_lock = None
        self._closed = False

    def _ensure(self):
        with self._mutex:
            if self._closed:
                raise RuntimeError("quant_module_closed")
            if self._kernel is not None:
                return
            kernel = _load_kernel()
            _no_links(self.workspace)
            control = kernel.desktop.control_directory(self.workspace)
            _no_links(control)
            for child in control.rglob("*") if control.exists() else ():
                _no_links(child)
            _no_links(control / "server.lock")
            _no_links(control / "jobs")
            control.mkdir(parents=True, exist_ok=True)
            lock = kernel.desktop.InstanceLock(control / "server.lock")
            try:
                service = kernel.service(self.workspace)
                if self._service_factory is not None:
                    service = self._service_factory(service)
                jobs = kernel.desktop.Jobs(service, control / "jobs")
            except BaseException:
                lock.close()
                raise
            self._kernel, self._service, self._jobs = kernel, service, jobs
            self._instance_lock = lock

    @property
    def initialized(self):
        with self._mutex:
            return self._kernel is not None and not self._closed

    @property
    def pending(self):
        with self._mutex:
            if self._jobs is None:
                return False
            with self._jobs.lock:
                return bool(self._jobs.live)

    def close(self):
        with self._mutex:
            if self.pending:
                return False
            self._closed = True
            if self._jobs is not None:
                self._jobs.close()
            if self._instance_lock is not None:
                self._instance_lock.close()
                self._instance_lock = None
            return True

    def _boundary(self, handler, authenticated=True):
        address, port = handler.server.server_address[:2]
        try:
            server_is_local = ipaddress.ip_address(address).is_loopback
            client_is_local = ipaddress.ip_address(handler.client_address[0]).is_loopback
        except ValueError:
            server_is_local = client_is_local = False
        if not server_is_local or (self.local_only and not client_is_local):
            raise PermissionError("quant_loopback_required")
        host = ("[" + address + "]" if ":" in address else address) + ":" + str(port)
        origin = "http://" + host
        if handler.headers.get_all("Host", []) != [host]:
            raise PermissionError("host_not_allowed")
        origins = handler.headers.get_all("Origin", [])
        if origins and origins != [origin]:
            raise PermissionError("origin_not_allowed")
        fetch_sites = handler.headers.get_all("Sec-Fetch-Site", [])
        if len(fetch_sites) > 1 or (fetch_sites and fetch_sites[0] not in {"", "none", "same-origin"}):
            raise PermissionError("cross_site_request_rejected")
        if authenticated:
            tokens = handler.headers.get_all("X-Hakimi-Token", [])
            if len(tokens) != 1 or not secrets.compare_digest(tokens[0], self._token):
                raise PermissionError("session_token_required:请重新打开量化模块")
        if handler.command == "POST" and origins != [origin]:
            raise PermissionError("exact_origin_required")

    @staticmethod
    def _send(handler, status, body, *, html=False, nonce=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False, allow_nan=False, sort_keys=True).encode("utf-8")
        handler.send_response(status)
        handler.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.send_header("Cache-Control", "no-store")
        handler.send_header("X-Content-Type-Options", "nosniff")
        handler.send_header("Referrer-Policy", "no-referrer")
        handler.send_header("X-Frame-Options", "SAMEORIGIN" if html else "DENY")
        handler.send_header("Content-Security-Policy", "default-src 'none'; connect-src 'self'; img-src 'self' data:; "
                            "style-src 'unsafe-inline'; script-src " + ("'nonce-" + nonce + "'" if nonce else "'none'")
                            + "; base-uri 'none'; frame-ancestors " + ("'self'" if html else "'none'") + "; form-action 'none'")
        handler.end_headers()
        handler.wfile.write(body)

    def _answer(self, handler, data, status=200):
        self._send(handler, status, {"ok": True, "data": data})

    def _fail(self, handler, error, status=400):
        detail = str(error).replace(self._token, "[redacted]")[:2000]
        self._send(handler, status, {"ok": False, "error": {"code": type(error).__name__,
                   "message": "量化模块操作未完成，请核对输入或查看具体原因。", "detail": detail}})

    def handle(self, handler):
        parsed = urlsplit(handler.path)
        path = parsed.path
        if path not in {"/quant", "/quant/", "/api/quant"} and not path.startswith("/api/quant/"):
            return False
        try:
            is_page = path in {"/quant", "/quant/"}
            self._boundary(handler, authenticated=not is_page)
            if parsed.query:
                raise ValueError("quant_query_parameters_not_supported")
            if handler.command == "GET":
                self._ensure()
                if is_page:
                    nonce = secrets.token_urlsafe(20)
                    html = render_quant_html((self._kernel.root / "resources" / "desktop.html").read_bytes(), self._token, nonce)
                    self._send(handler, 200, html, html=True, nonce=nonce)
                    return True
                route = path.removeprefix("/api/quant/")
                if route == "jobs":
                    result = self._jobs.list()
                elif route.startswith("jobs/"):
                    result = self._jobs.get(unquote(route[5:]))
                else:
                    resource, _, identity = route.partition("/")
                    if resource not in _READ_RESOURCES:
                        self._fail(handler, ValueError("quant_route_not_found"), 404)
                        return True
                    result = self._service.read(resource, unquote(identity) if identity else None)
                    if resource == "status" and isinstance(result, dict):
                        result.update(version=self._kernel.version,
                                      log_path=str(self.runtime_dir / ".hakimi-ui"),
                                      session={"offline": True, "embedded": True, "read_only": self.read_only},
                                      product_workspace=str(self.runtime_dir))
                self._answer(handler, result)
                return True
            if handler.command != "POST":
                self._fail(handler, ValueError("quant_method_not_allowed"), 405)
                return True
            if self.read_only:
                self._fail(handler, PermissionError("runtime_is_read_only"), 423)
                return True
            if not path.startswith("/api/quant/actions/"):
                self._fail(handler, ValueError("quant_route_not_found"), 404)
                return True
            if handler.headers.get_all("Content-Type", []) not in [["application/json"], ["application/json; charset=utf-8"]]:
                raise ValueError("json_content_type_required")
            lengths = handler.headers.get_all("Content-Length", [])
            if len(lengths) != 1 or not lengths[0].isascii() or not lengths[0].isdigit() or handler.headers.get_all("Transfer-Encoding", []):
                raise ValueError("valid_content_length_required")
            length = int(lengths[0])
            if not 0 < length <= MAX_REQUEST:
                self._fail(handler, ValueError("request_too_large:上传文件请控制在16MB以内"), 413)
                return True
            handler.connection.settimeout(20)
            raw = handler.rfile.read(length)
            if len(raw) != length:
                raise ValueError("incomplete_request")
            payload = json.loads(raw, object_pairs_hook=_json_object,
                                 parse_constant=lambda value: (_ for _ in ()).throw(ValueError("finite_json_required")))
            _finite_json(payload)
            if type(payload) is not dict or set(payload) - {"payload", "request_id"}:
                raise ValueError("request_object_required")
            with self._mutex:
                if self._mutation_guard is not None:
                    current = self._mutation_guard()
                    if (not isinstance(current, dict) or current.get("schema_version") != "hakimi-runtime-build-v1"
                            or current.get("status") != "PASS" or current.get("restart_required") is not False):
                        raise RuntimeError("source_changed_restart_required:运行代码已变化，请正常重启原交易窗口后再保存或运行。")
                self._ensure()
                job = self._jobs.submit(path.removeprefix("/api/quant/actions/"), payload.get("payload", {}), payload.get("request_id"))
            self._answer(handler, job, 202)
        except PermissionError as error:
            self._fail(handler, error, 403)
        except FileNotFoundError as error:
            self._fail(handler, error, 404)
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as error:
            self._fail(handler, error)
        except Exception:
            logging.exception("Quant workspace request failed")
            self._fail(handler, RuntimeError("quant_internal_error"), 500)
        return True
