"""Build the original integrated terminal from local, locked Windows runtimes.

This is a separate candidate identity. It does not change the dev5 wheel/trial,
install shortcuts, copy user data, download anything, or start a server.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
from build_windows_trial import RUNTIMES, archive_members, canonical, extract_checked, inspect_wheel, require, sha, write_new

ROOT = Path(__file__).resolve().parents[1]
APP_FILES = ("main.js", "boot.html", "desktop-security-policy.js", "backend-runtime-contract.js",
             "desktop-lifecycle.js", "terminal-package-runtime.js")
BUILD_FILES = ("tools/build_windows_terminal.py", "tools/build_windows_trial.py", "tools/terminal_package_bootstrap.py",
               "tools/terminal_package_canonical.py", "tools/requirements.terminal.lock", "tools/terminal-dependency-hashes.json",
               "pyproject.toml", "setup.py", "requirements.research.lock")
BROKER_IDENTITY_PERMISSIONS = frozenset({"external_connection_allowed", "query_allowed", "submit_allowed",
    "cancel_allowed", "unlock_allowed", "automatic_retry", "automatic_resume", "automatic_mode_fallback",
    "user_authorization_granted"})


def regular(path):
    for entry in (path, *path.parents):
        info = entry.lstat()
        require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                "terminal_reparse_source_rejected")
    require(path.is_file(), "terminal_regular_source_required")
    return path.read_bytes()


def source_files(root):
    """Explicit installed components; never copy runtime/data/config.local files."""
    root = Path(root)
    selected = {}
    canonical_root = root / "src/hakimi_research"
    formal = set(json.loads(regular(canonical_root / "runtime-files.json"))["files"])
    for name in sorted(formal):
        require(not Path(name).is_absolute() and ".." not in Path(name).parts and "\\" not in name,
                "terminal_canonical_path_invalid")
        selected["components/canonical/hakimi_research/" + name] = canonical_root / name
    # Preserve the canonical wheel boundary and its original runtime manifest.
    # Terminal-only modules live in a separate, manifest-bound package portion.
    for path in sorted(canonical_root.rglob("*.py")):
        name = path.relative_to(canonical_root).as_posix()
        if "__pycache__" not in path.parts and name not in formal:
            selected["components/terminal-canonical/hakimi_research/" + name] = path
    original = root / "outputs/python_quant_bot"
    for directory in ("exchange_terminal", "assets", "vendor/research"):
        for path in sorted((original / directory).rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts or path.name == "_build_identity.json":
                continue
            relative = path.relative_to(original).as_posix()
            if path.name.endswith((".test.js", ".pyc")) or path.suffix not in {".py", ".js", ".html", ".css", ".json", ".lock", ".csv", ".ico", ".png", ".svg", ".woff", ".woff2", ".txt"}:
                continue
            selected["components/terminal/" + relative] = path
    selected["components/terminal/_canonical_source.py"] = root / "tools/terminal_package_canonical.py"
    selected["resources/app/terminal-bootstrap.py"] = root / "tools/terminal_package_bootstrap.py"
    selected["FIRST_USE.md"] = root / "docs/windows-original-terminal-first-use.md"
    for name in APP_FILES:
        selected["resources/app/" + name] = root / "outputs/hakimi_trade_electron" / name
    for path in sorted((root / "tools/terminal-notices").glob("*")):
        selected["notices/" + path.name] = path
    require("components/terminal/exchange_terminal/server.py" in selected, "terminal_original_server_missing")
    require("components/terminal-canonical/hakimi_research/terminal_config.py" in selected, "terminal_config_missing")
    return selected


def source_provenance(root, selected, allow_dirty):
    names = sorted(set(BUILD_FILES) | {path.relative_to(root).as_posix() for path in selected.values()})
    files = {name: sha(regular(root / name)) for name in names}
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root).decode().strip()
    require(bool(re.fullmatch("[0-9a-f]{40}", commit)), "terminal_git_commit_invalid")
    dirty = subprocess.check_output(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root).decode().strip()
    require(allow_dirty or not dirty, "terminal_final_candidate_requires_clean_committed_source")
    if not allow_dirty:
        for name, expected in files.items():
            require(sha(subprocess.check_output(["git", "show", commit + ":" + name], cwd=root)) == expected,
                    "terminal_source_not_committed:" + name)
    return dict(git=dict(commit=commit, status="DIRTY" if dirty else "CLEAN"), files_sha256=files,
                scope="EXACT_INSTALLED_TERMINAL_COMPONENTS_AND_BUILD_TOOLS", development_probe=allow_dirty)


def package_identity(package, *, expected_algorithm=None):
    """Use the component's own, already staged source-identity algorithm."""
    algorithm = regular(package / "source_identity.py")
    require(expected_algorithm is None or algorithm == expected_algorithm, "terminal_source_identity_algorithm_changed")
    spec = importlib.util.spec_from_file_location("_terminal_staged_source_identity", package / "source_identity.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.package_content_identity(package)


def generate_build_identities(output, root, provenance):
    """Mirror setup.py receipts from installed bytes; never assert VERIFIED.

    Frozen namespace and upstream release identity stay distinct from wrapper
    Git. Each component's own environment verifier checks this receipt later.
    """
    definitions = {name: sha(regular(root / name)) for name in
                   ("setup.py", "pyproject.toml", "tools/build_windows_terminal.py")}
    canonical_package = output / "components/canonical/hakimi_research"
    frozen_package = output / "components/terminal/vendor/research/hakimi_terminal_research"
    canonical_identity = package_identity(canonical_package, expected_algorithm=regular(root / "src/hakimi_research/source_identity.py"))
    require(canonical_identity == package_identity(root / "src/hakimi_research"), "terminal_canonical_staged_identity_changed")
    origin_path = output / "components/terminal/vendor/research/ORIGIN.json"
    origin = json.loads(regular(origin_path))
    frozen_algorithm = regular(root / "outputs/python_quant_bot/vendor/research/hakimi_terminal_research/source_identity.py")
    require(sha(frozen_algorithm) == origin["derived_file_sha256"]["source_identity.py"], "terminal_frozen_identity_algorithm_unaccepted")
    frozen_identity = package_identity(frozen_package, expected_algorithm=frozen_algorithm)
    adapter = ast.parse(regular(root / "outputs/python_quant_bot/exchange_terminal/services/quant_workspace.py"))
    accepted = [ast.literal_eval(node.value) for node in adapter.body if isinstance(node, ast.Assign)
                and any(isinstance(target, ast.Name) and target.id == "ACCEPTED_SOURCE_SHA256" for target in node.targets)]
    require(len(accepted) == 1 and origin["schema_version"] == "isolated-terminal-kernel-origin-v1"
            and origin["namespace"] == "hakimi_terminal_research"
            and frozen_identity["content_sha256"] == accepted[0] == origin["derived_content_sha256"]
            and frozen_identity["file_hashes"] == origin["derived_file_sha256"], "terminal_frozen_accepted_identity_changed")
    receipts = {}
    for name, package, identity, git in (
        ("canonical", canonical_package, canonical_identity, provenance["git"]),
        ("frozen", frozen_package, frozen_identity, dict(commit="", status="UNKNOWN")),
    ):
        receipt = dict(schema_version="research-build-source-v1", **identity, git=git,
                       build_definition_sha256=definitions, wrapper_build_commit=provenance["git"]["commit"],
                       wrapper_build_git_status=provenance["git"]["status"],
                       wrapper_build_scope="ORIGINAL_TERMINAL_INSTALLED_COMPONENT_PACKAGING")
        if name == "frozen":
            receipt["frozen_source_origin"] = {key: origin[key] for key in
                ("source_version", "source_commit", "source_content_sha256", "derived_content_sha256", "namespace", "transformation")}
            receipt["frozen_source_origin"]["origin_file_sha256"] = sha(regular(origin_path))
        destination = package / "_build_identity.json"
        write_new(destination, canonical(receipt) + b"\n")
        receipts[name] = dict(path=destination.relative_to(output).as_posix(), sha256=sha(regular(destination)),
                              content_sha256=identity["content_sha256"])
    return receipts


EXECUTION_PROBE = r'''
import importlib.util,json,logging,os,socket,sys
from pathlib import Path
from hashlib import sha256
root,temporary=map(lambda value:Path(value).resolve(),sys.argv[1:3])
def require(value,reason):
    if not value: raise RuntimeError(reason)
require(temporary.is_dir() and not temporary.is_relative_to(root),'execution_probe_requires_external_temporary_root')
def audit(event,args):
    if event in {'socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'}:
        raise RuntimeError('execution_probe_external_side_effect_rejected:'+event)
sys.addaudithook(audit)
os.environ.update(HAKIMI_RUNTIME_DIR=str(temporary/'legacy'),HAKIMI_QUANT_WORKSPACE_DIR=str(temporary/'quant'),
    HAKIMI_RESEARCH_HOME=str(temporary/'research'),FUTU_PY_APPDATA=str(temporary/'futu-sdk'),
    HAKIMI_LOCAL_ONLY='1',HAKIMI_RUNTIME_READ_ONLY='1',HAKIMI_QUANT_READ_ONLY='0',
    HAKIMI_LOAD_LOCAL_AI_ENV='0',HAKIMI_SKIP_LOCAL_AI_ENV='1')
spec=importlib.util.spec_from_file_location('_terminal_execution_bootstrap',root/'resources/app/terminal-bootstrap.py')
bootstrap=importlib.util.module_from_spec(spec);spec.loader.exec_module(bootstrap)
manifest=bootstrap.verify(root);bootstrap.initialize(root,manifest)
from exchange_terminal.services.quant_workspace import _load_kernel,ACCEPTED_SOURCE_SHA256
kernel=_load_kernel()
from hakimi_terminal_research import offline_app
from hakimi_terminal_research.environment import build_runtime_provenance
from hakimi_research.environment import build_runtime_provenance as canonical_provenance
for provenance in (build_runtime_provenance(),canonical_provenance()):
    require(provenance['source_identity']['status']=='BUILD_VERIFIED','execution_probe_source_unverified')
    require(provenance['environment_verified']['status']=='VERIFIED','execution_probe_dependencies_unverified')
require(build_runtime_provenance()['source_identity']['content_sha256']==ACCEPTED_SOURCE_SHA256,'execution_probe_frozen_identity_changed')
workspace=temporary/'new-explicit-synthetic-workspace'
require(not workspace.exists(),'execution_probe_workspace_must_be_new')
core=kernel.service(workspace)
calls=[0]
original=offline_app.run_strategy
def observed(*args,**kwargs):
    calls[0]+=1
    return original(*args,**kwargs)
offline_app.run_strategy=observed
initialized=core.mutate('initialize_demo',{})
require(initialized['initialized'],'execution_probe_example_not_saved')
require(json.loads((workspace/'workspace.json').read_bytes())['data_kind']=='SYNTHETIC_TEST','execution_probe_example_not_synthetic')
task=next(row for row in core.read('tasks')['items'] if row['name']=='price')
saved_task=core.mutate('copy_task',{'task_id':task['id'],'name':'package-explicit-synthetic'})
require(calls[0]==0 and not core.read('runs')['items'],'execution_probe_save_must_not_run')
saved=core.mutate('run_task',{'task_id':saved_task['id']})
require(calls[0]==1 and saved['operation']=='RUN_REQUEST_COMPLETED','execution_probe_requires_one_explicit_run')
def forbidden(*args,**kwargs): raise RuntimeError('execution_probe_read_must_not_recompute')
offline_app.run_strategy=forbidden
def inventory():
    return {p.relative_to(workspace).as_posix():(sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns)
            for p in workspace.rglob('*') if p.is_file()}
before=inventory()
run_manifest,report,snapshot=offline_app.verify_run(core._lookup('runs',saved['id']))
readback=core.read('runs',saved['id'])
require(snapshot.document['evidence_kind']=='SYNTHETIC_TEST','execution_probe_saved_snapshot_not_synthetic')
require(run_manifest['task_id']==saved_task['task_id'],'execution_probe_saved_task_identity_changed')
require(report['provenance']['source_identity']['status']=='BUILD_VERIFIED','execution_probe_saved_report_source_unverified')
require(before==inventory() and len(core.read('runs')['items'])==1,'execution_probe_read_changed_saved_state')
require(readback['id']==saved['id'],'execution_probe_readback_identity_changed')
external={name:str(module.__file__) for name,module in tuple(sys.modules.items()) if getattr(module,'__file__',None)
          and not str(module.__file__).startswith('<') and not Path(module.__file__).resolve().is_relative_to(root)}
require(not external,'execution_probe_imported_external_module')
require(all(value and Path(value).resolve().is_relative_to(root) for value in sys.path),'execution_probe_external_search_path')
bootstrap.verify(root)
logging.shutdown()
print(json.dumps(dict(status='VERIFIED_NEW_SYNTHETIC_RUN',bundle_id=manifest['bundle_id'],
    frozen_content_sha256=ACCEPTED_SOURCE_SHA256,synthetic_runs=1,market_data_runs=0,
    historical_replays=0,provider_calls=0,listening_servers=0,external_module_count=0,
    saved_task_id=saved_task['task_id'],run_id=run_manifest['run_id'],report_hash=report['report_hash'],
    evidence_kind='SYNTHETIC_TEST',save_computed=False,read_computed=False,read_changed_files=False,
    source_status='BUILD_VERIFIED',dependency_status='VERIFIED',temporary_workspace=True,
    private_python=str(Path(sys.executable).resolve()))))
'''


def probe_installed_execution(output):
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("PYTHON")
                   and key.upper() not in {"NODE_OPTIONS", "ELECTRON_RUN_AS_NODE", "CHROME_CRASHPAD_PIPE_NAME", "CHROME_CRASHPAD_SERVER_URL"}}
    with tempfile.TemporaryDirectory(prefix="hakimi-terminal-synthetic-run-") as directory:
        environment.update(HAKIMI_RUNTIME_DIR=str(Path(directory) / "legacy"),
                           HAKIMI_QUANT_WORKSPACE_DIR=str(Path(directory) / "quant"),
                           HAKIMI_RESEARCH_HOME=str(Path(directory) / "research"), FUTU_PY_APPDATA=str(Path(directory) / "futu-sdk"),
                           HAKIMI_LOCAL_ONLY="1", HAKIMI_RUNTIME_READ_ONLY="1", HAKIMI_QUANT_READ_ONLY="0",
                           HAKIMI_LOAD_LOCAL_AI_ENV="0", HAKIMI_SKIP_LOCAL_AI_ENV="1")
        result = subprocess.run([str(output / "runtime/python/python.exe"), "-I", "-S", "-B", "-X", "utf8",
                                 "-c", EXECUTION_PROBE, str(output), directory], cwd=directory, env=environment,
                                capture_output=True, text=True, encoding="utf-8", timeout=120)
    require(result.returncode == 0, "terminal_private_execution_probe_failed:" + result.stderr[-2400:])
    proof = json.loads(result.stdout)
    require(proof.get("status") == "VERIFIED_NEW_SYNTHETIC_RUN" and proof.get("synthetic_runs") == 1
            and proof.get("evidence_kind") == "SYNTHETIC_TEST"
            and all(proof.get(key) == 0 for key in ("market_data_runs", "historical_replays", "provider_calls", "listening_servers", "external_module_count"))
            and all(proof.get(key) is False for key in ("save_computed", "read_computed", "read_changed_files"))
            and proof.get("temporary_workspace") is True and proof.get("source_status") == "BUILD_VERIFIED"
            and proof.get("dependency_status") == "VERIFIED"
            and Path(proof.get("private_python", "")).resolve() == (output / "runtime/python/python.exe").resolve(),
            "terminal_private_execution_proof_invalid")
    return proof


