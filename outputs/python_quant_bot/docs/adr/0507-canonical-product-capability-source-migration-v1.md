# ADR0507: Canonical Product Capability Source Migration v1

## Status

Accepted locally as the first consumer-first production source migration. It is
not current on GitHub until separately authorized, committed, and pushed.

## Context

The active product capability catalog was implemented inside
`outputs/python_quant_bot/exchange_terminal/domain/contracts.py`. That file also
owns market-data envelope contracts and is imported by many legacy terminal
consumers. Moving the entire project or duplicating the catalog under a new path
would either create a high-risk flag day or two authoritative implementations.

## Decision

1. Establish repository-root `src/hakimi_research` as the canonical source root.
2. Move the complete capability-v1 and product-capability-catalog-v1 implementation
   into `src/hakimi_research/product_capabilities.py`.
3. Make `run_bot.py` and `dashboard_app.py` consume the canonical module directly.
4. Keep `exchange_terminal.domain.contracts` as an identity-preserving compatibility
   export for existing terminal consumers; it may not redefine migrated symbols.
5. Add `_canonical_source.py` as a narrow compatibility bootstrap while the old
   project root remains executable without package installation.
6. Extend the root CI path filter and Python path to cover `src/**`.

## Consumer-first activation

1. Add canonical source with unchanged schemas, fixed items, and authority locks.
2. Activate the compatibility bootstrap without changing public object identity.
3. Switch the active CLI and dashboard imports to canonical source.
4. Prove legacy/canonical identity, canonical source location, active consumer
   imports, and absence of duplicate definitions.
5. Retain the compatibility export until all remaining imports have migrated.

## Removal criteria

The compatibility bootstrap and legacy exports may be removed only after a
separate audited slice proves that all source, test, Electron, documentation, and
packaging consumers resolve the canonical package without `outputs` path setup.
No directory move or wrapper removal is implied by this ADR alone.

## Fail-closed boundaries

- The migrated values, exact-native checks, schema versions, CLI statuses, and
  permanent research-only authority locks are unchanged.
- No paper/live/order implementation, runtime path, market data, service, browser,
  scheduler, formal backtest, or publication action is added or invoked.
- A compatibility import is not evidence that the whole project has migrated.
- CI and GitHub currentness remain UNKNOWN until an actual remote run consumes the
  committed source layout.

## Local acceptance target

- Canonical migration adversarial tests: 5/5 PASS.
- Targeted research contracts including CI and migration: 89/89 PASS.
- Python syntax for eight affected files: 8/8 PASS.
- Deterministic input verifier: 8/8 PASS.
- `git diff --check`: PASS.
