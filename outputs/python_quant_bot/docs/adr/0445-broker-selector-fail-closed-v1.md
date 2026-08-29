# ADR 0445: Broker selector fail-closed V1

## Status

Accepted on 2026-08-25.

## Context

`build_broker` previously treated every broker other than `ccxt`, and every mode
other than the exact lowercase string `live`, as permission to construct a
`PaperBroker`. Pure in-memory calls demonstrated both unsafe fallbacks:

- `mode="paper", broker="papre"` returned `PaperBroker`.
- `mode="staging", broker="paper"` returned `PaperBroker`.

The file-loader clamp is not a complete boundary because callers can construct or
mutate `BotConfig` directly. A typo or unregistered execution mode therefore
crossed the selector as if it were an explicitly supported local execution path.

## Decision

The V1 selector is fail-closed before broker construction:

- Registered local modes are exactly `paper` and `backtest`, case-insensitive.
- The only registered local broker is `paper`, case-insensitive.
- Surrounding whitespace, empty values, non-string selectors, and a non-boolean
  `live_trading_enabled` value are rejected explicitly.
- Any `live` mode, `ccxt` broker, or true live flag hits the permanent live hard
  wall before local selector admission.
- Unknown mode and broker values raise `ValueError`; they never default to
  `PaperBroker`.

The selector does not mutate the supplied configuration and does not submit an
order. `PaperBroker` pricing and portfolio accounting are unchanged.

## Consumer activation

`build_broker` is the existing shared consumer boundary used by the CLI and legacy
dashboard runtime builders. Activating strict admission there makes all current
consumers fail closed without introducing a second selector or compatibility
adapter. The normal file-loader output (`paper` plus a false live flag) remains a
registered shape.

Constructing a local simulator object is not paper-trading authorization. Paper
and live tasks remain unauthorized, and the permanent live hard wall remains in
force.

## Adversarial contract

The dedicated synthetic test matrix covers:

- the registered `paper/backtest` paths;
- misspelled and unknown brokers;
- unknown modes;
- lowercase and uppercase live indicators;
- a true or malformed live flag;
- non-string, empty-equivalent, and whitespace-padded selectors;
- fee and slippage propagation on the admitted local path.

The tests construct objects only. They do not submit orders, start services, read
runtime state, or invoke paper/live tasks.

## Evidence and authority boundary

This decision does not modify the natural-forward artifact chain, legacy public
read behavior, pointer contracts, UI wording, or any trading permission. It is a
configuration admission hardening result, not profitability evidence.