def verify_runtime_archives(archives):
    for kind, path in archives.items():
        require(sha(regular(path)) == RUNTIMES[kind]["sha256"], "terminal_runtime_archive_hash_changed:" + kind)
        archive_members(path)
    with zipfile.ZipFile(archives["python"]) as archive:
        metadata = json.loads(archive.read("__install__.json"))
        require(metadata["sort-version"] == RUNTIMES["python"]["version"] and metadata["url"] == RUNTIMES["python"]["url"],
                "terminal_python_distribution_identity_changed")
        require(all(name in archive.namelist() for name in ("python.exe", "python314.dll", "LICENSE.txt", "vcruntime140.dll")),
                "terminal_python_distribution_incomplete")
    with zipfile.ZipFile(archives["electron"]) as archive:
        require(archive.read("version").decode().strip().lstrip("v") == RUNTIMES["electron"]["version"],
                "terminal_electron_version_changed")
        require(all(name in archive.namelist() for name in ("electron.exe", "LICENSE", "LICENSES.chromium.html")),
                "terminal_electron_distribution_incomplete")


def dependency_wheels(wheelhouse, root):
    lock = "\n".join((root / name).read_text() for name in ("requirements.research.lock", "tools/requirements.terminal.lock"))
    pins = dict(re.findall(r"^([a-z0-9-]+)==([^\s]+)$", lock, re.MULTILINE))
    hashes = json.loads(regular(root / "tools/terminal-dependency-hashes.json"))
    require(hashes["schema_version"] == "original-terminal-wheel-hashes-v1" and set(hashes["packages"]) == set(pins),
            "terminal_dependency_hash_lock_inventory_changed")
    wheels = []
    for path in sorted(wheelhouse.glob("*.whl")):
        info = inspect_wheel(path)
        require(info["name"] in pins and info["version"] == pins[info["name"]], "terminal_dependency_not_locked")
        require(hashes["packages"][info["name"]] == dict(version=info["version"], filename=path.name, sha256=info["sha256"]),
                "terminal_dependency_hash_lock_changed")
        with zipfile.ZipFile(path) as archive:
            wheel_metadata = next(name for name in archive.namelist() if name.endswith(".dist-info/WHEEL"))
            tags = re.findall(r"^Tag: (.+)$", archive.read(wheel_metadata).decode(), re.MULTILINE)
        def supported(tag):
            parts = tag.split("-")
            if len(parts) != 3:
                return False
            interpreter, abi, platform = parts
            return (platform == "any" and abi == "none" and any(p in {"py3", "py314"} for p in interpreter.split("."))) or (
                platform == "win_amd64" and (interpreter == "cp314" and abi == "cp314"
                or abi == "abi3" and interpreter.startswith("cp3") and 2 <= int(interpreter[3:]) <= 14))
        require(any(supported(tag.strip()) for tag in tags), "terminal_dependency_platform_changed")
        if not info["license_files"]:
            notice_name = info["name"] + "-" + info["version"]
            notice = root / "tools/terminal-notices" / (notice_name + "-LICENSE.txt")
            receipt = json.loads(regular(root / "tools/terminal-notices" / (notice_name + "-source.json")))
            require(sha(regular(notice)) == receipt["sha256"] and receipt["component"] == info["name"]
                    and receipt["version"] == info["version"], "terminal_supplementary_notice_identity_changed")
            info["supplementary_notice"] = "notices/" + notice.name
        require(not any(name.endswith(".pth") or Path(name).name in {"sitecustomize.py", "usercustomize.py"}
                        for name in archive_members(path)), "terminal_dependency_startup_injection_rejected")
        wheels.append((path, info))
    require(len(wheels) == len(pins) and {info["name"] for _, info in wheels} == set(pins), "terminal_dependency_inventory_changed")
    return wheels


