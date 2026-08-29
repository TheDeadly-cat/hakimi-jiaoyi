# ADR 0495: Market-data envelope source-marker fail-closed v1

## Status

Accepted as a backward-compatible provenance-classification hardening. It changes no provider connection, market-data task, runtime mount, HTTP route, cache, database, current selector, pointer, frontend, paper path, or live path.

## Context

The v1 market-data manifest previously classified a row as synthetic only when its free-form source marker contained `synthetic`. Fallback detection similarly depended on `fallback`.

Pure synthetic calls proved that a complete row marked `generated_model`, and a complete row with no source marker, both produced `real_rows=1`, `synthetic_rows=0`, `fallback=false`. Both were then accepted by `consume_market_data_envelope(..., require_complete=True)`.

This is a fail-open classification defect. It is not evidence that any current provider emits those markers.

## Decision

Keep manifest schema v1 and conservatively classify a row as synthetic/fallback when its normalized source marker is empty or contains an explicit non-real fragment such as synthetic, fallback, generated, mock, fixture, demo, sample, test, simulated, random, placeholder, sandbox, paper, replay, stub, dummy, fake, or unknown.

The provider marker is evaluated by the same policy. A non-real provider forces `fallback=true` even when an individual row marker appears real.

Known cache/local markers remain eligible as non-synthetic rows when they do not contain a non-real fragment. Existing `okx_cache` behavior therefore remains compatible.

## Contract separation

`verify_market_data_envelope` continues to prove that envelope and manifest fields are internally consistent with the classifier. A structurally valid fallback envelope may pass that verifier.

`consume_market_data_envelope(..., require_complete=True)` remains the maturity gate and rejects fallback or synthetic rows. The two responsibilities are intentionally not collapsed.

## Claim boundary

This hardening closes known empty/non-real marker bypasses. A free-form marker can never prove external provider identity, market-data truth, completeness, freshness, or durable provenance. Those claims remain outside this local contract.

No market data, historical K-line, backtest, paper, or live task is run by this ADR. Passing tests do not prove strategy quality or profitability.

## Compatibility

The natural-forward public chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 reads remain `UNKNOWN`/null. Pointer-v2 is unchanged and is not reissued.
