# ADR0503: Product capability catalog v1

Date: 2026-08-29

## Status

Accepted as a local source contract. This does not activate runtime, paper,
live, order, optimizer, scheduler, browser, or publication paths.

## Context

The exact `capability-v1` authority contract correctly locks the product to
research-only mode, but legacy README, CLI, Streamlit, and example configuration
surfaces still described paper execution and parameter optimization as usable.
The authority lock alone did not express whether a product feature was
Supported, Experimental, Disabled, Archived, or Planned.

## Decision

Add `product-capability-catalog-v1` beside the existing typed domain capability
contract. It binds a fixed capability inventory, CLI command bindings, and the
unchanged `capability-v1` authority document.

Supported CLI commands are derived from the catalog. Legacy `paper` and
`optimize` functions remain import-compatible fail-closed guards, but are
Archived and absent from CLI choices. The Streamlit consumer exposes only the
capability boundary, historical backtest, research reports, and local logs.

The wire-level `capability-v1` payload remains unchanged so the current Python
health producer and Electron consumer do not need a synchronized protocol
switch. The natural-forward single-look chain, legacy pack-v5 UNKNOWN reads,
and pointer-v2 no-reissue contract are unchanged.

## Capability states

- Supported: current documented product behavior.
- Experimental: research UI behavior without stability or authority claims.
- Disabled: intentionally unavailable behavior.
- Archived: legacy code may remain for compatibility but has no product entry.
- Planned: not implemented and not advertised as available.

## Consequences

README, CLI, example configuration, and the legacy dashboard now describe the
same research-only product. Internal historical fill simulation remains an
implementation detail and does not grant paper authority. Tests bind the exact
catalog, CLI choices, documentation rows, archived functions, and unchanged
authority payload.

No backtest result, report, catalog status, or passing contract proves
profitability, strategy maturity, paper authorization, or live permission.
