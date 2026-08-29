# ADR 0494: Candle decision ID delimiter lock v1

## Status

Accepted as a backward-compatible anti-replay identifier hardening. It changes no engine selection, reservation backend, runtime state, database, current selector, pointer, HTTP route, frontend, paper path, or live path.

## Context

`build_candle_decision_id` formats six normalized components with a literal pipe delimiter. Component values were not checked for that delimiter.

Two distinct input tuples could therefore generate the same identifier. For example, moving `|symbol:` between the strategy and symbol values produced byte-identical output. This creates an avoidable collision and log-forging surface in a key used by decision reservation.

Changing every valid identifier to a new hash format would require a migration against reservation state, which is outside this task and cannot be justified without reading protected runtime assets.

## Decision

Keep the existing v1 output format and its established case, trim, and empty-value normalization for valid inputs. Add a construction-time input-domain lock that:

1. Requires string components, except that the existing optional strategy version may remain `None` and normalize to `v1`.
2. Rejects the pipe delimiter in every component.
3. Rejects C0 control characters, DEL, and Unicode line/paragraph separators.
4. Rejects leading or trailing whitespace in candle-close time instead of silently changing reservation identity.
5. Bounds strategy, symbol, timeframe, action, and version to 128 characters and candle-close time to 256 characters.
6. Raises stable `ValueError` codes before constructing an ambiguous reservation key.

Normal identifiers remain byte-for-byte unchanged. Inputs that could previously collide now fail closed.

## Claim boundary

This proves only local decision-ID input disjointness with respect to the reserved delimiter and bounded control-character policy. It does not prove global uniqueness, durable reservation, runtime replay prevention, market-data truth, profitability, or paper/live authorization.

## Compatibility and authority

No reservation data is read or migrated. The engine continues to call the same v1 builder. Existing valid IDs remain unchanged, so no current consumer switch is required.

The natural-forward public chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 reads remain `UNKNOWN`/null. Pointer-v2 is unchanged and is not reissued.
