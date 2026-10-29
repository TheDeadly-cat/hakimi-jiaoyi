"""Private CPython entry for the original terminal, launched with -I -S -B.

The installed source-layout binding belongs to this component, not to the
historical research wheel or frozen kernel. No source repository is inferred.
"""
from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import stat
import sys
import tempfile

_VERIFIED_PACKAGE = None
_ACTIVATED_LOADER = None
_LOADER_MODULE = "exchange_terminal.services.terminal_broker_package_loader"
_LOADER_PATH = "components/terminal/exchange_terminal/services/terminal_broker_package_loader.py"


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def no_links(path):
    for entry in (path, *path.parents):
        info = entry.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "terminal_reparse_path_rejected")


def verify(root):
    global _VERIFIED_PACKAGE
    _VERIFIED_PACKAGE = None
    no_links(root)
    root = Path(root).resolve(strict=True)
    raw_manifest = (root / "terminal-manifest.json").read_bytes()
    manifest = json.loads(raw_manifest)
    identity = manifest.pop("bundle_id")
    encoded = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    require(manifest["schema_version"] == "hakimi-original-terminal-v1"
            and identity == hashlib.sha256(encoded).hexdigest(), "terminal_manifest_identity_invalid")
    manifest["bundle_id"] = identity
    observed = {}
    for entry in root.rglob("*"):
        no_links(entry)
        if entry.is_file() and entry.relative_to(root).as_posix() != "terminal-manifest.json":
            observed[entry.relative_to(root).as_posix()] = hashlib.sha256(entry.read_bytes()).hexdigest()
    require(observed == manifest["files"], "terminal_program_inventory_or_hash_changed")
    require((root / "terminal-manifest.json").read_bytes() == raw_manifest,
            "terminal_manifest_changed_during_verification")
    # Keep the same verification's immutable bytes; environment display fields
    # are not a substitute for this private bootstrap handoff.
    _VERIFIED_PACKAGE = (str(root), raw_manifest)
    return manifest


def initialize(root, manifest):
    try:
        return _initialize_verified(root, manifest)
    except Exception:
        if _ACTIVATED_LOADER is not None:
            _ACTIVATED_LOADER._invalidate_bootstrap_anchor()
        raise


def _initialize_verified(root, manifest):
    global _ACTIVATED_LOADER
    root = Path(root).resolve(strict=True)
    require(_VERIFIED_PACKAGE is not None and _VERIFIED_PACKAGE[0] == str(root)
            and json.loads(_VERIFIED_PACKAGE[1]) == manifest, "terminal_same_verification_required")
    runtime = root / "runtime" / "python"
    require(sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode,
            "terminal_isolated_python_flags_required")
    require(Path(sys.executable).resolve() == runtime / "python.exe"
            and Path(sys.prefix).resolve() == runtime and Path(sys.base_prefix).resolve() == runtime,
            "terminal_private_interpreter_required")
    require(sys.version.split()[0] == manifest["runtimes"]["python"]["version"], "terminal_python_version_changed")
    require(all(value and Path(value).resolve().is_relative_to(runtime) for value in sys.path),
            "terminal_external_python_search_path")
    component = root / "components" / "terminal"
    canonical = root / "components" / "canonical"
    supplemental = root / "components" / "terminal-canonical" / "hakimi_research"
    site = runtime / "Lib" / "site-packages"
    sys.path[:0] = [str(component), str(canonical), str(site)]
    import hakimi_research
    import hakimi_research.source_layout as layout
    require(Path(hakimi_research.__file__).resolve() == canonical / "hakimi_research" / "__init__.py",
            "terminal_canonical_import_shadowed")
    hakimi_research.__path__.append(str(supplemental))
    layout.LEGACY_PROJECT_ROOT = component
    require(layout.REPOSITORY_ROOT is None, "terminal_repository_layout_not_allowed")
    os.environ["HAKIMI_TERMINAL_PACKAGE_ID"] = manifest["bundle_id"]
    os.environ["HAKIMI_TERMINAL_PACKAGE_VERSION"] = manifest["version"]
    os.environ["HAKIMI_TERMINAL_BUILD_COMMIT"] = manifest["source_provenance"]["git"]["commit"]
    require(os.environ.get("HAKIMI_RUNTIME_DIR"), "terminal_writable_workspace_required")
    workspace = Path(os.environ["HAKIMI_RUNTIME_DIR"]).resolve()
    require(not workspace.is_relative_to(root), "terminal_workspace_inside_program_rejected")
    _activate_verified_loader(root, manifest)
    return component