def probe_installation(output):
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("PYTHON")
           and key.upper() not in {"NODE_OPTIONS", "ELECTRON_RUN_AS_NODE"}}
    with tempfile.TemporaryDirectory(prefix="hakimi-terminal-probe-") as directory:
        env.update(HAKIMI_RUNTIME_DIR=directory, HAKIMI_QUANT_WORKSPACE_DIR=directory,
                   HAKIMI_LOCAL_ONLY="1", HAKIMI_RUNTIME_READ_ONLY="1",
                   HAKIMI_QUANT_READ_ONLY="1", HAKIMI_LOAD_LOCAL_AI_ENV="0", HAKIMI_SKIP_LOCAL_AI_ENV="1")
        result = subprocess.run([str(output / "runtime/python/python.exe"), "-I", "-S", "-B", "-X", "utf8",
                                 str(output / "resources/app/terminal-bootstrap.py"), "--probe"],
                                cwd=directory, env=env, capture_output=True, text=True, encoding="utf-8", timeout=90)
    require(result.returncode == 0, "terminal_private_runtime_probe_failed:" + result.stderr[-2400:])
    return json.loads(result.stdout)


def probe_broker_package_identity(output, *, development=False):
    """New private identity-only subprocess, separate from SDK/execution probes."""
    env = {key: value for key, value in os.environ.items() if not key.upper().startswith("PYTHON")
           and key.upper() not in {"NODE_OPTIONS", "ELECTRON_RUN_AS_NODE", "CHROME_CRASHPAD_PIPE_NAME"}}
    with tempfile.TemporaryDirectory(prefix="hakimi-broker-loader-probe-") as directory:
        env.update(HAKIMI_RUNTIME_DIR=directory, HAKIMI_QUANT_WORKSPACE_DIR=directory,
                   HAKIMI_LOCAL_ONLY="1", HAKIMI_RUNTIME_READ_ONLY="1", HAKIMI_QUANT_READ_ONLY="1",
                   HAKIMI_LOAD_LOCAL_AI_ENV="0", HAKIMI_SKIP_LOCAL_AI_ENV="1",
                   FUTU_PY_APPDATA=str(Path(directory) / "unused-futu"))
        result = subprocess.run([str(output / "runtime/python/python.exe"), "-I", "-S", "-B", "-X", "utf8",
                                 str(output / "resources/app/terminal-bootstrap.py"), "--broker-identity-probe"],
                                cwd=directory, env=env, capture_output=True, text=True, encoding="utf-8", timeout=90)
    require(result.returncode == 0, "terminal_broker_identity_probe_failed:" + result.stderr[-2400:])
    proof = json.loads(result.stdout)
    expected = "DEVELOPMENT_PACKAGE_NOT_ELIGIBLE" if development else "PACKAGE_IDENTITY_ONLY_VERIFIED"
    require(proof.get("status") == expected and proof.get("runtime_compatibility") == "NOT_VERIFIED"
            and all(proof.get(key) is False for key in ("sdk_imported", "server_imported"))
            and all(type(proof.get(key)) is int and proof[key] == 0 for key in ("external_calls", "economic_runs", "business_files_created"))
            and type(proof.get("permissions")) is dict and set(proof["permissions"]) == BROKER_IDENTITY_PERMISSIONS
            and all(value is False for value in proof["permissions"].values()), "terminal_broker_identity_proof_invalid")
    for key, relative in (("loader_module", "terminal_broker_package_loader.py"), ("plan_module", "terminal_broker_execution_plan.py")):
        require(Path(proof.get(key, "")).resolve() == output / "components/terminal/exchange_terminal/services" / relative,
                "terminal_broker_identity_import_path_changed")
    require(type(proof.get("modes")) is dict and set(proof["modes"]) ==
            (set() if development else {"OFFICIAL_SIMULATION", "LIVE_CANDIDATE"}), "terminal_broker_identity_modes_invalid")
    for mode, value in proof["modes"].items():
        require(type(value) is dict and value.get("schema_version") == "hakimi-broker-package-load-v1"
                and value.get("status") == "PACKAGED_IDENTITY_MATCHED" and value.get("mode") == mode
                and value.get("package", {}).get("bundle_id") == proof.get("bundle_id")
                and value.get("runtime_compatibility") == "NOT_VERIFIED"
                and "sdk" in value and "adapter" in value and type(value.get("missing_capabilities")) is list
                and value.get("permissions") == proof["permissions"], "terminal_broker_identity_mode_proof_invalid")
    return proof


