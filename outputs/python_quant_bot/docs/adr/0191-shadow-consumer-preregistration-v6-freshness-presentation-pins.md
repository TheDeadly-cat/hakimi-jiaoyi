# ADR 0191: Shadow-consumer preregistration v6 freshness presentation pins

## Status

Accepted as an immutable, `BLOCKED`, research-only preregistration. It does not
activate a consumer, mount UI, register HTTP, switch `current`, or grant runtime,
paper, live, registry, writer, or migration authority.

## Context

ADR0186 preregistration-v5 freezes the original fourteen shadow inputs, three
local blocker closures, and twenty-six implementation fingerprints through the
adapter-v2/projection-v2 presentation layer. ADR0187-ADR0190 add corrected
lineage, a joint local decision, a minimal public projection, and an unmounted
freshness card. Those contracts are implemented but not preregistered by v5.

## Decision

Add immutable shadow-consumer preregistration-v6. It first invokes the public v5
exact verifier through a strict three-key predecessor context, then requires an
exact thirty-three-entry implementation manifest. Seven new pins are added:

1. immutable shadow preregistration-v5
2. adapter-v2/session-freshness lineage binding-v1
3. corrected uncertainty-aware lineage binding-v2
4. portfolio-risk adapter-v3
5. portfolio-risk projection-v3
6. freshness-gate card-v3 JavaScript
7. freshness-gate card-v3 stylesheet

The predecessor's fourteen input schemas and three closed local blockers are
byte-preserved. No adapter, projection, lineage, DOM, browser, HTTP, or runtime
evidence instance is accepted by the v6 API.

## Evidence separation

Every new capability records `contract_pinned=true` only when the exact manifest
matches. It always records `evidence_bound=false`, `consumer_executed=false`, and
`external_authority_verified=false`. New blockers explicitly retain missing
lineage evidence, adapter-v3 evidence, projection-v3 evidence, DOM review,
browser visual review, and presentation HTTP versioning.

The status remains `BLOCKED` even with a fully matching manifest. A hash pin is
not evidence that a consumer ran, a browser rendered, a market condition was
observed, a strategy is profitable, or trading is authorized.

## Consumer-first activation order

1. Bind and exactly verify ADR0188 lineage evidence.
2. Bind and exactly verify ADR0189 adapter-v3 evidence.
3. Bind and exactly verify ADR0190 projection-v3 evidence.
4. Register an isolated, still-unmounted presentation consumer fixture.
5. Separately authorize isolated DOM and browser visual review.
6. Version the presentation HTTP contract before any mount.
7. Keep `current` switch authorization last and separate.

## Adversarial matrix

The contract covers each of seven new hash drifts, missing/extra manifest keys,
v5 tampering, predecessor-context shape drift, exact verifier tamper, immutable
fourteen-input and three-closure preservation, blocker ordering, activation
ordering, output redaction, deterministic non-mutation, API narrowing, import
boundaries, neutral wording, and permanent authority denial.

## Compatibility and evidence boundaries

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 fields and hash contract
are unchanged and no pointer is reissued. No runtime assets, market tasks,
backtests, services, browsers, schedulers, or trading paths are used.
