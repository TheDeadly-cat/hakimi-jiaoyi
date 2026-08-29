# ADR 0330: Strategy correlation matrix geometry to complete-link binding v1

- Status: accepted as an unmounted research-only candidate
- Date: 2026-08-24
- Scope: synthetic, in-memory contract evidence only
- Authority: no current admission, writer, paper, or live permission

## Context

ADR0329 introduced a positive-semidefinite geometry gate for strategy correlation
matrices.  The existing complete-link cluster consumer still accepted its matrix
directly, so the geometry result was not a required predecessor.  Pairwise-valid
but globally impossible correlation matrices could therefore reach that consumer
when called outside the new geometry module.

## Decision

Add an unmounted versioned binding:

`exchange_terminal.services.strategy_correlation_matrix_geometry_complete_link_binding_v1`

The binding preregisters exact producer and consumer identities and enforces this
order for one immutable synthetic request snapshot:

1. Verify the existing correlation-matrix contract.
2. Verify the exact geometry preregistration for the matrix symbol order.
3. Verify the exact geometry gate document against the same matrix and require
   its status to be `PASS`.
4. Invoke the existing complete-link gate v2.  That primary consumer evaluation
   owns construction of its embedded complete-link audit.
5. Independently reconstruct the complete gate with the reviewed evaluator
   callable captured when the binding module was imported.  Require exact audit
   and gate self-hashes plus full-document equality with this reconstruction.
6. Apply the existing audit and gate verifiers as an additional check.  This
   verification replay is separate from the primary consumer invocation.
7. Return evidence-only output with all current authority flags false.

Lock-3 preregisters the research-only lane allowlist `RAW_EXCESS` and `research`.
`RAW_EXCESS` is the existing effective-budget research lane.  Any other lane,
including paper/live labels, is rejected before complete-link invocation.

Missing, forged, stale, cross-matrix, or non-PASS geometry evidence prevents the
complete-link consumer from being called.  A consumer exception or forged audit
or gate document returns `UNKNOWN`, including a forgery whose attacker recomputed
its self-hash.  A valid non-PSD matrix returns `BLOCK` before consumer invocation.

## Pinned dependencies

- Geometry provider source SHA-256:
  `f2f4ac9b9989e925440ce4fd4a46174f3ea3d5d96e1fe9fe81d9808b29829e30`
- Complete-link consumer source SHA-256:
  `a44851d07ce6757f11763f8f76f5036129ab0a718094a9cb1b46886781885be8`
- Correlation matrix/preregistration contract source SHA-256:
  `90cfa45aa05b3fd3d915221ece7e7c5ef4634a334ac3099080f60133b56b62b3`

Any dependency drift requires a new review and contract version.  The source-pin
checks are activation evidence, not runtime authority.

## Consumer-first activation order

1. Keep this binding unmounted and register no HTTP, scheduler, writer, or engine
   consumer.
2. Review exact source pins, preregistration hashes, and independent adversarial
   evidence.
3. If a later ADR proposes a consumer, make that consumer require this exact
   binding evaluation and reject missing geometry without a compatibility path.
4. Activate a current pointer only after a separate authorization decision.

This ADR does not activate `current`, republish pointer-v2, alter the natural
forward chain, or authorize paper/live execution.

## Adversarial acceptance matrix

- Exact PSD geometry plus authentic complete-link output: binding evidence
  `PASS`; underlying gate status is preserved; authority remains false.
- Geometry evidence absent: `UNKNOWN`; consumer not invoked.
- Geometry document changed without rebuilding: `UNKNOWN`; consumer not invoked.
- Geometry document belongs to another matrix: `UNKNOWN`; consumer not invoked.
- Pairwise-valid but non-PSD matrix: `BLOCK`; consumer not invoked.
- Binding preregistration changed: `UNKNOWN`; consumer not invoked.
- Non-research lane: `BLOCK`; consumer not invoked.
- Existing `RAW_EXCESS` research lane: exact consumer evidence may be produced;
  all current authority remains false.
- Consumer exception: `UNKNOWN`; no consumer document trusted.
- Forged embedded audit with a recomputed audit and gate hash: `UNKNOWN`; gate
  not trusted.
- Forged outer gate with a recomputed gate hash: `UNKNOWN`; exact audit may
  remain trusted, but no gate or authority is accepted.

## Consequences

The gap between geometry validation and the real complete-link consumer is now
closed in a narrow, independently testable candidate.  The candidate remains
unmounted, synthetic-only, and evidence-only.  It does not change the existing
single-look evidence chain or establish profitability, readiness, or trading
permission.