def build(python_archive, electron_archive, wheelhouse, output, *, version="0.7.0.dev1", root=ROOT, allow_dirty=False, make_archive=True):
    root, output, wheelhouse = Path(root).resolve(), Path(output).resolve(), Path(wheelhouse).resolve()
    archive_path = Path(str(output) + ".zip")
    require(os.name == "nt", "terminal_build_requires_windows")
    require(not output.exists() and not archive_path.exists(), "terminal_output_exists_use_new_destination")
    require(not output.is_relative_to(root), "terminal_output_must_be_outside_checkout")
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+(?:\.dev\d+)?", version)), "terminal_candidate_version_invalid")
    selected = source_files(root)
    provenance = source_provenance(root, selected, allow_dirty)
    archives = dict(python=Path(python_archive).resolve(), electron=Path(electron_archive).resolve())
    verify_runtime_archives(archives)
    wheels = dependency_wheels(wheelhouse, root)
    try:
        extract_checked(archives["python"], output / "runtime/python")
        extract_checked(archives["electron"], output, transform=lambda name: "HakimiTrade.exe" if name == "electron.exe" else name)
        for source, _ in wheels:
            extract_checked(source, output / "runtime/python/Lib/site-packages")
        for destination, source in selected.items():
            raw = regular(source)
            require(sha(raw) == provenance["files_sha256"][source.relative_to(root).as_posix()], "terminal_source_changed_during_staging")
            write_new(output / destination, raw)
        component_build_identities = generate_build_identities(output, root, provenance)
        write_new(output / "resources/app/package.json", canonical(dict(name="hakimi-original-terminal", productName="哈基米交易", version=version, main="main.js")) + b"\n")
        notices = []
        for kind, source in archives.items():
            prefix = "runtime/python/" if kind == "python" else ""
            paths = [prefix + name for name in archive_members(source) if any(word in name.lower() for word in ("license", "licence", "notice", "copying"))]
            notices.append(dict(component=kind, version=RUNTIMES[kind]["version"], source=RUNTIMES[kind]["url"], notices=paths))
        notices.extend(dict(component=info["name"], version=info["version"], source_wheel_sha256=info["sha256"],
                            notices=["runtime/python/Lib/site-packages/" + name for name in info["license_files"]]
                            + ([info["supplementary_notice"]] if info.get("supplementary_notice") else [])) for _, info in wheels)
        write_new(output / "THIRD-PARTY-NOTICES.json", canonical(dict(components=notices, original_notice_bytes_retained=True,
                    project_license_grant="NO_NEW_PROJECT_LICENSE_GRANTED_BY_THIS_INDEX")) + b"\n")
        write_new(output / "README.txt", ("哈基米交易 " + version + " · 原终端候选\n\n"
            "将整个文件夹保留在一起，双击 HakimiTrade.exe。包内已包含 Python 和 Electron。\n"
            "此版本从原终端进入量化研究；程序和旧工作台的版本身份分别保留。\n"
            "首次使用与旧结果说明见同目录 FIRST_USE.md。保存后明确点击“运行这次回测”；读取结果不会重算。\n"
            "数据位于当前用户 LocalAppData/HakimiTradeTerminal/workspaces/default/runtime。\n"
            "不要覆盖旧安装或旧数据。此包是未签名候选；独立 Windows 与真人验收另行记录。\n").encode())
        verify_runtime_archives(archives)
        require(source_provenance(root, selected, allow_dirty) == provenance, "terminal_source_changed_during_build")
        for source, info in wheels:
            require(sha(regular(source)) == info["sha256"], "terminal_dependency_changed_during_build")
        files = {path.relative_to(output).as_posix(): sha(regular(path)) for path in sorted(output.rglob("*")) if path.is_file()}
        core = dict(schema_version="hakimi-original-terminal-v1", platform="win32-x64", version=version,
                    scope="UNSIGNED_ORIGINAL_TERMINAL_CANDIDATE", desktop_entry="HakimiTrade.exe",
                    python="runtime/python/python.exe", bootstrap="resources/app/terminal-bootstrap.py",
                    backend_entry="exchange_terminal.server", primary_route="/?workspace=quant", quant_route="/quant/",
                    runtimes=RUNTIMES, dependency_wheels=[info for _, info in wheels], source_provenance=provenance,
                    files=files, no_external_runtime_required=True, clean_windows_acceptance="NOT_PERFORMED",
                    native_user_flow_acceptance="NOT_PERFORMED", component_build_identities=component_build_identities,
                    economic_runs_during_packaging=1, economic_run_scope="ONE_NEW_SYNTHETIC_TEST_FIXTURE_ONLY",
                    historical_replays_during_packaging=0)
        manifest = {**core, "bundle_id": sha(canonical(core))}
        write_new(output / "terminal-manifest.json", canonical(manifest) + b"\n")
        probe = probe_installation(output)
        require(probe["bundle_id"] == manifest["bundle_id"] and probe["status"] == "VERIFIED", "terminal_probe_identity_changed")
        broker_identity_probe = probe_broker_package_identity(output, development=provenance["development_probe"])
        require(broker_identity_probe["bundle_id"] == manifest["bundle_id"], "terminal_broker_identity_probe_identity_changed")
        execution_probe = probe_installed_execution(output)
        require(execution_probe["bundle_id"] == manifest["bundle_id"], "terminal_execution_probe_identity_changed")
        if make_archive:
            with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for name in sorted([*files, "terminal-manifest.json"]):
                    archive.write(output / name, name)
        return dict(status="BUILT_AND_PRIVATE_RUNTIME_VERIFIED", output=str(output), bundle_id=manifest["bundle_id"],
                    archive=str(archive_path) if make_archive else None, archive_sha256=sha(archive_path.read_bytes()) if make_archive else None,
                    source_git=provenance["git"], probe=probe, broker_identity_probe=broker_identity_probe, execution_probe=execution_probe,
                    clean_windows_acceptance="NOT_PERFORMED", new_economic_runs=1, synthetic_runs=1,
                    market_data_runs=0, historical_replays=0)
    except Exception as error:
        # Retain all partial bytes, but an added marker makes the manifest fail
        # closed, so a failed probe cannot launch a seemingly valid candidate.
        write_new(output / "BUILD-STOPPED.json", canonical(dict(status="STOPPED", reason=str(error), original_artifacts_retained=True)) + b"\n")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("python-archive", "electron-archive", "wheelhouse", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--version", default="0.7.0.dev1")
    parser.add_argument("--allow-dirty-probe", action="store_true", help="Label exact dirty bytes as development probe, never a clean candidate")
    parser.add_argument("--no-archive", action="store_true")
    args = parser.parse_args()
    print(json.dumps(build(args.python_archive, args.electron_archive, args.wheelhouse, args.output,
                          version=args.version, allow_dirty=args.allow_dirty_probe, make_archive=not args.no_archive), ensure_ascii=False))


if __name__ == "__main__":
    main()
