# ADR 0446: Protective exit contract V1

## Status

Accepted on 2026-08-25.

## Context

`RiskManager.enforce_stop_rules` previously compared unvalidated floating-point
values directly. Pure in-memory calls demonstrated three distinct fail-open
behaviors:

- a `NaN` market price returned no protective order;
- a `NaN` stop threshold silently disabled the stop;
- an infinite market price produced a sell order with an infinite price.

The method also used the caller-provided stop threshold directly. A 50% threshold
therefore bypassed a configured `max_single_loss_pct` of 3%, even though
`effective_stop_loss` calculated the intended 3% cap.

## Decision

Protective Exit Contract V1 is enforced inside the shared risk boundary:

- Open-position quantity, average entry price, market price, configured maximum
  loss, stop threshold, and take-profit threshold must be finite numeric values;
  booleans are not accepted as numbers.
- Open positions require positive quantity, average entry price, and market price.
- `max_single_loss_pct` is a mandatory global ceiling. An omitted stop uses that
  ceiling, a wider signal stop is capped, and a tighter signal stop is preserved.
- A derived non-finite return percentage is rejected before order construction.
- Invalid contracts raise `ValueError`; they never silently suppress a stop or
  construct a malformed order.
- Valid take-profit and flat-portfolio behavior remains unchanged.

The method remains pure with respect to portfolio state. It can return a proposed
protective sell order but never submits one or mutates the portfolio.

## Consumer activation

The contract is activated in `RiskManager.enforce_stop_rules`, the existing shared
consumer boundary. Consumers that already pass `effective_stop_loss` remain
compatible because applying the cap twice is idempotent. Consumers that pass raw
or omitted stop values now receive the mandatory configured protection without a
parallel adapter or compatibility fallback.

## Adversarial contract

The dedicated synthetic matrix covers:

- omitted, wider, and tighter stop thresholds;
- `NaN`, positive/negative infinity, zero, negative, boolean, and non-numeric
  market prices;
- malformed open-position quantity and average entry price;
- malformed stop, take-profit, and global single-loss thresholds;
- valid take-profit and flat-position behavior;
- portfolio non-mutation on rejection.

No broker is constructed and no order is submitted by these tests.

## Evidence and authority boundary

This is a protective-order calculation hardening result. It does not change the
natural-forward artifact chain, pointer contracts, legacy public reads, UI
wording, paper/live authorization, or any profitability claim.
