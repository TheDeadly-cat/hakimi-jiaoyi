# ADR 0496: Market-data envelope source-marker type lock v1

## Status

Accepted as an additive source-normalization hardening. It changes no provider connection, market-data fetch, runtime mount, cache, database, HTTP route, current selector, pointer, frontend, paper path, or live path.

## Context

ADR0495 conservatively classifies empty and explicitly non-real source words. The builder still converted arbitrary provider and row-source values through `str(...)`.

Pure synthetic calls proved that integer, Boolean, mapping, and newline-bearing source values were converted into nonempty strings, classified as real rows, and accepted by `require_complete=True`.

This is a separate type/confusion and control-character bypass. It is not evidence that a current provider emits those values.

## Decision

1. Accept provider and row-source markers only when the original value is a string.
2. Trim valid strings while preserving provider case and using lowercase only for classification.
3. Treat empty, longer-than-256, C0-control, DEL, Unicode line-separator, and Unicode paragraph-separator strings as invalid.
4. Normalize an invalid provider to `unknown`, which is fallback under ADR0495.
5. Normalize an invalid row source to empty, which is synthetic/fallback under ADR0495.
6. Use the same provider normalization in the builder and consumer so structural verification remains deterministic.
7. Reject control-bearing and oversized provider strings in direct `MarketDataSourceManifest` construction.

No source value is converted from an unrelated Python type into provenance text.

## Compatibility

Valid string markers retain existing trim and case behavior. Known cache/local markers remain eligible under ADR0495. Manifest and envelope schema versions do not change.

## Claim boundary

This closes type-coercion, control-character, and unbounded-marker bypasses only. A valid source string still does not prove provider identity, market-data truth, completeness, freshness, durability, profitability, or trading permission.

No runtime or market-data task is executed. Natural-forward evidence chain, legacy pack-v5 `UNKNOWN`/null behavior, pointer-v2, paper lock, and live lock remain unchanged.
