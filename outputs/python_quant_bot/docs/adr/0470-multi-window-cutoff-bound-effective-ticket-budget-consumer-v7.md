# ADR0470: Multi-window cutoff-bound effective-ticket budget consumer v7

Date: 2026-08-25

## Status

Accepted as a versioned research-only consumer candidate. It does not replace
effective-bet budget v11, portfolio admission, runtime gates, or `current`.

## Context

ADR0465-ADR0469 provide dynamic 20/60/120 correlation clusters, an exact
multi-window consumer, return-panel lineage, canonical market-data envelopes,
and an independently preregistered common cutoff. The latest legacy
effective-bet budget v11 instead extends a separate witness/checkpoint/replay
chain. Its local result may be `PASS`, but its `admission_status` is always
`BLOCKED` and its evaluator has no cutoff or envelope input. The existing
portfolio admission/effective-budget binding still consumes budget v3.

A pure synthetic gap proof evaluated a coherently shifted market-data chain.
ADR0469 correctly returned `UNKNOWN`, while budget v11 remained byte-for-byte
unchanged with local `PASS` and admission `BLOCKED`. Therefore the dynamic
natural-forward source chain did not constrain proposal-level ticket budgeting.

## Decision

Add a separate v7 consumer that:

- exact-verifies a `PASS` ADR0469 common-cutoff document and its complete v5
  context before reading any cluster evidence;
- preregisters strategy identity, universe, required short/anchor/long windows,
  effective-ticket limit, cluster gross-bps limit, and the v6 preregistration
  hash;
- recomputes all three window cluster covers from the exact v2 gate documents;
- adds an edge whenever two symbols share a cluster in any required window and
  takes connected components of the edge union;
- counts each occupied conservative component as one effective ticket;
- adds proposal gross exposure to its component even when the proposal consumes
  zero marginal effective tickets;
- uses integer caller-defined minor units and ceiling basis-point arithmetic;
- returns `UNKNOWN` for invalid source or inputs, `BLOCK` for a budget breach,
  and `PASS` only for a local research-budget condition;
- keeps `admission_status` fixed at `BLOCKED` and all authority fields false.

The merge rule is intentionally conservative:

`ANY_WINDOW_COCLUSTER_EDGE_CONNECTED_COMPONENTS`

If A and B share a cluster in one window, while B and C share a cluster in a
different window, A/B/C form one effective component. A single-window split
cannot restore an independence claim.

## Consumer-first activation order

1. Create the v7 budget preregistration without evaluating a proposal.
2. Produce and exact-verify ADR0469 and its full envelope/lineage context.
3. Evaluate v7 only in synthetic or isolated read-only consumers.
4. Compare local PASS/BLOCK/UNKNOWN results against independently reviewed
   proposal fixtures while admission remains blocked.
5. Design a separate merger with v11 and portfolio admission before any runtime
   integration. This ADR grants no such integration or authority.

## Adversarial matrix

- A/B correlated proposal consumes zero marginal tickets but accumulates gross;
- A/B combined gross exceeds the preregistered component cap;
- C then B consumes a second effective ticket and can exceed ticket budget;
- v6 UNKNOWN after a coherent ten-year timestamp shift;
- transitive any-window union across A/B and B/C;
- boolean aliases for money and policy limits;
- malformed, duplicate, or out-of-universe position/proposal rows;
- window-gate drift beneath an old exact cutoff document;
- resealed preregistration, budget summary, and authority promotion;
- deterministic output, input immutability, and raw-input redaction.

## Consequences

Highly correlated symbols no longer appear as independent tickets in this new
proposal-level research consumer, and correlation concentration remains visible
even when the marginal ticket count is zero. The consumer is not yet bound to
legacy budget v11 or portfolio admission. Profitability, execution, paper/live
permission, runtime activation, public evidence promotion, and real-source
validity remain unproven and unauthorized.
