# ADR 0199: Portfolio-risk presentation HTTP candidate v3

## Status

Accepted as an unregistered, side-effect-free HTTP candidate. It defines no
route or method and grants no mount, current, paper, or live authority.

## Context

V8 now exposes a known but blocked local maturity state with exact fixture and
registration evidence closures. The generic `services/http_contract.py` owns
loopback and mutation safety rules and already contains unrelated user changes;
it should not absorb a portfolio-risk payload schema. The architecture also has
an established `interfaces/http` candidate boundary for pure, unregistered
response construction.

Independent review remains incomplete and cannot be self-certified. A separate
versioned HTTP payload can still be defined before any route, DOM, browser, or
mount work.

## Decision

Add
`interfaces/http/strategy_correlation_cluster_portfolio_risk_presentation_candidate_v3.py`.
The candidate:

- accepts an exact request containing v8, v7, and ADR0197 documents;
- accepts the v8 verification context separately and never echoes request or
  context documents;
- public-reverifies v8 and requires `contract_state=KNOWN` with public status
  still `BLOCKED`;
- projects only source hashes, maturity counts, remaining blockers, and the
  neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` axis;
- reports `KNOWN_BLOCKED`, not a permission or readiness state;
- fixes transport to unregistered, externally uncallable, route-less,
  method-less, and free of runtime/cache reads or mutations;
- returns `UNKNOWN` without a payload for malformed requests, malformed
  contexts, verifier errors, source drift, status promotion, or authority
  leakage.

The module does not modify `server.py`, `services/http_contract.py`, `app.js`,
or `index.html`. It therefore versions the candidate response contract without
registering transport or mounting UI.

## Consequences

The v3 HTTP payload can be pinned by a later successor. Independent descriptor
review, actual HTTP transport review, route registration, DOM/browser review,
registration activation, mount, current, runtime, profitability, paper, and
live authority all remain fail-closed.
