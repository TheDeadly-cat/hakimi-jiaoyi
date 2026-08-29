# ADR0175: Portfolio-risk shadow consumer preregistration v2

## Status

Accepted as a successor, immutable `BLOCKED` preregistration. ADR0169 v1 is not
modified. This document cannot activate shadow, risk-service, current, paper,
or live behavior through caller flags.

## Context

ADR0169 fixed the first missing local capability as legacy-matrix derivation
binding, followed by native cutoff and shadow freshness policy. ADR0170 now pins
the deterministic legacy matrix to the attested completed-price chain. ADR0171
provides a native session-label cutoff manifest. ADR0172 preregisters and
evaluates completed-session lag under a dual-source clock attestation while
keeping external time authority unproven.

Those contracts close three local implementation gaps, but they do not make the
legacy `portfolio-shadow-risk-v1` signature adapter-aware and do not establish
external provider or time authority.

## Decision

Add successor preregistration-v2 that:

1. Exact-verifies immutable v1 and pins its fixed preregistration hash.
2. Rechecks all v1 implementation hashes rather than relying only on the v1
   source file.
3. Adds direct source pins for ADR0170, ADR0171, and ADR0172.
4. Marks exactly the legacy-matrix binding, native cutoff manifest, and local
   completed-session freshness policy blockers as locally closed.
5. Defines the six versioned documents a future shadow consumer must accept.
6. Excludes UI/public projection from the shadow input signature.
7. Remains `BLOCKED` with external trust, replay, application consumer,
   risk-service versioning, independent review, and current authorization gaps.

## Remaining blockers

- Legacy shadow service is not adapter-v1 aware.
- Provider dataset-key control is unproven.
- External provider data issuance is unproven.
- The replay registry is unchecked for the bound dataset lineage.
- External time authority is unauthenticated.
- No isolated application shadow consumer exists.
- Risk-service adapter input is not versioned.
- Independent shadow review is missing.
- Current switch is unauthorized.

## Activation order

External provider identity/key control/data issuance and replay are first,
followed by external time authority, an isolated shadow-consumer-v2,
independent synthetic review, risk-service versioning, and a separate current
decision. Paper/live remain unauthorized.

## Consequences

The project now distinguishes locally implemented input integrity from external
trust and runtime consumption. v2 does not call shadow code, replace the legacy
service, register HTTP/UI, read runtime assets, run backtests, or modify the
natural-forward chain or pointer-v2. Local or synthetic evidence remains neither
profitability proof nor trading authority.

## Validation evidence

- Successor-v2 adversarial contract: 16/16 PASS.
- v2, immutable v1, ADR0170, ADR0171, and ADR0172 dependency matrix: 112/112
  PASS.
- In-memory Python compilation: 2/2 PASS.

Validation built and exact-verified preregistration documents and inspected the
legacy shadow function signature. It did not execute shadow logic, risk-service,
backtests, market data, runtime assets, HTTP, UI, paper, or live paths.
