"""Prepare a local Windows desktop entry from an exact accepted installation.

This does not install software, copy user records, or replace an existing entry.
The copied launcher checks the installation and frozen desktop files on every use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


SCHEMA = "research-local-desktop-v1"
DESKTOP_FILES = ("research-main.js", "desktop-security-policy.js")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _clean_env():
    env = dict(os.environ)
    for name in ("PYTHONPATH", "PYTHONHOME", "ELECTRON_RUN_AS_NODE", "NODE_OPTIONS"):
        env.pop(name, None)
    env.update(PYTHONNOUSERSITE="1", PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    return env


def _probe_installation(python):
    code = """
import importlib.metadata, json, pathlib, sys
import hakimi_research
from hakimi_research.environment import build_runtime_provenance
p = build_runtime_provenance()
s, e = p['source_identity'], p['environment_verified']
package = pathlib.Path(hakimi_research.__file__).resolve().parent
print(json.dumps(dict(
    version=importlib.metadata.version('hakimi-research'),
    source_status=s['status'], source_sha256=s['content_sha256'],
    build_receipt=s.get('build_receipt'), environment_status=e['status'],
    lock_sha256=e['lock_sha256'], python=str(pathlib.Path(sys.executable).resolve()),
    package_directory=str(package), isolated_venv=sys.prefix != sys.base_prefix,
    package_inside_venv=package.is_relative_to(pathlib.Path(sys.prefix).resolve())
), ensure_ascii=True))
"""
    result = subprocess.run([str(python), "-I", "-B", "-c", code], capture_output=True,
                            text=True, encoding="utf-8", env=_clean_env(), timeout=30)
    _require(result.returncode == 0, "无法核对已安装候选，请检查该独立 Python 环境。")
    return json.loads(result.stdout)


def _check_installation(actual, expected, python):
    _require(actual.get("isolated_venv") is True and actual.get("package_inside_venv") is True,
             "需要普通安装的独立环境，不能使用源码目录或系统包。")
    _require(Path(actual.get("python", "")).resolve() == Path(python).resolve(), "实际 Python 与入口绑定不一致。")
    for key in ("version", "source_status", "source_sha256", "build_receipt", "environment_status", "lock_sha256"):
        _require(actual.get(key) == expected.get(key), f"已安装候选身份不匹配：{key}；请保留原入口并重新交付新候选。")


def _cmd(python):
    value = str(python)
    _require(not any(c in value for c in '\r\n"'), "Python 路径不能包含换行或引号。")
    # No CALL or delayed expansion: user-data paths are read from JSON in Python.
    value = value.replace("%", "%%")
    return ("@echo off\r\nsetlocal DisableDelayedExpansion\r\nchcp 65001 >nul\r\n"
            f'"{value}" -I -B "%~dp0launch_workbench.py" --launch\r\n'
            "if errorlevel 1 (\r\n  echo 工作台没有启动，请保留上方错误并核对交付目录。\r\n  pause\r\n  exit /b 1\r\n)\r\n")


def prepare(acceptance, electron, workspace, output, *, python=None):
    acceptance, electron = Path(acceptance).resolve(), Path(electron).resolve()
    workspace, output = Path(workspace).resolve(), Path(output).resolve()
    _require(not output.exists(), "桌面交付目录已存在，不能覆盖。请指定新目录。")
    _require(electron.is_file() and electron.suffix.lower() == ".exe", "需要已有的 Electron 可执行文件。")
    _require(not workspace.exists() or workspace.is_dir(), "数据工作区必须是目录。")
    receipt = json.loads(acceptance.read_text(encoding="utf-8-sig"))
    python = Path(python or receipt["python"]).resolve()
    _require(python.is_file(), "验收记录绑定的 Python 不存在。")
    source = receipt["installed_runtime"]["source_identity"]
    environment = receipt["installed_runtime"]["environment_verified"]
    wheel = Path(receipt["wheel"])
    expected = dict(version=wheel.name.split("-")[1], source_status="BUILD_VERIFIED",
                    source_sha256=source["content_sha256"], build_receipt=source["build_receipt"],
                    environment_status="VERIFIED", lock_sha256=environment["lock_sha256"])
    _require(expected["build_receipt"].get("git", {}).get("status") == "CLEAN", "日常候选需要 CLEAN 构建回执。")
    actual = _probe_installation(python)
    _check_installation(actual, expected, python)
    desktop = Path(__file__).resolve().parents[1] / "outputs/hakimi_trade_electron"
    files = {name: (desktop / name).read_bytes() for name in DESKTOP_FILES}
    files["launch_workbench.py"] = Path(__file__).read_bytes()
    files["Start-Workbench.cmd"] = _cmd(python).encode("utf-8")
    # Reuse the existing complete acceptance validator and its exact-wheel export.
    # It validates all evidence before creating the destination; no weaker second
    # acceptance definition is introduced by the desktop wrapper.
    from release_wheel_bundle import export_bundle
    export_bundle(receipt, output / "accepted-wheel")
    for name, data in files.items():
        with (output / name).open("xb") as stream:
            stream.write(data)
    frozen = {p.relative_to(output).as_posix(): _sha(p.read_bytes())
              for p in sorted(output.rglob("*")) if p.is_file()}
    profile = _sha(json.dumps([os.path.normcase(str(python)), os.path.normcase(str(workspace)),
                              expected["source_sha256"]], separators=(",", ":")).encode())
    manifest = dict(schema_version=SCHEMA, scope="LOCAL_WINDOWS_CANDIDATE_NOT_RELEASE",
                    python=str(python), electron=str(electron), electron_sha256=_sha(electron.read_bytes()),
                    workspace=str(workspace), profile=profile, expected_installation=expected,
                    package_directory=actual["package_directory"], acceptance_sha256=_sha(acceptance.read_bytes()),
                    files_sha256=frozen)
    with (output / "desktop-manifest.json").open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(manifest, stream, indent=2, ensure_ascii=False)
        stream.write("\n")
    return manifest


def verify(directory):
    directory = Path(directory).resolve()
    manifest = json.loads((directory / "desktop-manifest.json").read_text(encoding="utf-8-sig"))
    _require(manifest.get("schema_version") == SCHEMA, "桌面入口清单版本不受支持。")
    for name, digest in manifest["files_sha256"].items():
        path = (directory / name).resolve()
        _require(path.is_relative_to(directory) and path.is_file() and _sha(path.read_bytes()) == digest,
                 f"候选交付文件缺失或已变化：{name}；未启动工作台。")
    electron, python = Path(manifest["electron"]), Path(manifest["python"])
    _require(electron.is_file() and _sha(electron.read_bytes()) == manifest["electron_sha256"],
             "Electron 文件缺失或已变化；请重新核对交付。")
    _require(python.is_file(), "候选 Python 环境不存在。")
    _check_installation(_probe_installation(python), manifest["expected_installation"], python)
    return manifest


def launch(directory):
    directory = Path(directory).resolve()
    manifest = verify(directory)
    env = _clean_env()
    env.update(HAKIMI_RESEARCH_PYTHON=manifest["python"], HAKIMI_RESEARCH_WORKSPACE=manifest["workspace"],
               HAKIMI_RESEARCH_DESKTOP_PROFILE=manifest["profile"])
    return subprocess.run([manifest["electron"], str(directory / "research-main.js")],
                          cwd=directory, env=env, shell=False).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--launch", action="store_true")
    parser.add_argument("--check", action="store_true", help="Check a prepared entry without opening a window")
    parser.add_argument("--acceptance", type=Path)
    parser.add_argument("--python", type=Path)
    parser.add_argument("--electron", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        if args.launch:
            return launch(Path(__file__).resolve().parent)
        if args.check:
            value = verify(args.output or Path(__file__).resolve().parent)
        else:
            _require(all((args.acceptance, args.electron, args.workspace, args.output)),
                     "请同时提供 --acceptance、--electron、--workspace 和全新的 --output。")
            value = prepare(args.acceptance, args.electron, args.workspace, args.output, python=args.python)
        print(json.dumps(dict(status="VERIFIED", version=value["expected_installation"]["version"],
                              build=value["expected_installation"]["build_receipt"]["git"], workspace=value["workspace"]),
                         ensure_ascii=True))
        return 0
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"工作台入口检查失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
