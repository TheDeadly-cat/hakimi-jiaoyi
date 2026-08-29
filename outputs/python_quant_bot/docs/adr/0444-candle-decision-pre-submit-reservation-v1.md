# ADR 0444: Candle decision pre-submit reservation V1

- Status: Accepted
- Date: 2026-08-25
- Scope: legacy research engine safety and idempotency

## Problem

TradingEngine previously had two compatibility and safety gaps:

- failure to import the canonical domain decision-id builder silently selected
  a second legacy formatting contract;
- an ordinary signal order reached the broker before its candle decision was
  persisted, and persistence failure was only logged.

The second behavior allowed a process restart to forget a submitted decision
and retry the same candle.

## Decision

The engine imports the canonical domain builder directly.  Import failure now
fails closed instead of changing the decision identity contract.

For ordinary signal orders, the engine persists the existing state-v1 decision
value before broker submission:

1. Build the canonical candle decision identity.
2. Reject an existing identical reservation.
3. Save the new reservation and persist it.
4. Submit to the broker only after persistence succeeds.
5. Retain the reservation if broker submission raises, because the external
   result may be ambiguous and automatic retry could duplicate an order.

If reservation persistence fails, the in-memory prior value is restored and
the broker is not called.

## Compatibility

The legacy_engine_decision_state.json version and decisions mapping remain
unchanged.  Existing string reservations continue to load without migration.
No paper or live capability is added.

Forced stop-rule orders are intentionally unchanged because they have different
position-reduction and retry semantics.  Their broker idempotency remains a
separate review item.

## Validation boundary

The contract is exercised only with a synthetic DataFrame, fake strategy,
fake risk manager, fake broker, mocks, and a temporary directory.  No service,
runtime asset, market source, browser, scheduler, paper broker, live broker, or
trading task is started.

## Safety

This change reduces duplicate-submission risk but does not prove broker-side
idempotency, execution outcome, profitability, current maturity, paper
authorization, or live authorization.  The single-look chain and pointer-v2
remain unchanged.
