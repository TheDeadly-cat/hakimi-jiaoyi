# ADR 0009: Consumer-first market-data envelope gate

Status: Accepted for protocol-v5/schema16 research admission; no current-pointer switch

## Context

`MarketDataEnvelope` and `MarketDataSourceManifest` were declared domain contracts but had no producer-consumer path. Research loaders therefore accepted raw row dictionaries without a local, exact binding between symbol, timeframe, provider, completed-row semantics, dataset hash, and authority flags.

This is a provenance gap, not evidence of a strategy return problem. No historical run is repeated to demonstrate it.

## Decision

Use `market-data-envelope-v1` as a sidecar on `backtest_market_rows` results. The application adapter recomputes an exact canonical row hash and source manifest. The shared matrix loader verifies the sidecar before alignment, then removes it so existing downstream alignment and report hashes do not drift.

Activation order is consumer-first:

1. Define a strict application verifier and adversarial synthetic fixtures.
2. Add the producer sidecar at both stock and crypto return paths.
3. Validate and strip every present sidecar before alignment.
4. Require the sidecar only for protocol-v5/schema16 selection and holdout loads.
5. Keep legacy callers compatible with a missing sidecar, but fail closed if a sidecar is present and invalid.

Admission requires non-empty completed rows, zero synthetic rows, no fallback, a known provider, exact symbol/timeframe/source/row binding, `research_only=true`, `paper_authorized=false`, and `live_order_allowed=false`.

## Consequences

- The former declaration-only boundary is now wired end to end for schema16 inputs.
- Tampered rows, hashes, sources, authority flags, incomplete rows, and synthetic fallback block before alignment.
- Existing downstream payload shape is preserved after verification.
- No current pointer is switched or reissued.
- The gate is research provenance only. It is not profitability evidence and grants no paper or live authority.
