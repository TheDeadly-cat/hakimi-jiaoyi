# ADR 0493: Domain research-only contract construction lock v1

## Status

Accepted as an additive domain safety hardening. It changes no runtime mount, evidence selector, pointer, HTTP route, scheduler, frontend, paper path, or live path.

## Context

The serialized market-data envelope verifier already rejects research, paper, live, manifest, and row-binding drift. The underlying frozen dataclasses did not enforce those invariants at construction time.

Callers could therefore create a contradictory object such as `research_only=False`, `paper_authorized=True`, or `live_order_allowed=True` and pass it through code before serialization. Frozen dataclasses prevent field reassignment but do not validate constructor values or protect nested row dictionaries from alias mutation.

`MarketDataSourceManifest` also accepted negative or Boolean row counts, non-Boolean flags, noncanonical provider strings, and arbitrary dataset-hash strings.

## Decision

Enforce fail-closed construction invariants in `exchange_terminal.domain.contracts`:

1. `CapabilityContract` accepts only `product_mode=research_only`, `research_only=true`, `paper_allowed=false`, `live_allowed=false`, and schema `capability-v1`.
2. `MarketDataSourceManifest` requires a nonempty trimmed provider, exact nonnegative integer counts, `cache_rows <= real_rows`, exact Boolean flags, lowercase 64-character SHA-256, and schema v1.
3. Any positive synthetic-row count requires `fallback=true`.
4. `MarketDataEnvelope` requires canonical nonempty symbol/timeframe strings, a list of mapping rows, an exact manifest object, and a row count matching `real_rows + synthetic_rows`.
5. Envelope authority remains permanently `research_only=true`, `paper_authorized=false`, and `live_order_allowed=false` under schema v1.
6. Envelope construction copies input rows, and `to_dict()` returns a second copy so caller mutation cannot alter the domain object's retained row values.

The application builder and serialized verifier remain the authority for provider/row-source classification and strict-canonical dataset-hash recomputation. The domain layer does not import application or service hashing code.

## Compatibility

Existing valid builder output remains unchanged. Invalid direct constructors now fail earlier with stable `ValueError` codes rather than allowing contradictory objects to propagate to a later verifier.

The natural-forward public chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain `UNKNOWN`/null. Pointer-v2 fields and hash contract remain unchanged, and no pointer is reissued.

## Non-claims

This hardening proves only local constructor and copy-isolation behavior. It does not prove market-data truth, source authority, dataset completeness, strategy quality, profitability, or paper/live authorization.
