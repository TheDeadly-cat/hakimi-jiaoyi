"""Compatibility shim for the witness-ownership state-store application port."""

from exchange_terminal.application.ports.witness_ownership_state_store_v1 import (
    COMMAND_SCHEMA_VERSION,
    RECEIPT_CLAIM_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    STATIC_FINGERPRINT,
    WITNESS_OWNERSHIP_NAMESPACE,
    WitnessOwnershipCompareConsumeAndAdvanceCommandV1,
    WitnessOwnershipCompareConsumeAndAdvanceResultV1,
    WitnessOwnershipProviderOutcomeV1,
    WitnessOwnershipStateProviderPortV1,
    build_witness_ownership_compare_consume_and_advance_command_v1,
    build_witness_ownership_compare_consume_and_advance_result_v1,
    build_witness_ownership_consumption_key_v1,
    build_witness_ownership_state_provider_receipt_claim_v1,
    verify_witness_ownership_compare_consume_and_advance_result_v1,
)


__all__ = [
    "COMMAND_SCHEMA_VERSION",
    "RECEIPT_CLAIM_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "STATIC_FINGERPRINT",
    "WITNESS_OWNERSHIP_NAMESPACE",
    "WitnessOwnershipCompareConsumeAndAdvanceCommandV1",
    "WitnessOwnershipCompareConsumeAndAdvanceResultV1",
    "WitnessOwnershipProviderOutcomeV1",
    "WitnessOwnershipStateProviderPortV1",
    "build_witness_ownership_compare_consume_and_advance_command_v1",
    "build_witness_ownership_compare_consume_and_advance_result_v1",
    "build_witness_ownership_consumption_key_v1",
    "build_witness_ownership_state_provider_receipt_claim_v1",
    "verify_witness_ownership_compare_consume_and_advance_result_v1",
]
