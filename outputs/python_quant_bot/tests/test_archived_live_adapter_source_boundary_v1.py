from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from _canonical_source import activate_canonical_source

activate_canonical_source()

from hakimi_research.product_capabilities import build_product_capability_catalog
from quant_bot import execution
from quant_bot.config import BotConfig


class ArchivedLiveAdapterSourceBoundaryV1Tests(unittest.TestCase):
    ARCHIVE_SHA256 = "82a4a1e56201fef94a5ce158043c671d9b29463d843e69674bf8914f6c140e03"

    def test_pre_removal_execution_snapshot_is_preserved_outside_formal_source(self) -> None:
        archived = (
            REPOSITORY_ROOT
            / "archive"
            / "legacy_live_adapter"
            / "execution_with_ccxt_stub.py"
        )
        self.assertTrue(archived.is_file())
        self.assertEqual(hashlib.sha256(archived.read_bytes()).hexdigest(), self.ARCHIVE_SHA256)

    def test_formal_execution_module_exposes_no_ccxt_adapter(self) -> None:
        source_path = PROJECT_ROOT / "quant_bot" / "execution.py"
        source = source_path.read_text(encoding="utf-8")
        self.assertFalse(hasattr(execution, "CcxtBroker"))
        self.assertNotIn("class CcxtBroker", source)
        self.assertNotIn("import ccxt", source)
        self.assertNotIn("create_order", source)
        self.assertFalse(hasattr(execution, "build_broker"))
        self.assertFalse(hasattr(execution, "PaperBroker"))

    def test_formal_dependency_manifests_exclude_ccxt(self) -> None:
        for name in ("requirements.txt", "requirements-core.txt"):
            with self.subTest(name=name):
                lines = (PROJECT_ROOT / name).read_text(encoding="utf-8").splitlines()
                packages = {
                    line.split("=", 1)[0].split(">", 1)[0].strip().lower()
                    for line in lines
                    if line.strip() and not line.lstrip().startswith("#")
                }
                self.assertNotIn("ccxt", packages)

    def test_negative_live_markers_remain_manifest_provenance_only(self) -> None:
        config = BotConfig()
        self.assertEqual(config.execution.broker, "research_simulator")
        self.assertFalse(config.execution.live_trading_enabled)
        self.assertFalse(hasattr(execution, "build_broker"))
        self.assertFalse(hasattr(execution, "CcxtBroker"))

    def test_capability_catalog_keeps_live_execution_archived(self) -> None:
        catalog = build_product_capability_catalog().to_dict()
        self.assertEqual(catalog["capabilities"]["live_execution"], "Archived")
        self.assertFalse(catalog["authority"]["live_allowed"])


if __name__ == "__main__":
    unittest.main()
