# ADR0466: Multi-window independent-ticket consumer v3

## Status

Accepted as an unmounted, synthetic, research-only consumer on 2026-08-25.
It does not replace multi-window stratified stability v2, integrate a runtime
gate, switch current, or authorize paper/live activity.

## Context

ADR0465 added an exact dynamic-window source-v2 because matrix-v1 is fixed to a
60-observation lookback while the existing multi-window contract preregisters
20/60/120. The legacy multi-window positive unit path patches the budget-v3
verifier; its unpatched synthetic call remains UNKNOWN with zero verified
windows. A real consumer must call source-v2 verifiers rather than trust mocked
receipts or stored gate conclusions.

## Decision

Add a separate consumer-v3 contract that:

1. Structurally preregisters exactly three strictly increasing windows and the
   expected source-v2 preregistration hash for each window.
2. Requires an externally supplied expected consumer-preregistration hash.
3. Calls the exact source-v2 preregistration, matrix, and independent-ticket
   gate verifiers for every window without monkeypatching a verifier.
4. Returns UNKNOWN and no partial summaries when a source is missing, spliced,
   malformed, promoted, or otherwise not exactly verifiable.
5. Treats an exactly verified window BLOCK as evidence, then blocks the
   aggregate rather than misclassifying it as a source failure.
6. Requires identical cluster partitions and symbol universes across all three
   exact windows.
7. Uses the minimum effective independent-ticket count across windows and never
   promotes raw symbol count to independent count.
8. Emits only bounded hashes, status, counts, and neutral summaries. Raw
   matrices, cells, and source documents are not embedded.
9. Keeps current, runtime, writer, paper, and live authority false.

## Consumer-first order

1. Land source-v2 exact verifiers and tests through ADR0465.
2. Land this unmounted consumer-v3 and verify it with synthetic windows.
3. Independently design a budget/strata adapter that consumes the exact v3
   receipt; do not reinterpret the legacy mock path as evidence.
4. Add dataset/cutoff lineage and independently anchored preregistration
   chronology before any real-source claim.
5. Run a separately authorized shadow dual-read before any current decision.
6. Require an explicit later decision for current, writer, paper, or live. No
   step automatically performs or authorizes the next step.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Three exact 20/60/120 source-v2 windows | research consumer PASS |
| One exact window vote BLOCK | aggregate BLOCK |
| Exact cluster partition drift | partition tier BLOCK |
| Missing or extra window | UNKNOWN with no partial summaries |
| Spliced window from another lookback | UNKNOWN |
| Resealed blocked-window promotion | UNKNOWN |
| Nested unhashable pseudo-status | UNKNOWN |
| Wrong consumer preregistration pin | UNKNOWN |
| Wrong binding count/order, boolean lookback, duplicate source hash | builder rejects |
| Resealed aggregate count or authority promotion | exact verifier rejects |
| Input mutation attempt | caller inputs remain unchanged |

## Boundary

All evidence is pure synthetic and in-memory. This ADR does not use historical
or real-market data, run a profitability backtest, G50/G51, formal blind task,
service, browser, scheduler, publication, paper execution, or live execution.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued.
