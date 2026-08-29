# ADR0500: Correlation v5 complete-source test-fixture marker compatibility v1

Date: 2026-08-25

## Status

Accepted as a test-harness compatibility closure. It does not change the
market-data envelope schema, complete-source admission policy, adapter-v5
implementation, provider authentication claims, runtime wiring, or current
evidence pointers.

## Current gap evidence

ADR0495 expanded the fail-closed non-real source vocabulary to include
`fixture`. The older positive adapter-v5 fixture still used providers named
`fixture_cache_a`, `fixture_cache_b`, and `fixture_cache_c`. A direct in-memory
call now correctly classifies those rows as synthetic fallback and blocks
`consume_market_data_envelope(..., require_complete=True)`.

The loader integration positive case and the cache-only server integration case
also used `fixture_cache` as their complete-source token. Both were therefore
blocked before alignment by the same correct production policy.

This prevented the synthetic correlation fixture chain from reaching its
intended structural adapter contracts. It did not show that the production
complete-source gate was wrong. A two-row probe confirmed:

- `fixture_cache_a` is fallback with two synthetic rows and is blocked;
- `synthetic_fallback_a` is fallback with two synthetic rows and is blocked;
- a neutral logical provider token has two structurally real rows, no fallback,
  and passes the complete-source shape gate without becoming authenticated.

## Decision

1. Preserve the production envelope classifier and adapter-v5
   `require_complete=True` call unchanged.
2. Rename only positive unit-contract provider tokens. Adapter-v5 and loader
   fixtures use `unverified_primary_feed_*`; the cache-only server fixture uses
   `unverified_primary_cache` and still records one cache row. The values remain
   generated in memory and are not market evidence; the tokens model complete
   structural provider branches.
3. Preserve `provider_identity_authenticated=False` and every research-only
   authority lock.
4. Add `fixture_cache_*` to the explicit adapter and loader negative matrix
   beside synthetic, missing-envelope, and incomplete-row cases. Rejected v5
   adapter outputs remain UNKNOWN with no source summaries, and rejected loader
   inputs never reach alignment.
5. Do not introduce a test-only production bypass, monkeypatch the consumer, or
   relax synthetic/fallback rejection.

## Compatibility boundary

The change affects fixture construction only. Dynamic downstream correlation
fixtures may rebuild different synthetic hashes because their logical provider
token changed. No persisted artifact, pointer, current pack, runtime source, or
public contract is reissued.

## Adversarial matrix

- a complete neutral logical provider fixture reaches the structural v5 path;
- a neutral cache fixture records cache lineage without synthetic fallback;
- a provider containing `fixture` remains synthetic fallback and is rejected;
- a provider containing `synthetic` or `fallback` remains rejected;
- missing envelopes and incomplete rows remain UNKNOWN;
- source summaries remain empty on every source-tier rejection;
- provider identity remains structurally bound but unauthenticated;
- no paper, live, writer, current-admission, or profitability authority opens.

## Safety boundaries

All evidence is generated in memory. No market data, old K-line, runtime,
database, cache, log, credential, backtest, blind test, scheduler, service,
browser, paper, or live task is used. Passing these contracts is not market
source authentication, profitability evidence, strategy maturity, trading
authorization, or release approval. The single-look chain, legacy pack-v5
UNKNOWN behavior, and pointer-v2 no-reissue contract remain unchanged.
