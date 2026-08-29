# ADR 0087: Detached Factor Calibration Finite-Horizon Card v4

- Date: 2026-09-15
- Status: Accepted for local research, detached

## Context

Presentation envelope v4 exposes a finite-horizon six-lag aggregate with a
distinct omnibus band over lags 4, 5, and 6. The detached v3 card is exactly
bound to the older three-lag envelope and cannot represent the omnibus guard
without hiding its source boundary.

## Decision

Add a new exact-schema detached card v4. Its strict verifier requires the
envelope-v4 schema, fingerprint, top-level key set, canonical hash, expected
hash, source/consumer/precommit/omnibus cross-bindings, six ordered coverage
teeth, exact omnibus band, Q aggregate semantics, open GAP, and locked
PERMISSION.

The visual direction is a finite-horizon laboratory instrument:

- lags 1 through 3 form a mineral-blue baseline comb;
- a structural Q GUARD seam separates source coverage;
- lags 4 through 6 form an amber omnibus comb;
- a single dark elliptical aperture displays Q(04-06) and its ceiling;
- the four evidence axes remain a quiet numbered rail.

Rendering uses only an explicitly supplied detached document and textContent.
The component has responsive layouts and reduced-motion support, but no page
activation hook.

## Consequences

- A verified consumer-v7 block remains EVIDENCE_BLOCK in the card even when the
  older consumer-v6 source remains locally positive.
- No rows, returns, beta values, residual values, identities, per-lag results,
  or private ledgers enter the model or DOM.
- The card remains detached and has no app import, DOM-ready hook, route,
  current pointer, scheduler, paper path, or live path.
