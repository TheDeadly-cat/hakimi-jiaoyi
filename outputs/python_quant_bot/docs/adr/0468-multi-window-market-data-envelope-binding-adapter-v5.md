# ADR0468: Multi-window market-data envelope binding adapter v5

## Status

Accepted as an unmounted, synthetic, research-only adapter on 2026-08-25. It
does not authenticate a provider, connect a real feed, switch current, or grant
paper/live authority.

## Current gap

ADR0467 recomputes every Pearson matrix from one exact return panel, but its
evaluator accepts a caller-supplied panel and has no market-data-envelope or
provider input. A pure synthetic panel therefore passes with a panel hash while
provider identity is absent. Content integrity is not source binding.

The canonical application contract already verifies per-symbol
`market-data-envelope-v1` sidecars, hashes observed rows, binds provider strings,
locks paper/live authority, and rejects missing, incomplete, synthetic,
fallback, unknown-provider, symbol, timeframe, source, row, and hash drift. A
new duplicate envelope is unnecessary.

## Decision

Add a thin adapter-v5 that:

1. Calls the canonical market-data-envelope verifier and complete-source
   consumer for every symbol.
2. Requires native payload identity, known provider string, complete rows,
   positive finite closes, exact row source, strictly increasing `ts_ms`, and a
   bounded row count.
3. Requires every symbol to share the identical 1D timestamp grid.
4. Derives the common return panel exclusively from close-to-close ratios and
   does not accept caller-injected returns.
5. Structurally preregisters each symbol/provider/dataset-hash/grid commitment,
   the expected panel hash, and exact ADR0467 lineage-preregistration hash.
6. Exact-verifies the ADR0467 adapter using the derived panel.
7. Preserves an exact ADR0467 BLOCK as BLOCK; any source, binding, derivation,
   or exact-verification failure is UNKNOWN without source summaries.
8. Keeps raw rows and envelopes out of output.
9. Marks provider identity as structurally bound but explicitly unauthenticated.
10. Keeps runtime, current, writer, paper, and live authority false.

## Consumer-first order

1. Keep the canonical envelope consumer required and fail closed.
2. Land this unmounted binding adapter with synthetic envelope fixtures.
3. Specify a separately authenticated provider-identity and source-transport
   contract before any claim of trusted or real market data.
4. Independently anchor preregistration chronology and cutoff before natural
   forward shadow use.
5. Require separate authorization for any real read-only source, dual-read,
   current, writer, paper, or live step. No step activates the next one.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact complete canonical envelopes on one grid | adapter PASS |
| Exact downstream lineage BLOCK | adapter preserves BLOCK |
| Missing, synthetic/fallback, or incomplete envelope | UNKNOWN |
| Payload row changed without sidecar update | UNKNOWN |
| Coherently resealed source with old binding/lineage | UNKNOWN |
| Timestamp-grid drift | UNKNOWN |
| Wrong binding pin or provider drift | UNKNOWN |
| Resealed summary or authority promotion | exact verifier rejects |
| Input mutation attempt | caller inputs remain unchanged |

## Boundary

All envelope rows are synthetic fixtures. Provider strings are not authenticated
identities, and cache markers are not proof of a real feed. No historical or
real-market task, profitability backtest, G50/G51, formal blind task, service,
browser, scheduler, publication, paper execution, or live execution is used.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued.
