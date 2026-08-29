# ADR 0046: Downside-tail read-only report consumer

## Status

Candidate consumer implemented. It is hash-bound, read-only, non-formal, and not connected to current state.

## Decision

Consume a downside-tail evaluation only when all of the following agree:

- the candidate registration rebuilds to the fixed v1 contract;
- the externally expected registration hash matches;
- the externally expected evaluation hash matches the sealed evaluation;
- source, counts, cross-stratum pair ordering, overlap ratios, exact hypergeometric p-values, Bonferroni values, flags, decision, blockers, and authority fields are semantically coherent.

A self-sealed mutation is not sufficient. Changing a p-value, pair scope, decision, count, or permission field and recomputing the hash still fails semantic verification.

The consumer distinguishes contract validity from the gate result. A valid observed BLOCK has verification status PASS and gate decision BLOCK. A valid sealed UNKNOWN remains UNKNOWN and blocked. Invalid or mismatched input produces a generic UNKNOWN receipt and does not reflect untrusted text.

## Projection boundary

The receipt exposes only source state, gate decision, aggregate counts, expected hashes, and verification booleans. It does not expose observation ids, returns, pair identities, strata, overlap details, or p-values. All independence, formal binding, current, paper, live, writer, and profitability permissions remain false.

## Next order

1. Candidate gate.
2. This read-only consumer.
3. Separate protocol registration binding and migration blockers.
4. Redacted public projection and optional unmounted neutral UI.
5. Formal persistence only after independent review; never an automatic current switch.
