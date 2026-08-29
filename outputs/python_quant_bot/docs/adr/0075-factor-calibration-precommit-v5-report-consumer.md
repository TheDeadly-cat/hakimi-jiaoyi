# ADR 0075: Factor calibration precommit v5 report consumer

## Status

Candidate only. Read-only, unmounted, and not current.

## Decision

Add a public aggregate-only consumer for precommit v5. The consumer replays the
official v5 verifier with the complete v4, order-v2, v3, order-v1, v2, energy,
v1, H0, declaration, source-report, replay, registration, and observation
context before exposing any result.

The only observed states are `VERIFIED_LOCAL_BINDING` and `VERIFIED_BLOCK`.
Missing, unsupported, mismatched, or coherently resealed inputs remain
`UNKNOWN`. Rows, per-fold values, returns, factors, and private ledgers are not
publicly projected.

## Limits

Verification does not prove residual independence, profitability, external
timing, or execution authority. Presentation mounting, current admission,
paper, and live remain disabled.