def _activate_verified_loader(root, manifest):
    global _ACTIVATED_LOADER
    require(_VERIFIED_PACKAGE is not None and _VERIFIED_PACKAGE[0] == str(root)
            and json.loads(_VERIFIED_PACKAGE[1]) == manifest, "terminal_same_verification_required")
    loader_path = root / _LOADER_PATH
    no_links(loader_path)
    require(hashlib.sha256(loader_path.read_bytes()).hexdigest() == manifest["files"].get(_LOADER_PATH),
            "terminal_package_loader_bytes_changed")
    loader = importlib.import_module(_LOADER_MODULE)
    require(Path(loader.__file__).resolve() == loader_path
            and hashlib.sha256(loader_path.read_bytes()).hexdigest() == manifest["files"][_LOADER_PATH],
            "terminal_package_loader_import_shadowed")
    _ACTIVATED_LOADER = loader
    # Install last: failed private-interpreter/path initialization grants no
    # broker package identity. No SDK, server or data service is imported here.
    loader._install_bootstrap_anchor(root, _VERIFIED_PACKAGE[1])


def run_broker_identity_probe(root, manifest):
    """Separate identity-only proof; the older --probe still imports the SDK."""
    def audit(event, args):
        if event in {"socket.connect", "socket.bind", "socket.getaddrinfo", "subprocess.Popen", "sqlite3.connect", "os.system"}:
            raise RuntimeError("terminal_broker_identity_probe_io_rejected:" + event)
        if event == "import" and (args[0] == "futu" or args[0].startswith("futu.")):
            raise RuntimeError("terminal_broker_identity_probe_sdk_import_rejected")
    sys.addaudithook(audit)
    with tempfile.TemporaryDirectory(prefix="hakimi-broker-identity-probe-") as directory:
        os.environ.update(HAKIMI_LOCAL_ONLY="1", HAKIMI_RUNTIME_READ_ONLY="1", HAKIMI_QUANT_READ_ONLY="1",
                          HAKIMI_LOAD_LOCAL_AI_ENV="0", HAKIMI_SKIP_LOCAL_AI_ENV="1",
                          HAKIMI_RUNTIME_DIR=directory, HAKIMI_QUANT_WORKSPACE_DIR=directory,
                          FUTU_PY_APPDATA=str(Path(directory) / "unused-futu"))
        initialize(root, manifest)
        loader = _ACTIVATED_LOADER
        from exchange_terminal.services import terminal_broker_execution_plan as plan
        require(Path(plan.__file__).resolve() == root / "components/terminal/exchange_terminal/services/terminal_broker_execution_plan.py",
                "terminal_broker_plan_import_shadowed")
        # Dirty development builds remain usable as development probes, but
        # cannot produce the clean-package identity required by broker plans.
        development = manifest["source_provenance"].get("development_probe") is True
        modes = {} if development else {mode: loader.load_broker_runtime_identity(mode).as_dict() for mode in loader.DESCRIPTORS}
        require("exchange_terminal.server" not in sys.modules
                and not any(name == "futu" or name.startswith("futu.") for name in sys.modules),
                "terminal_identity_probe_imported_runtime_service_or_sdk")
        require(not list(Path(directory).rglob("*")), "terminal_identity_probe_wrote_business_data")
        return {"status": "DEVELOPMENT_PACKAGE_NOT_ELIGIBLE" if development else "PACKAGE_IDENTITY_ONLY_VERIFIED",
                "bundle_id": manifest["bundle_id"], "modes": modes,
                "loader_module": str(Path(loader.__file__).resolve()), "plan_module": str(Path(plan.__file__).resolve()),
                "runtime_compatibility": "NOT_VERIFIED", "sdk_imported": False, "server_imported": False,
                "external_calls": 0, "economic_runs": 0, "business_files_created": 0,
                "permissions": dict(plan.PERMISSIONS)}


