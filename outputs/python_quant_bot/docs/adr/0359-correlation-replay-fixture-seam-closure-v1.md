# ADR0359: Correlation replay fixture seam closure v1

## Status

Accepted as a test-only evidence refinement. It changes no production contract, runtime path, storage path, evidence pointer, UI, paper path, or live path.

## Context

ADR0358 documented exactly three inherited upstream synthetic fixture seams beneath the real ADR0356 and ADR0357 verifiers. A captured-call audit replayed every current fixture invocation through each patched function's original implementation:

1. Correlation-matrix replay: all 18 captured calls returned a PASS document from the original verifier.
2. Calendar-session verification: all 58 captured calls returned false from the original verifier.
3. Provider-identity assertion verification: all 58 captured calls returned false from the original verifier.

The correlation replay patch was therefore redundant. Keeping it would overstate the remaining synthetic boundary and make later seam-removal work harder to audit.

## Decision

Add a test-only integration context that:

1. Locates exactly one patch targeting `strategy_correlation_uncertainty_audit.verify_correlation_matrix_replay`.
2. Replays every call already captured during fixture setup through the original verifier and requires every result to be a PASS document.
3. Stops that patch, removes its cleanup entry, and asserts the active function is no longer a Mock.
4. Requires the two remaining patch targets to be exactly the calendar-session and provider-identity assertion verifiers.
5. Rebuilds the complete ADR0358 tree `3 -> 4 -> 5` source, persistence, lineage, and ADR0357 coverage chain.
6. Reverifies all three ADR0356 documents while the original correlation replay verifier is active.

## Evidence boundary

This closes one redundant fixture seam. It does not make the chain all-source-unmocked. Calendar-session and provider-identity assertion verification remain explicit synthetic seams, and their captured inputs currently fail the original verifiers.

All market, external-authority, storage-durability, complete-history, profitability, paper, live, writer, and current-pointer claims remain false or unproven. No runtime mutation or I/O is performed.

## Compatibility

ADR0356, ADR0357, and ADR0358 files remain unchanged. No production or frontend file is modified. The public natural-forward evidence chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 contract, and neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` presentation remain unchanged.
