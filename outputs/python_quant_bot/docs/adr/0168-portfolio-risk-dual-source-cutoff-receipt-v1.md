# ADR 0168: Portfolio-risk dual-source cutoff receipt v1

## Status

Accepted as an additive, provider-assertion-only research contract on
2026-08-22. It is not a trusted-provider implementation, shadow consumer,
runtime gate, paper authorization, or live authorization.

## Context

ADR0166 deliberately consumes two different correlation representations. The
legacy proposal-centered gate consumes portfolio-risk-budget-v1 pair maps. The
all-cluster gate consumes strategy-selection-correlation-matrix-v1 documents.
Both formats bind symbols, lookback, overlap requirements, and canonical matrix
hashes, but neither payload contains an observation cutoff.

A future shadow consumer cannot infer that both matrices describe the same
market prefix merely because both report PASS or use a 60-observation window.
Last-row dates must not be guessed from the result payload because those rows
are absent from both matrix documents.

## Decision

Add two exact source envelopes and one dual-source alignment receipt.

Each envelope:

1. Verifies the role-specific matrix schema and canonical payload hash.
2. Requires a strict provider identifier, completed-daily-return assertion, and
   second-precision UTC observation cutoff.
3. Binds the assertion to payload hash, symbol universe, lookback, and minimum
   pair overlap.
4. Excludes the matrix, pair values, raw rows, and source data.
5. States that provider identity is unauthenticated and cutoff is not native to
   the matrix payload.

The receipt exact-verifies both envelopes against externally expected provider
identifiers, cutoff, return series, and symbol universe. It passes only when
both payloads remain valid and their cutoff, symbols, lookback, overlap, and
return-series assertions align.

The receipt decision DUAL_SOURCE_PROVIDER_ASSERTIONS_ALIGNED means only that
two sealed provider assertions are structurally aligned. It does not establish
provider authenticity, data truth, freshness at consumption time, profitability,
or execution authority.

## Adversarial matrix

The targeted contract covers missing native cutoff proof, valid legacy and
complete-link envelopes, malformed provider IDs, cutoff and scalar aliases,
payload tampering, resealed metadata and authority changes, external cutoff
mismatch, symbol-universe mismatch, valid-but-different lookback windows,
expected-metadata aliases, receipt resealing, input immutability, source
redaction, and research-only authority fields.

## Consumer-first order

1. Freeze and independently review envelope and receipt v1.
2. Bind authenticated provider identity and raw observation manifests.
3. Add freshness and cutoff-to-session verification at shadow-consumption time.
4. Preregister a shadow-only application consumer.
5. Run isolated synthetic shadow calls before any server or runtime registration.
6. Require separate current-switch authorization.

## Remaining blockers

- Provider identity is not authenticated.
- Matrix payloads do not natively prove their asserted cutoff.
- Raw observation manifests and per-symbol last-completed sessions are absent.
- No freshness, timeout, persistence, replay, or monitoring contract exists.
- No shadow, application, HTTP, runtime, current, paper, or live consumer exists.

## Consequences

Window, symbol-universe, and cutoff drift can now be rejected before a future
shadow consumer combines the two correlation sources. Current behavior remains
unchanged. The natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2. No backtest, profitability claim, paper authority, or
live authority follows from this receipt.
