from __future__ import annotations

from pathlib import Path
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from _canonical_source import activate_canonical_source


REPO_ROOT = Path(__file__).resolve().parents[3]
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
LOCK_PATH = REPO_ROOT / "requirements.research.lock"
ACTIVE_CONFIG_PATH = REPO_ROOT / "src" / "hakimi_research" / "resources" / "config.example.json"
CAPABILITY_DEFINITION_PATH = (
    REPO_ROOT
    / "src"
    / "hakimi_research"
    / "contracts"
    / "product-capabilities.json"
)

activate_canonical_source()

from hakimi_research import cli  # noqa: E402
from hakimi_research.source_layout import default_artifact_root  # noqa: E402


class PackageMetadataV1Tests(unittest.TestCase):
    @classmethod
    def metadata(cls) -> dict:
        return tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))

    def test_src_package_has_formal_cli_entrypoint_and_packaged_contract(self) -> None:
        metadata = self.metadata()
        self.assertEqual(metadata["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertEqual(metadata["project"]["name"], "hakimi-research")
        self.assertEqual(
            metadata["project"]["scripts"]["hakimi-research"],
            "hakimi_research.cli:main",
        )
        self.assertEqual(metadata["tool"]["setuptools"]["package-dir"], {"": "src"})
        self.assertEqual(
            metadata["tool"]["setuptools"]["package-data"]["hakimi_research"],
            ["contracts/*.json", "resources/*.json", "resources/*.lock", "_build_identity.json"],
        )
        self.assertTrue(CAPABILITY_DEFINITION_PATH.is_file())

    def test_project_dependencies_match_locked_research_closure(self) -> None:
        metadata = self.metadata()
        locked = [
            line.strip()
            for line in LOCK_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        self.assertEqual(metadata["project"]["dependencies"], locked)
        self.assertEqual(
            LOCK_PATH.read_bytes(),
            (ACTIVE_CONFIG_PATH.parent / "requirements.research.lock").read_bytes(),
        )

    def test_active_config_and_artifacts_are_outside_outputs(self) -> None:
        self.assertEqual(cli.DEFAULT_CONFIG_PATH, ACTIVE_CONFIG_PATH)
        self.assertNotIn("outputs", cli.DEFAULT_CONFIG_PATH.relative_to(REPO_ROOT).parts)
        self.assertTrue(ACTIVE_CONFIG_PATH.is_file())
        self.assertTrue((ACTIVE_CONFIG_PATH.parent / "experiment.example.json").is_file())
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", {"HAKIMI_RESEARCH_HOME": str(Path(directory) / "research")}):
            self.assertEqual(default_artifact_root(), (Path(directory) / "research").resolve())
            self.assertFalse(default_artifact_root().exists())
        launcher = (REPO_ROOT / "hakimi-research.ps1").read_text(encoding="utf-8")
        self.assertNotIn("PYTHONPATH", launcher)
        self.assertNotIn("outputs\\python_quant_bot", launcher)

    def test_package_contract_does_not_depend_on_legacy_project_root(self) -> None:
        source = (
            REPO_ROOT / "src" / "hakimi_research" / "product_capabilities.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("LEGACY_PROJECT_ROOT", source)
        self.assertNotIn("outputs/python_quant_bot", source)


if __name__ == "__main__":
    unittest.main()
