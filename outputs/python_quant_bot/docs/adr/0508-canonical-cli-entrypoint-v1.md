# ADR0508: Canonical CLI Entrypoint v1

## Status

Accepted locally as the second consumer-first source migration boundary. It is
not current on GitHub until separately authorized, committed, and pushed.

## Context

`outputs/python_quant_bot/run_bot.py` still owned all CLI command logic after the
product capability catalog moved to canonical source. Adding a new launcher that
delegated to that file would preserve the wrong source authority and create only
the appearance of a unique entrypoint.

## Decision

1. Move the complete CLI implementation to `src/hakimi_research/cli.py`.
2. Add `src/hakimi_research/__main__.py` so the canonical Python entrypoint is
   `python -m hakimi_research`.
3. Add root `hakimi-research.ps1` as the documented Windows entrypoint. It sets
   only source paths, temporarily uses the legacy project working directory, and
   invokes the canonical module once.
4. Reduce `outputs/python_quant_bot/run_bot.py` to identity-preserving compatibility
   exports plus the legacy script `main()` call.
5. Keep quant_bot imports behind `activate_legacy_project_root()` until those
   modules migrate in later audited slices.

## Stable path correction

The canonical CLI binds its default config, report directory, and experiment
context to the existing project root rather than its new source-file directory.
This prevents source migration from silently changing config identity, dependency
lock lookup, or report placement.

## Consumer-first activation

1. Add canonical source-layout and CLI modules.
2. Preserve all legacy public CLI objects by identity.
3. Add and test the module entrypoint from an unrelated temporary directory.
4. Switch documentation to the root launcher.
5. Keep the old script only for compatibility until downstream callers migrate.

## Fail-closed boundaries

- Supported commands remain exactly backtest, capabilities, and list-strategies.
- Paper and optimize functions remain archived and permanently disabled.
- The launcher contains no service, browser, network, scheduler, paper/live,
  order, or publication action.
- The entrypoint test executes only the side-effect-free capabilities consumer.
- This migration does not move quant_bot, exchange_terminal, Electron, or runtime
  assets and does not prove the whole source migration complete.

## Local acceptance target

- Canonical CLI entrypoint adversarial tests: 5/5 PASS.
- Targeted research contracts: 89/89 PASS.
- Python syntax for seven CLI-boundary files: 7/7 PASS.
- PowerShell parser: 1/1 PASS.
- Deterministic input verifier: 8/8 PASS.
- `git diff --check`: PASS.
