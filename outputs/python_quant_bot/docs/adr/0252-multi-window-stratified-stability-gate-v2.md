# ADR 0252: Multi-window stratified stability gate-v2

## Status

Accepted as an unmounted, research-only strategy gate on 2026-08-23.

## Observed gap

ADR0212 multi-window-v1 exactly verifies one weighted budget-v2 document for
each of three preregistered windows. Its preregistration pin, verifier, document
shape, and window summaries are all budget-v2 specific. ADR0249 later introduced
budget-v3 preregistered-strata concentration, while ADR0250 accepts only one
budget-v3 document beside the older portfolio-risk chain.

A pure synthetic read-only call chain produced a short-window budget-v3 PASS and
a long-window budget-v3 BLOCK. Passing the three-window v3 set to v1 yielded
`UNKNOWN / BLOCK_MULTI_WINDOW_SOURCE_UNVERIFIED` with zero verified windows,
rather than a conservative stratified BLOCK. Seven gap predicates passed:

1. The short budget-v3 document passed.
2. The long budget-v3 document blocked.
3. Multi-window-v1 rejected the v3 set as unknown.
4. Multi-window-v1 reported source-unverified.
5. Multi-window-v1 projected zero verified windows.
6. Presentation-v7 accepts only one budget-v3 document.
7. Presentation-v7 has no window budget-v3 document-set input.

This is a versioned strategy gap, not evidence that v1 is incorrect within its
budget-v2 contract.

## Decision

Add a separate multi-window stratified stability gate-v2 without changing v1,
adapter-v5/v6, presentation-v7, or any mounted consumer.

Before risk-increasing evaluation, v2 preregisters exactly three unique windows
with strictly increasing lookbacks. The registration freezes four policies:

1. Any exactly verified window budget-v3 BLOCK blocks risk increase.
2. Complete-link partitions must remain identical across windows.
3. Preregistered strata topology must remain identical across windows.
4. Risk reduction remains source free, matching budget-v3 semantics.

For every risk-increasing window the gate:

1. Calls the public budget-v3 exact verifier with the complete context.
2. Requires the budget-v3 seal, schema, authority locks, and context hashes.
3. Requires the exact registered lookback and a unique matrix hash.
4. Requires the same proposal, positions, equity, cap, symbol universe, return
   series, threshold, direction, and risk direction across windows.
5. Normalizes the complete-link partition and strata topology into separate
   canonical hashes.
6. Projects only bounded window summaries and conservative cross-window extrema.

Decision precedence for risk increase is source verification, any window v3
BLOCK, partition drift, strata topology drift, then local research PASS. An
unknown source never exposes partial window summaries.

## Consumer-first activation order

1. Keep gate-v2 as a standalone pure service and validate synthetic contracts.
2. Design a separate adapter that cross-binds an anchor v3 document and the v2
   gate before changing any presentation.
3. Add a neutral presentation candidate only after the adapter exact contract is
   independently reviewed.
4. Require separate route and mount ADRs if those steps are ever proposed.
5. Never infer current, paper, live, order, or profitability authority.

This ADR authorizes only step 1.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Missing or extra window | UNKNOWN, no summaries |
| Duplicate matrix hash | UNKNOWN, no summaries |
| Budget-v3 verifier failure | UNKNOWN, no summaries |
| Spliced strata registration hash | UNKNOWN, no summaries |
| Any exact window budget-v3 BLOCK | BLOCK |
| All budgets PASS but partition drifts | BLOCK |
| All budgets PASS but strata topology drifts | BLOCK |
| Proposal or trade identity drifts | UNKNOWN |
| Re-sealed permission promotion | Exact verifier BLOCK |
| Risk reduction with no sources | PASS, verifier not called |

## Authority and evidence boundary

The output contains window IDs, lookbacks, matrix hashes, budget-v3 hashes,
partition hashes, topology hashes, local decisions, bounded counts, and extrema.
It does not embed matrices, audits, positions, source documents, verification
contexts, or runtime assets. Writer, current, runtime, paper, and live authority
remain false.

Synthetic contracts do not prove market stability, profitability, future
performance, provider trust, or trading authority. No natural-forward artifact,
legacy pack-v5 behavior, pointer-v2 contract, current admission, HTTP route,
static mount, scheduler, or trading task changes in this slice.
