# ADR 0498: Market-data envelope source-affinity lock v1

## Status

Accepted as an additive provider/row provenance-consistency hardening. It changes no provider connection, market-data fetch, schema, runtime mount, cache, database, HTTP route, current selector, pointer, frontend, paper path, or live path.

## Context

The v1 manifest records one provider and per-row source markers but did not require them to agree. Pure synthetic calls proved that `provider=okx,row=futu`, `provider=okx,row=okx_cache`, and a mixed `okx/futu` row set all produced `fallback=false` and passed `require_complete=True`.

A single-provider manifest cannot establish provenance for differently labeled rows without an explicit cross-source composition contract.

## Decision

After ADR0495/0496 normalization, compare every lowercase row-source marker with the lowercase provider marker.

If any marker differs, classify the whole manifest as `fallback=true`. Do not guess that cache, local, API, websocket, or other suffixes belong to the same provider family. An upstream producer that owns such an equivalence must emit one exact canonical label or introduce a separately verified composition contract.

Case-only and outer-whitespace differences remain equivalent after existing normalization. Exact cache labels such as provider and row both equal to `okx_cache` remain compatible.

## Contract separation

The structural verifier may accept a self-consistent mismatch/fallback manifest. The complete consumer continues to reject fallback. This preserves the established `SOURCE -> GAP -> MATURITY -> PERMISSION` separation.

## Claim boundary

This closes local single-provider/row-label inconsistency only. Matching free-form labels do not prove provider identity, source authority, market-data truth, completeness, freshness, durability, profitability, or trading permission.

No runtime or market task is executed. Natural-forward evidence chain, legacy pack-v5 `UNKNOWN`/null behavior, pointer-v2, paper lock, and live lock remain unchanged.
