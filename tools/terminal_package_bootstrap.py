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


def require(value, reason):
    if not value:
        raise RuntimeError(reason)


def no_links(path):
    for entry in (path, *path.parents):
        info = entry.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "terminal_reparse_path_rejected")


def verify(root):
    no_links(root)
    manifest = json.loads((root / "terminal-manifest.json").read_bytes())
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
    return manifest


def initialize(root, manifest):
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
    return component


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
    else:
        initialize(root, manifest)
        from exchange_terminal.server import main as server_main
        server_main()


if __name__ == "__main__":
    main()
