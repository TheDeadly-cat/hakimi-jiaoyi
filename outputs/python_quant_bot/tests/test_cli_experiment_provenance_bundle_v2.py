from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from unittest.mock import mock_open, patch
import unittest

from _canonical_source import activate_canonical_source


activate_canonical_source()

from hakimi_research.experiment_provenance_consumer_adapter_v1 import (  # noqa: E402
    build_cli_report_provenance_bundle_candidate,
)
from hakimi_research.reporting import (  # noqa: E402
    RESEARCH_JSON_REPORT_BUNDLE_SCHEMA_VERSION,
    RESEARCH_JSON_REPORT_BUNDLE_TRUST_MODEL,
    _canonical_hash,
    build_json_report_bundle_v2,
    render_json_report,
    save_json_report_bundle_v2,
    verify_json_report_bundle_v2,
)
from tests.test_experiment_provenance_consumer_adapter_v1 import (  # noqa: E402
    _cli_artifact_identity,
    _material,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def _bundle_material() -> tuple[dict, dict, dict]:
    material = _material("UNCLASSIFIED")
    report = {
        **material["result"],
        "experiment_manifest": material["manifest"],
    }
    identity = _cli_artifact_identity(material)
    receipt = build_cli_report_provenance_bundle_candidate(
        report,
        expected_reproducibility=material["reproducibility"],
        expected_context=material["context"],
        expected_manifest_identity=material["manifest_identity"],
        expected_artifact_identity=identity,
    )
    return report, identity, receipt


class CliExperimentProvenanceBundleV2Tests(unittest.TestCase):
    def test_bundle_is_exact_verified_and_non_authorizing(self) -> None:
        report, identity, receipt = _bundle_material()
        bundle = build_json_report_bundle_v2(
            report,
            receipt,
            artifact_identity=identity,
        )

        self.assertEqual(
            bundle["schema_version"],
            RESEARCH_JSON_REPORT_BUNDLE_SCHEMA_VERSION,
        )
        self.assertEqual(
            bundle["trust_model"],
            RESEARCH_JSON_REPORT_BUNDLE_TRUST_MODEL,
        )
        self.assertTrue(bundle["external_artifact_hash_required"])
        self.assertTrue(verify_json_report_bundle_v2(bundle))
        for field in (
            "ranking_allowed",
            "paper_authorized",
            "live_order_allowed",
            "order_entry_allowed",
            "result_is_profitability_proof",
        ):
            self.assertIs(bundle[field], False)

    def test_report_or_receipt_tamper_cannot_cross_bundle(self) -> None:
        report, identity, receipt = _bundle_material()
        bundle = build_json_report_bundle_v2(
            report,
            receipt,
            artifact_identity=identity,
        )
        for field in ("report_payload", "provenance_receipt"):
            with self.subTest(field=field):
                attacked = deepcopy(bundle)
                attacked[field]["tampered"] = True
                self.assertFalse(verify_json_report_bundle_v2(attacked))

    def test_resealed_outer_bundle_cannot_hide_nested_receipt_drift(self) -> None:
        report, identity, receipt = _bundle_material()
        bundle = build_json_report_bundle_v2(
            report,
            receipt,
            artifact_identity=identity,
        )
        attacked = deepcopy(bundle)
        attacked["provenance_receipt"]["provenance_binding"][
            "context_hash"
        ] = "0" * 64
        core = {
            key: value
            for key, value in attacked.items()
            if key != "bundle_hash"
        }
        attacked["bundle_hash"] = _canonical_hash(core)

        self.assertFalse(verify_json_report_bundle_v2(attacked))

    def test_bundle_save_is_single_file_deterministic_and_idempotent(self) -> None:
        report, identity, receipt = _bundle_material()
        bundle = build_json_report_bundle_v2(
            report,
            receipt,
            artifact_identity=identity,
        )
        rendered = render_json_report(bundle)
        writer = mock_open()
        with patch("hakimi_research.reporting.Path.mkdir") as mkdir_mock, patch(
            "hakimi_research.reporting.Path.open",
            writer,
        ):
            path = save_json_report_bundle_v2(bundle, "reports")
        self.assertEqual(Path(path).name, identity["filename"])
        mkdir_mock.assert_called_once_with(parents=True, exist_ok=True)
        writer().write.assert_called_once_with(rendered)

        with patch("hakimi_research.reporting.Path.mkdir"), patch(
            "hakimi_research.reporting.Path.open",
            side_effect=FileExistsError,
        ), patch(
            "hakimi_research.reporting.Path.read_text",
            return_value=rendered,
        ):
            self.assertEqual(
                save_json_report_bundle_v2(bundle, "reports"),
                path,
            )

    def test_current_cli_uses_v2_bundle_before_persistence(self) -> None:
        source = (
            REPOSITORY_ROOT / "src" / "hakimi_research" / "cli.py"
        ).read_text(encoding="utf-8")
        build_position = source.index("build_json_report_bundle_v2(")
        verify_position = source.index("verify_json_report_bundle_v2(")
        save_position = source.index("save_json_report_bundle_v2(")
        self.assertLess(build_position, verify_position)
        self.assertLess(verify_position, save_position)
        self.assertNotIn("output = save_json_report(\n", source)


if __name__ == "__main__":
    unittest.main()