def probe(root, manifest):
    # Importing the server establishes resources/contracts without listening or
    # running a strategy. Probe data remains outside the immutable program.
    import numpy
    import pandas
    import exchange_calendars
    import cryptography
    import google.protobuf
    import simplejson
    import Crypto
    from exchange_terminal import server
    from exchange_terminal.services.quant_workspace import _load_kernel
    from hakimi_research.product_capabilities import build_product_capability_catalog
    require(Path(server.RUNTIME_DIR).resolve() == Path(os.environ["HAKIMI_RUNTIME_DIR"]).resolve()
            and Path(server.QUANT_WORKSPACE.runtime_dir).resolve() == Path(os.environ["HAKIMI_QUANT_WORKSPACE_DIR"]).resolve(),
            "terminal_probe_workspace_not_isolated")
    kernel = _load_kernel()
    catalog = build_product_capability_catalog()
    sessions = exchange_calendars.get_calendar("XNYS").sessions_in_range("2026-10-01", "2026-10-28")
    require(len(sessions) > 0, "terminal_stock_calendar_unavailable")
    # Futu import is local only; its default appdata is redirected to disposable
    # probe storage, and no quote context or external connection is created.
    from exchange_terminal.market_data.futu import import_futu_sdk
    sdk, _ = import_futu_sdk()
    require(sdk is not None, "terminal_broker_sdk_import_failed")
    resources = [server.STATIC_DIR / "index.html", server.STATIC_DIR / "terminal-quant-ui.js",
                 kernel.root / "resources" / "desktop.html"]
    require(all(path.is_file() for path in resources), "terminal_required_resource_missing")
    foreign = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if filename and not str(filename).startswith("<") and not Path(filename).resolve().is_relative_to(root):
            foreign[name] = str(filename)
    require(not foreign, "terminal_imported_module_outside_bundle")
    installed = {info["name"]: importlib.metadata.version(info["name"]) for info in manifest["dependency_wheels"]}
    require(all(installed[info["name"]] == info["version"] for info in manifest["dependency_wheels"]),
            "terminal_dependency_version_changed")
    require(all(value and Path(value).resolve().is_relative_to(root) for value in sys.path),
            "terminal_dependency_added_external_search_path")
    return dict(status="VERIFIED", bundle_id=manifest["bundle_id"], version=manifest["version"],
                python=str(Path(sys.executable).resolve()), python_version=sys.version.split()[0],
                import_search_paths=sys.path, terminal_module=str(Path(server.__file__).resolve()),
                canonical_repository=None, frozen_kernel_version=kernel.version,
                frozen_kernel_root=str(kernel.root), capability_catalog_loaded=bool(catalog),
                numpy=numpy.__version__, pandas=pandas.__version__, external_module_count=len(foreign),
                calendar_version=exchange_calendars.__version__, stock_calendar_sessions=len(sessions),
                broker_sdk_available=True, cryptography_version=cryptography.__version__,
                installed_dependency_versions=installed,
                economic_runs=0, listening_servers=0)


def run_probe(root, manifest):
    # A directly invoked --probe is isolated too: never trust inherited data
    # roots, even when the builder has already provided a disposable cwd.
    with tempfile.TemporaryDirectory(prefix="hakimi-terminal-private-probe-") as directory:
        os.environ.update(HAKIMI_LOCAL_ONLY="1", HAKIMI_RUNTIME_READ_ONLY="1", HAKIMI_QUANT_READ_ONLY="1",
                          HAKIMI_LOAD_LOCAL_AI_ENV="0", HAKIMI_SKIP_LOCAL_AI_ENV="1",
                          HAKIMI_RUNTIME_DIR=directory, HAKIMI_QUANT_WORKSPACE_DIR=directory,
                          FUTU_PY_APPDATA=str(Path(directory) / "futu-sdk"))
        try:
            initialize(root, manifest)
            return {**probe(root, manifest), "probe_workspace_temporary": True}
        finally:
            # Broker import may hold a log file open on Windows. No broker
            # connection is created; release logging handles before cleanup.
            logging.shutdown()


def main():
    root = Path(__file__).resolve().parents[2]
    manifest = verify(root)
    if sys.argv[1:] == ["--probe"]:
        print(json.dumps(run_probe(root, manifest), ensure_ascii=False))
    elif sys.argv[1:] == ["--broker-identity-probe"]:
        print(json.dumps(run_broker_identity_probe(root, manifest), ensure_ascii=False))
    else:
        initialize(root, manifest)
        from exchange_terminal.server import main as server_main
        server_main()


if __name__ == "__main__":
    main()
