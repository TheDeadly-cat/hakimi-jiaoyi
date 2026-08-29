from __future__ import annotations

import copy
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from exchange_terminal.services.static_presentation_application_load_descriptor_preregistration_v1 import (
    build_static_presentation_application_load_descriptor_preregistration_v1,
    verify_static_presentation_application_load_descriptor_preregistration_v1,
)
from exchange_terminal.services.static_presentation_host_patch_preregistration_v1 import (
    APP_BINDING_FRAGMENT_SHA256,
    EXPECTED_APP_JS_POST_SHA256,
    EXPECTED_INDEX_HTML_POST_SHA256,
    LOAD_DESCRIPTOR_HASH,
    ROUNDTRIP_SCHEMA_VERSION,
    SCHEMA_VERSION,
    build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1,
    build_static_presentation_host_patch_preregistration_v1,
    verify_static_presentation_host_patch_in_memory_roundtrip_evidence_v1,
    verify_static_presentation_host_patch_preregistration_v1,
)
from exchange_terminal.services.strict_canonical_json_hash import (
    seal_strict_canonical_document,
    strict_canonical_hash,
)


class NonNativeMapping(dict):
    pass


class StaticPresentationHostPatchPreregistrationV1Tests(unittest.TestCase):
    def setUp(self) -> None:
        self.index_source = (
            PROJECT_ROOT / "exchange_terminal/static/index.html"
        ).read_bytes().decode("utf-8")
        self.app_source = (
            PROJECT_ROOT / "exchange_terminal/static/app.js"
        ).read_bytes().decode("utf-8")
        self.descriptor = (
            build_static_presentation_application_load_descriptor_preregistration_v1()
        )
        self.preregistration = (
            build_static_presentation_host_patch_preregistration_v1()
        )
        self.evidence = (
            build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                self.preregistration,
                self.descriptor,
                self.index_source,
                self.app_source,
            )
        )

    def _reseal(self, document: dict, hash_key: str) -> dict:
        document.pop(hash_key)
        return seal_strict_canonical_document(document, hash_key)

    def test_preregistration_is_exact_blocked_and_not_applied(self) -> None:
        self.assertEqual(self.preregistration["schema_version"], SCHEMA_VERSION)
        self.assertEqual(self.preregistration["status"], "BLOCKED")
        self.assertEqual(
            self.preregistration["preregistration_state"],
            "EXACT_REVERSIBLE_HOST_PATCH_PLAN_REGISTERED_NOT_APPLIED",
        )
        self.assertTrue(
            verify_static_presentation_host_patch_preregistration_v1(
                self.preregistration
            )
        )

    def test_source_contract_pins_exact_load_descriptor(self) -> None:
        self.assertTrue(
            verify_static_presentation_application_load_descriptor_preregistration_v1(
                self.descriptor
            )
        )
        self.assertEqual(
            self.descriptor["load_descriptor_hash"],
            LOAD_DESCRIPTOR_HASH,
        )
        self.assertEqual(
            self.preregistration["source_contract"]["load_descriptor_hash"],
            self.descriptor["load_descriptor_hash"],
        )

    def test_source_contract_file_hashes_match_disk(self) -> None:
        source = self.preregistration["source_contract"]
        expected = {
            source["implementation_path"]: source["implementation_sha256"],
            source["test_path"]: source["test_sha256"],
            source["adr_path"]: source["adr_sha256"],
        }
        observed = {
            path: sha256((PROJECT_ROOT / path).read_bytes()).hexdigest()
            for path in expected
        }
        self.assertEqual(observed, expected)

    def test_target_preimages_match_current_host_bytes(self) -> None:
        targets = {
            row["target_id"]: row
            for row in self.preregistration["patch_plan"]["targets"]
        }
        self.assertEqual(
            sha256(self.index_source.encode("utf-8")).hexdigest(),
            targets["index_html"]["pre_sha256"],
        )
        self.assertEqual(
            sha256(self.app_source.encode("utf-8")).hexdigest(),
            targets["app_javascript"]["pre_sha256"],
        )
        self.assertEqual(
            targets["index_html"]["expected_post_sha256"],
            EXPECTED_INDEX_HTML_POST_SHA256,
        )
        self.assertEqual(
            targets["app_javascript"]["expected_post_sha256"],
            EXPECTED_APP_JS_POST_SHA256,
        )

    def test_patch_plan_has_four_ordered_unperformed_operations(self) -> None:
        rows = self.preregistration["patch_plan"]["operations"]
        self.assertEqual([row["sequence"] for row in rows], [1, 2, 3, 4])
        self.assertTrue(all(row["performed"] is False for row in rows))
        self.assertEqual(
            [row["operation_type"] for row in rows],
            [
                "INSERT_AFTER_UNIQUE_ANCHOR",
                "INSERT_AFTER_UNIQUE_ANCHOR",
                "INSERT_BEFORE_UNIQUE_ANCHOR",
                "APPEND_EXACT_SUFFIX",
            ],
        )

    def test_operation_anchors_are_unique_and_fragments_absent(self) -> None:
        sources = {
            "exchange_terminal/static/index.html": self.index_source,
            "exchange_terminal/static/app.js": self.app_source,
        }
        for row in self.preregistration["patch_plan"]["operations"]:
            source = sources[row["target_path"]]
            self.assertNotIn(row["fragment"], source)
            if row["operation_type"] != "APPEND_EXACT_SUFFIX":
                self.assertEqual(
                    source.count(row["anchor"]),
                    row["required_anchor_count"],
                )

    def test_fragment_hashes_and_lengths_are_exact(self) -> None:
        rows = self.preregistration["patch_plan"]["operations"]
        for row in rows:
            self.assertEqual(
                sha256(row["fragment"].encode("utf-8")).hexdigest(),
                row["fragment_sha256"],
            )
            self.assertEqual(len(row["fragment"]), row["fragment_length"])
        self.assertEqual(rows[-1]["fragment_sha256"], APP_BINDING_FRAGMENT_SHA256)

    def test_app_fragment_is_unmounted_nonexecuting_and_neutral(self) -> None:
        fragment = self.preregistration["patch_plan"]["operations"][-1]["fragment"]
        self.assertIn(
            "buildPortfolioCorrelationAdmissionRailHostRenderCandidateV1",
            fragment,
        )
        self.assertIn("EXACT_UNMOUNTED_MARKUP_CANDIDATE", fragment)
        self.assertNotIn("document.", fragment)
        self.assertNotIn("innerHTML", fragment)
        self.assertNotIn("fetch(", fragment)
        self.assertNotRegex(fragment, r"\bREADY\b")

    def test_patch_and_rollback_plan_hashes_are_exact(self) -> None:
        self.assertEqual(
            self.preregistration["patch_plan_hash"],
            strict_canonical_hash(self.preregistration["patch_plan"]),
        )
        self.assertEqual(
            self.preregistration["rollback_plan_hash"],
            strict_canonical_hash(self.preregistration["rollback_plan"]),
        )
        operation_ids = [
            row["operation_id"]
            for row in self.preregistration["patch_plan"]["operations"]
        ]
        self.assertEqual(
            self.preregistration["rollback_plan"]["reverse_operation_ids"],
            list(reversed(operation_ids)),
        )

    def test_execution_plan_and_authority_remain_fully_unbound(self) -> None:
        self.assertTrue(
            all(
                value is None
                for value in self.preregistration["execution_plan"].values()
            )
        )
        self.assertTrue(
            all(
                value is False
                for value in self.preregistration["authority"].values()
            )
        )

    def test_registration_records_no_host_or_runtime_mutation(self) -> None:
        facts = self.preregistration["facts"]
        self.assertFalse(facts["patch_operations_performed"])
        self.assertFalse(facts["rollback_performed"])
        self.assertFalse(facts["host_files_written"])
        self.assertFalse(facts["app_fragment_executed"])
        self.assertFalse(facts["browser_executed"])
        self.assertFalse(facts["dom_mounted"])
        self.assertFalse(facts["runtime_mutations_performed"])

    def test_exact_sources_build_blocked_hash_only_roundtrip_evidence(self) -> None:
        self.assertEqual(self.evidence["schema_version"], ROUNDTRIP_SCHEMA_VERSION)
        self.assertEqual(self.evidence["status"], "BLOCKED")
        self.assertEqual(
            self.evidence["roundtrip_state"],
            "EXACT_IN_MEMORY_APPLY_AND_ROLLBACK_HASH_ROUNDTRIP",
        )
        self.assertEqual(self.evidence["operation_count"], 4)
        self.assertTrue(
            verify_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                self.evidence,
                self.preregistration,
                self.descriptor,
                self.index_source,
                self.app_source,
            )
        )

    def test_roundtrip_evidence_proves_expected_post_and_recovered_hashes(self) -> None:
        hashes = self.evidence["target_hashes"]
        self.assertEqual(
            hashes["exchange_terminal/static/index.html"]["post_sha256"],
            EXPECTED_INDEX_HTML_POST_SHA256,
        )
        self.assertEqual(
            hashes["exchange_terminal/static/app.js"]["post_sha256"],
            EXPECTED_APP_JS_POST_SHA256,
        )
        for row in hashes.values():
            self.assertEqual(row["pre_sha256"], row["recovered_sha256"])

    def test_roundtrip_evidence_embeds_no_raw_host_or_patch_source(self) -> None:
        serialized = json.dumps(self.evidence, sort_keys=True)
        self.assertNotIn("<!doctype html>", serialized)
        self.assertNotIn("const state =", serialized)
        self.assertNotIn("attachPortfolioCorrelationAdmissionRailHostV1", serialized)
        self.assertFalse(self.evidence["facts"]["raw_host_sources_embedded"])
        self.assertFalse(self.evidence["facts"]["raw_patched_sources_embedded"])

    def test_host_preimage_drift_returns_unknown(self) -> None:
        evidence = (
            build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                self.preregistration,
                self.descriptor,
                self.index_source + "\n<!-- forged -->",
                self.app_source,
            )
        )
        self.assertEqual(evidence["status"], "UNKNOWN")
        self.assertEqual(
            evidence["reason_code"],
            "HOST_PRECONDITION_HASH_MISMATCH",
        )

    def test_tampered_preregistration_returns_unknown(self) -> None:
        tampered = copy.deepcopy(self.preregistration)
        tampered["facts"]["host_files_written"] = True
        evidence = (
            build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                tampered,
                self.descriptor,
                self.index_source,
                self.app_source,
            )
        )
        self.assertEqual(evidence["status"], "UNKNOWN")
        self.assertEqual(
            evidence["reason_code"],
            "PATCH_PREREGISTRATION_NOT_EXACT",
        )

    def test_tampered_descriptor_returns_unknown(self) -> None:
        tampered = copy.deepcopy(self.descriptor)
        tampered["facts"]["app_binding_present"] = True
        evidence = (
            build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                self.preregistration,
                tampered,
                self.index_source,
                self.app_source,
            )
        )
        self.assertEqual(evidence["status"], "UNKNOWN")
        self.assertEqual(evidence["reason_code"], "LOAD_DESCRIPTOR_NOT_EXACT")

    def test_non_native_and_cyclic_documents_fail_closed(self) -> None:
        evidence = (
            build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                NonNativeMapping(self.preregistration),
                self.descriptor,
                self.index_source,
                self.app_source,
            )
        )
        self.assertEqual(evidence["status"], "UNKNOWN")
        self.assertEqual(
            evidence["reason_code"],
            "PATCH_PREREGISTRATION_SNAPSHOT_FAILED",
        )
        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        evidence = (
            build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                self.preregistration,
                cyclic,
                self.index_source,
                self.app_source,
            )
        )
        self.assertEqual(evidence["status"], "UNKNOWN")

    def test_resealed_fragment_swap_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.preregistration)
        operation = tampered["patch_plan"]["operations"][0]
        operation["fragment"] += "<!-- forged -->"
        operation["fragment_sha256"] = sha256(
            operation["fragment"].encode("utf-8")
        ).hexdigest()
        operation["fragment_length"] = len(operation["fragment"])
        tampered["patch_plan_hash"] = strict_canonical_hash(tampered["patch_plan"])
        tampered = self._reseal(tampered, "patch_preregistration_hash")
        self.assertFalse(
            verify_static_presentation_host_patch_preregistration_v1(tampered)
        )

    def test_resealed_authority_promotion_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.preregistration)
        tampered["authority"]["host_asset_write_allowed"] = True
        tampered = self._reseal(tampered, "patch_preregistration_hash")
        self.assertFalse(
            verify_static_presentation_host_patch_preregistration_v1(tampered)
        )

    def test_resealed_roundtrip_promotion_fails_exact_verifier(self) -> None:
        tampered = copy.deepcopy(self.evidence)
        tampered["facts"]["host_files_written"] = True
        tampered = self._reseal(tampered, "roundtrip_evidence_hash")
        self.assertFalse(
            verify_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                tampered,
                self.preregistration,
                self.descriptor,
                self.index_source,
                self.app_source,
            )
        )

    def test_documents_have_no_promotional_copy(self) -> None:
        values: list[str] = []

        def collect(value: object) -> None:
            if type(value) is dict:
                for nested in value.values():
                    collect(nested)
            elif type(value) is list:
                for nested in value:
                    collect(nested)
            elif type(value) is str:
                values.append(value)

        semantic_preregistration = copy.deepcopy(self.preregistration)
        fragments: list[str] = []
        for operation in semantic_preregistration["patch_plan"]["operations"]:
            fragments.append(operation.pop("fragment"))
            operation.pop("anchor")
        collect(semantic_preregistration)
        collect(self.evidence)
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\breturn\b|\balpha\b|win rate",
                " ".join(values),
                re.IGNORECASE,
            )
        )
        self.assertIsNone(
            re.search(
                r"\bREADY\b|\bprofit\b|\balpha\b|win rate",
                " ".join(fragments),
                re.IGNORECASE,
            )
        )
        self.assertFalse(self.evidence["facts"]["profitability_proven"])

    def test_preregistration_and_evidence_are_deterministic(self) -> None:
        self.assertEqual(
            self.preregistration,
            build_static_presentation_host_patch_preregistration_v1(),
        )
        self.assertEqual(
            self.evidence,
            build_static_presentation_host_patch_in_memory_roundtrip_evidence_v1(
                self.preregistration,
                self.descriptor,
                self.index_source,
                self.app_source,
            ),
        )


if __name__ == "__main__":
    unittest.main()
