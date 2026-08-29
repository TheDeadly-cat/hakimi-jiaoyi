# ADR 0086: Factor Calibration Precommit Presentation Envelope v4

- Date: 2026-09-14
- Status: Accepted for local research, unmounted

## Context

Report consumer v7 closes the finite-horizon omnibus composition gap for lags
4, 5, and 6. Presentation envelope v3 is intentionally bound to report
consumer v6 and only represents lags 1 through 3. Reusing it through a
compatibility path would hide a verified omnibus block.

## Decision

Add presentation envelope v4 as an exact consumer of report consumer v7. It
fully re-verifies the consumer and its complete source context before mapping
the result to the neutral SOURCE, GAP, MATURITY, and PERMISSION axes.

- VERIFIED_LOCAL_BINDING maps to LOCAL_BINDING.
- VERIFIED_BLOCK maps to EVIDENCE_BLOCK.
- Missing, unsupported, invalid, or mismatched context maps to UNKNOWN.
- GAP remains OPEN for lags above 6 and external timing.
- PERMISSION remains LOCKED for current, profitability, paper, and live.

The MATURITY and phase-comb projections expose six preregistered coverage teeth,
the omnibus band 4 through 6, and one quadratic-energy aggregate and ceiling.
They do not expose per-lag results, rows, returns, beta values, residual values,
identities, or private ledgers.

## Consequences

- The known consumer-v6-positive and consumer-v7-block synthetic path becomes
  EVIDENCE_BLOCK rather than a misleading local-binding presentation.
- The envelope remains unmounted and has no route, DOM hook, current pointer,
  scheduler, paper path, or live path.
- A detached card may consume this exact schema in a later consumer-first
  slice. No existing v3 card receives compatibility authority.
