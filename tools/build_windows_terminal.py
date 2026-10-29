"""Build the original integrated terminal from local, locked Windows runtimes.

This is a separate candidate identity. It does not change the dev5 wheel/trial,
install shortcuts, copy user data, download anything, or start a server.
"""
from __future__ import annotations

import argparse
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
               "pyproject.toml", "requirements.research.lock")


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
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(original).as_posix()
            if path.name.endswith((".test.js", ".pyc")) or path.suffix not in {".py", ".js", ".html", ".css", ".json", ".lock", ".csv", ".ico", ".png", ".svg", ".woff", ".woff2", ".txt"}:
                continue
            selected["components/terminal/" + relative] = path
    selected["components/terminal/_canonical_source.py"] = root / "tools/terminal_package_canonical.py"
    selected["resources/app/terminal-bootstrap.py"] = root / "tools/terminal_package_bootstrap.py"
    selected["FIRST_USE.md"] = root / "docs/windows-original-terminal-candidate.md"
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
                    native_user_flow_acceptance="NOT_PERFORMED", economic_runs_during_packaging=0)
        manifest = {**core, "bundle_id": sha(canonical(core))}
        write_new(output / "terminal-manifest.json", canonical(manifest) + b"\n")
        probe = probe_installation(output)
        require(probe["bundle_id"] == manifest["bundle_id"] and probe["status"] == "VERIFIED", "terminal_probe_identity_changed")
        if make_archive:
            with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                for name in sorted([*files, "terminal-manifest.json"]):
                    archive.write(output / name, name)
        return dict(status="BUILT_AND_PRIVATE_RUNTIME_VERIFIED", output=str(output), bundle_id=manifest["bundle_id"],
                    archive=str(archive_path) if make_archive else None, archive_sha256=sha(archive_path.read_bytes()) if make_archive else None,
                    source_git=provenance["git"], probe=probe, clean_windows_acceptance="NOT_PERFORMED", new_economic_runs=0)
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
