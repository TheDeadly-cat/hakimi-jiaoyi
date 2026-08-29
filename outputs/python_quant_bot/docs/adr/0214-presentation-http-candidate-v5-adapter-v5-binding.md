# ADR 0214: Presentation HTTP candidate-v5 adapter-v5 binding

## Status

Accepted as an unregistered, synthetic, read-only candidate. It is not mounted and does not activate `current`.

## Context

Presentation HTTP candidate-v4 exactly consumes preregistration-v10 and projects the neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` view. Portfolio-risk adapter-v5 was added later to join the weighted single-window decision with the multi-window correlation-cluster stability gate.

A pure synthetic call-chain counterexample established the consumption gap:

- a valid adapter-v5 joint document can be built and exactly verified;
- candidate-v4 has no adapter-v5 input;
- its payload contains neither `adapter_v5_hash` nor `cluster_partition_stable` evidence;
- adding the valid adapter-v5 document to the exact v4 request correctly returns `UNKNOWN`;
- therefore v4 cannot present the new joint-risk evidence without a versioned successor.

The gap proof passed `6/6` assertions. It used only in-memory fixtures and did not read runtime assets.

## Decision

Add candidate-v5 as a separate unregistered interface contract.

Candidate-v5:

1. accepts an exact v4 request plus an adapter-v5 document;
2. accepts v4 and adapter-v5 verification contexts only as keyword-only inputs;
3. rebuilds and exactly verifies candidate-v4 through its public API;
4. exactly verifies adapter-v5 through its public verifier;
5. rejects source status, fact, seal, lineage, and authority promotion;
6. projects only hashes, calibrated state, and the four neutral presentation axes;
7. never embeds source documents, contexts, positions, or correlation matrices;
8. remains `UNREGISTERED_CANDIDATE` and `KNOWN_BLOCKED` even when the local joint-risk gate passes;
9. keeps transport, route, UI mount, runtime mutation, `current`, paper, and live authority false;
10. pins candidate-v4, adapter-v5, and strict-canonical implementations by SHA256.

The response is deterministic and sealed. Its verifier accepts only an exact rebuild from the original inputs and contexts.

## Consumer-first activation order

1. Keep candidate-v5 synthetic and unmounted.
2. Complete targeted and independent adversarial review.
3. Review a separate registration or mount preregistration only if provenance and compatibility remain closed.
4. Add a runtime/HTTP route only under explicit later authorization.
5. Never auto-switch `current`, reissue pointer-v2, or promote paper/live authority.

## Consequences

- Existing candidate-v4 and preregistration-v10 remain immutable.
- Existing production HTTP and runtime contracts remain unchanged.
- Adapter-v5 `PASS` is displayed only as a local research-gate fact; it is not a profitability, readiness, or permission claim.
- Adapter-v5 `UNKNOWN/BLOCK` is preserved as a visible `GAP` while permission remains unauthorized.
- Legacy pack-v5 public reads and the natural-forward single-look chain are unaffected.

## Non-goals

- No HTTP route registration.
- No UI mount or stylesheet change.
- No runtime, cache, database, provider, scheduler, browser, paper, live, or order access.
- No return backtest or profitability claim.
- No `current` activation, evidence-pack publication, or pointer reissue.
