"""Build a source-byte receipt inside each ordinary wheel (no checkout required)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithSourceIdentity(build_py):
    def find_package_modules(self, package, package_dir):
        modules = super().find_package_modules(package, package_dir)
        root = Path(__file__).resolve().parent
        manifest = json.loads((root / "src/hakimi_research/runtime-files.json").read_text(encoding="utf-8"))
        selected = set(manifest["files"])
        package_root = (root / "src/hakimi_research").resolve()
        return [item for item in modules if Path(item[2]).resolve().relative_to(package_root).as_posix() in selected]

    def run(self):
        super().run()
        root = Path(__file__).resolve().parent
        package = Path(self.build_lib) / "hakimi_research"
        spec = importlib.util.spec_from_file_location("_hakimi_build_identity", root / "src/hakimi_research/source_identity.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        identity = module.package_content_identity(package)
        git = {"commit": "", "status": "UNKNOWN"}
        try:
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=3)
            status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=root, capture_output=True, text=True, timeout=3)
            if commit.returncode == 0:
                git["commit"] = commit.stdout.strip()
            if commit.returncode == 0 and status.returncode == 0:
                git["status"] = "DIRTY" if status.stdout.strip() else "CLEAN"
        except (OSError, subprocess.SubprocessError):
            pass
        origin_path = root / ".source-build-origin.json"
        if origin_path.is_file():
            origin = json.loads(origin_path.read_text(encoding="utf-8"))
            if (
                type(origin) is not dict or origin.get("schema_version") != "research-source-build-origin-v1"
                or origin.get("content_sha256") != identity["content_sha256"]
                or origin.get("file_hashes") != identity["file_hashes"]
                or type(origin.get("git")) is not dict
                or origin["git"].get("status") not in {"CLEAN", "DIRTY", "UNKNOWN"}
            ):
                raise RuntimeError("Build source origin does not match the actual packaged bytes")
            git = origin["git"]
        receipt = {
            "schema_version": "research-build-source-v1",
            **identity,
            "git": git,
            "build_definition_sha256": {
                name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in ("pyproject.toml", "setup.py")
            },
        }
        (package / module.BUILD_IDENTITY_FILENAME).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")


setup(cmdclass={"build_py": BuildWithSourceIdentity})
