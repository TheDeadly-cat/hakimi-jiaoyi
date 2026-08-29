# ADR 0497: Market-data envelope identity lock v1

## Status

Accepted as an additive symbol/timeframe identity hardening. It changes no market-data fetch, provider connection, strategy selection, runtime mount, HTTP route, current selector, pointer, frontend, paper path, or live path.

## Context

The envelope builder converted `symbol` and `timeframe` through `str(...)`. Pure synthetic calls proved that integer/Boolean identities, a symbol containing a newline, and a timeframe containing the decision-ID pipe delimiter all passed the complete-consumer path.

ADR0494 rejects those values when a candle decision ID is later built, but the market-data boundary should not admit ambiguous strategy identity and defer failure to a later layer.

## Decision

Apply one identity policy across the application builder, serialized verifier, and domain envelope constructor:

1. The original symbol/timeframe value must be a string.
2. The builder retains existing trim behavior for valid strings.
3. The normalized value must be nonempty and no longer than 128 characters.
4. Pipe delimiters, C0 controls, DEL, Unicode line separators, and Unicode paragraph separators are rejected.
5. Serialized envelopes and direct domain constructors require already-canonical values, so whitespace or injected identities cannot be trusted after construction.
6. Existing valid symbol and timeframe bytes remain unchanged.

## Claim boundary

This closes local type-coercion, control-character, and delimiter ambiguity at the envelope identity boundary. It does not prove symbol existence, venue mapping, timeframe semantics, market-data truth, strategy quality, profitability, or trading permission.

## Compatibility and authority

No ID migration, runtime state, provider data, cache, database, or market task is read. Schemas remain v1.

Natural-forward evidence chain, legacy pack-v5 `UNKNOWN`/null behavior, pointer-v2, paper lock, and live lock remain unchanged.
