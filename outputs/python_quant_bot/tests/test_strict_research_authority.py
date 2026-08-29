import unittest

from exchange_terminal.services.strict_research_authority import (
    strict_research_authority_invalid,
    strict_research_authority_violations,
)


class StrictResearchAuthorityTests(unittest.TestCase):
    def test_native_false_authority_surface_is_valid(self):
        payload = {
            "current_admission_allowed": False,
            "current_writer_activation_allowed": False,
            "formal_registry_activation_allowed": False,
            "writer_implemented": False,
            "permissions": {
                "paper_authorized": False,
                "live_order_allowed": False,
            },
        }
        self.assertFalse(strict_research_authority_invalid(payload))
        self.assertEqual(strict_research_authority_violations(payload), [])

    def test_top_level_true_is_rejected(self):
        violations = strict_research_authority_violations(
            {"current_admission_allowed": True}
        )
        self.assertIn("$.current_admission_allowed", violations)

    def test_nested_writer_activation_is_rejected(self):
        violations = strict_research_authority_violations(
            {
                "evidence": {
                    "formal_registry_activation_allowed": True,
                }
            }
        )
        self.assertIn(
            "$.evidence.formal_registry_activation_allowed",
            violations,
        )

    def test_truthy_string_is_not_native_false(self):
        self.assertTrue(
            strict_research_authority_invalid(
                {"permissions": {"paper_authorized": "false"}}
            )
        )

    def test_authority_inside_list_is_rejected(self):
        violations = strict_research_authority_violations(
            [{"live_order_allowed": 0}]
        )
        self.assertIn("$[0].live_order_allowed", violations)
