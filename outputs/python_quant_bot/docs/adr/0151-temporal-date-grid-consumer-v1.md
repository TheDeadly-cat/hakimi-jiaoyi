# ADR 0151: Temporal date-grid consumer v1

- Status: Accepted, unactivated research-only candidate
- Date: 2026-08-22

## Context

The temporal-stability v1 consumer splits each symbol's local 60-return array
into three positional windows. The replay layer instead computes pair
correlation from intersecting dates. A pure synthetic adversarial fixture
proved that these semantics can diverge: A and B had 61 price rows each but
only 40 shared return dates, while completed-input verification, replay,
uncertainty, full-window stability, temporal v1 and temporal v1 verification
all returned PASS. Temporal v1 therefore reported three 20-observation
hypotheses without proving 60 common observations.

Preregistration topology itself is closed upstream. Duplicate cluster IDs,
duplicate members and cross-cluster symbol reuse are rejected by the existing
preregistration builder and verifier, so those checks are not duplicated here.

## Decision

Add a versioned consumer after temporal v1. It independently requires every
preregistered symbol to expose the exact same ordered 61-price-date grid before
accepting the source temporal decision. Date intersection, positional
substitution and partial overlap cannot satisfy this gate. The audit exposes
only per-symbol grid hashes and counts, not raw dates.

The consumer preserves source BLOCK, distinguishes structural verification
from decision status, rebuilds exactly during verification and remains
consumer-only. External authenticity, profitability, performance claims,
writer activation, current admission and paper/live permissions remain false.

## Consumer-first activation order

1. Prove the consumer with aligned and adversarial synthetic fixtures.
2. Rebind the report21 protocol and extension candidates to the new gate hash.
3. Run migration list/dry-run and verify zero runtime mutations.
4. Require separate explicit authorization before any current admission.

No step automatically reissues pointer-v2 or changes pack-v6/evidence-v2.

## Adversarial requirements

- Exact 61-row grids preserve an existing temporal PASS.
- Forty shared return dates cannot stand in for three 20-point windows.
- Symbol coverage, row count, date order and grid equality fail closed.
- Coherently resealed grid claims fail exact rebuild.
- Native-number aliases and execution-authority aliases fail closed.
- No writer, current switch, report builder, route or runtime I/O is exported.

## Boundary

This candidate does not change the public single-look chain, legacy pack-v5
UNKNOWN behavior or pointer-v2. It is synthetic contract evidence only, not a
backtest, profitability result, market-data authenticity proof or trading
authorization.
