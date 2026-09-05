"""Build and install an ordinary wheel, then run MVP tests outside the checkout.

Use --wheelhouse for a strictly local install. CI may install the same pinned
dependencies from its package index. This harness never sets PYTHONPATH or uses
an editable install, and venv does not inherit system-site-packages.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import venv


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheelhouse", type=Path)
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if (root / "requirements.research.lock").read_bytes() != (root / "src/hakimi_research/resources/requirements.research.lock").read_bytes():
        raise RuntimeError("Packaged dependency lock differs from the canonical lock")
    work = args.work_dir.resolve() if args.work_dir else Path(tempfile.mkdtemp(prefix="hakimi-wheel-acceptance-"))
    if work.is_relative_to(root):
        raise RuntimeError("Wheel acceptance work directory must be outside the source checkout")
    if work.exists() and any(work.iterdir()):
        raise RuntimeError("Wheel acceptance work directory must be empty")
    work.mkdir(parents=True, exist_ok=True)
    outside = work / "outside-checkout"
    outside.mkdir()
    clean_env = dict(os.environ)
    clean_env.pop("PYTHONPATH", None)
    clean_env.pop("PYTHONHOME", None)
    clean_env["PYTHONNOUSERSITE"] = "1"
    clean_env["PYTHONUTF8"] = "1"
    clean_env["PYTHONIOENCODING"] = "utf-8"
    clean_env["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    clean_env["HAKIMI_RESEARCH_HOME"] = str(work / "research-artifacts")

    def run(command: list[str], *, cwd: Path = outside, echo: bool = True) -> str:
        completed = subprocess.run(command, cwd=cwd, env=clean_env, text=True, encoding="utf-8", errors="replace", capture_output=True, timeout=900)
        if echo:
            print(completed.stdout, end="", flush=True)
        print(completed.stderr, end="", file=sys.stderr, flush=True)
        if completed.returncode:
            raise RuntimeError(f"Wheel acceptance command failed ({completed.returncode}): {command[0:3]}")
        return completed.stdout

    dist = work / "dist"
    # Build from a fresh, minimal source staging directory: stale build products
    # cannot slip into the wheel, and neither archives nor examples are required.
    staging = work / "source-build"
    staging.mkdir()
    for name in ("pyproject.toml", "setup.py", "README.md", "requirements.research.lock"):
        shutil.copy2(root / name, staging / name)
    build_inputs = {
        name: hashlib.sha256((staging / name).read_bytes()).hexdigest()
        for name in ("pyproject.toml", "setup.py", "requirements.research.lock")
    }
    shutil.copytree(root / "src", staging / "src", ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.egg-info"))
    identity_spec = importlib.util.spec_from_file_location("_acceptance_source_identity", root / "src/hakimi_research/source_identity.py")
    identity_module = importlib.util.module_from_spec(identity_spec)
    identity_spec.loader.exec_module(identity_module)
    original_identity = identity_module.package_content_identity(root / "src/hakimi_research")
    staged_identity = identity_module.package_content_identity(staging / "src/hakimi_research")
    if original_identity != staged_identity:
        raise RuntimeError("Source changed while staging the wheel; rebuild from a stable snapshot")
    git_origin = {"commit": "", "status": "UNKNOWN"}
    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=3)
        state = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, capture_output=True, text=True, timeout=3)
        if commit.returncode == 0:
            git_origin["commit"] = commit.stdout.strip()
        if commit.returncode == 0 and state.returncode == 0:
            git_origin["status"] = "DIRTY" if state.stdout.strip() else "CLEAN"
    except (OSError, subprocess.SubprocessError, UnicodeError):
        pass
    (staging / ".source-build-origin.json").write_text(json.dumps({
        "schema_version": "research-source-build-origin-v1", **staged_identity, "git": git_origin,
    }, sort_keys=True) + "\n", encoding="utf-8")
    run([sys.executable, "-m", "pip", "wheel", str(staging), "--no-index", "--no-deps", "--no-build-isolation", "--wheel-dir", str(dist)])
    wheels = list(dist.glob("hakimi_research-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError("Expected exactly one built research wheel")
    wheel = wheels[0]
    environment = work / "venv"
    venv.EnvBuilder(with_pip=True, system_site_packages=False).create(environment)
    python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    installation = [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
    if args.wheelhouse:
        installation.extend(["--no-index", "--find-links", str(args.wheelhouse.resolve())])
    run([*installation, "-r", str(root / "requirements.research.lock")])
    run([*installation, "--no-deps", str(wheel)])
    run([str(python), "-m", "pip", "check"])
    receipt_code = (
        "import json,pathlib,sys; from hakimi_research.environment import build_runtime_provenance; "
        "from hakimi_research.source_layout import REPOSITORY_ROOT,DEFAULT_CONFIG_PATH,DEFAULT_EXPERIMENT_SPEC_PATH; "
        "p=build_runtime_provenance(); assert REPOSITORY_ROOT is None; "
        "assert DEFAULT_CONFIG_PATH.is_file() and DEFAULT_EXPERIMENT_SPEC_PATH.is_file(); "
        "assert p['source_identity']['status']=='BUILD_VERIFIED',p; "
        "assert p['environment_verified']['status']=='VERIFIED',p; "
        "assert str(pathlib.Path(sys.prefix).resolve()) in str(DEFAULT_CONFIG_PATH.resolve()); "
        "print(json.dumps(p,ensure_ascii=True))"
    )
    provenance = json.loads(run([str(python), "-c", receipt_code], echo=False))
    if provenance["source_identity"]["content_sha256"] != staged_identity["content_sha256"]:
        raise RuntimeError("Installed source identity differs from the staged source snapshot")
    if provenance["source_identity"]["build_receipt"]["git"] != git_origin:
        raise RuntimeError("Installed build receipt lost its source checkout observation")
    print("Installed runtime: " + json.dumps({
        "environment": provenance["environment_verified"]["status"],
        "source": provenance["source_identity"]["status"],
        "source_sha256": provenance["source_identity"]["content_sha256"],
    }), flush=True)
    command = environment / ("Scripts/hakimi-research.exe" if os.name == "nt" else "bin/hakimi-research")
    run([str(command), "--help"])
    run([str(command), "capabilities"])
    run([str(command), "list-strategies"])
    tests = outside / "tests"
    shutil.copytree(root / "tests", tests, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # The independent Decimal reconciler is a test/audit sidecar, not a runtime
    # import of the research package. Copy its explicit fixture dependency too.
    # No checkout source or PYTHONPATH is made available to installed commands.
    test_support = {}
    for relative in ("scripts/reconcile_research_ledger.py",):
        destination = outside / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / relative, destination)
        test_support[relative] = hashlib.sha256(destination.read_bytes()).hexdigest()
    if not list(tests.glob("test_*.py")):
        raise RuntimeError("No MVP tests found for installed-package acceptance")
    run([str(python), "-m", "unittest", "discover", "-s", str(tests), "-p", "test_*.py", "-v"])
    if identity_module.package_content_identity(root / "src/hakimi_research") != original_identity:
        raise RuntimeError("Source changed during wheel acceptance; rerun on the final source snapshot")
    if any(hashlib.sha256((root / name).read_bytes()).hexdigest() != expected for name, expected in build_inputs.items()):
        raise RuntimeError("Build inputs changed during wheel acceptance; rerun on the final snapshot")
    if any(hashlib.sha256((root / name).read_bytes()).hexdigest() != expected for name, expected in test_support.items()):
        raise RuntimeError("Independent audit support changed during wheel acceptance")
    receipt = {
        "schema_version": "research-wheel-acceptance-v1", "status": "PASS",
        "wheel": str(wheel), "wheel_sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
        "python": str(python), "outside_directory": str(outside),
        "editable": False, "pythonpath_used": False, "system_site_packages": False,
        "installed_runtime": provenance,
        "source_checkout_unchanged": True,
        "build_inputs_sha256": build_inputs,
        "independent_test_support_sha256": test_support,
        "tests": sorted(path.name for path in tests.glob("test_*.py")),
        "console_smoke_commands": ["--help", "capabilities", "list-strategies"],
    }
    receipt_path = work / "wheel-acceptance.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(f"Wheel acceptance receipt: {receipt_path}")


if __name__ == "__main__":
    main()
