# ADR 0253: Stratified multi-window anchor adapter-v7

## Status

Accepted as an unmounted, local research adapter on 2026-08-23.

## Observed gap

ADR0252 added a multi-window gate for budget-v3, but no consumer cross-binds its
window set to the single budget-v3 component already used by the stratified
portfolio-risk path. Adapter-v5 has the correct anchor pattern but is explicitly
bound to weighted budget-v2 and multi-window gate-v1. Presentation-v7 accepts one
budget-v3 document and has no gate-v2 input.

A pure synthetic read-only chain proved five predicates:

1. The registered anchor budget-v3 passed.
2. The long-window budget-v3 blocked.
3. Multi-window stratified gate-v2 conservatively blocked.
4. Adapter-v5 rejected the gate-v2 schema.
5. Presentation-v7 had no gate-v2 input.

Without an exact joint consumer, a caller could display the anchor PASS while
omitting the valid long-window BLOCK.

## Decision

Add a separate stratified multi-window anchor adapter-v7. Do not modify
adapter-v5/v6, presentation-v7, the HTTP candidate, or any mounted consumer.

For risk increase, adapter-v7 independently exact-verifies the anchor budget-v3
document and the multi-window gate-v2 document. It then requires these bindings:

1. The configured anchor occurs exactly once in gate window summaries.
2. The configured anchor occurs exactly once in preregistered window specs.
3. The adapter anchor budget document exactly equals the gate anchor document.
4. The adapter anchor verification context exactly equals the gate anchor context.
5. Anchor budget hash, status, decision, and lookback equal the gate summary.
6. The canonical trade identity equals the gate source identity.
7. The gate preregistration hash equals the out-of-band expected hash.

Unknown or spliced sources return `UNKNOWN` and hide both component states and
hashes. For known sources, an anchor BLOCK is preserved first; otherwise a
multi-window gate BLOCK overrides anchor PASS; only two PASS components produce
a local research PASS. Risk reduction remains source free and invokes neither
verifier.

## Consumer-first activation order

1. Keep adapter-v7 standalone and validate pure synthetic contracts.
2. Design a bounded presentation-v8 that jointly verifies the existing
   presentation-v7 and adapter-v7 without changing either source.
3. Add an unregistered HTTP candidate only after presentation-v8 review.
4. Add an unmounted neutral card only after the HTTP contract is frozen.
5. Require separate route/current/mount authorization, which this ADR does not
   grant.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Anchor PASS and gate PASS | Local research PASS |
| Anchor PASS and long-window gate BLOCK | BLOCK |
| Anchor BLOCK | BLOCK before gate decision |
| Anchor document or context splice | UNKNOWN |
| Summary budget hash/status/decision splice | UNKNOWN |
| Missing or duplicate anchor summary | UNKNOWN |
| Anchor lookback mismatch | UNKNOWN |
| Trade identity or preregistration hash splice | UNKNOWN |
| Extra context key or malformed receipt | UNKNOWN |
| Verifier exception | UNKNOWN |
| Re-sealed permission promotion | Exact verifier BLOCK |
| Risk reduction without sources | PASS, no verifier calls |

## Authority and evidence boundary

The adapter output contains component hashes, statuses, decisions, the anchor
window ID, boolean checks, and the canonical trade identity hash only. It does
not embed budgets, matrices, audits, positions, source documents, verification
contexts, or runtime state. Writer, risk-service, runtime, current, registry,
paper, and live authority remain false.

Pure synthetic contracts do not prove future stability, profitability, market
performance, provider trust, or trading authority. No natural-forward artifact,
legacy pack-v5 behavior, pointer-v2 contract, current admission, route, mount,
scheduler, or trading task changes in this slice.
