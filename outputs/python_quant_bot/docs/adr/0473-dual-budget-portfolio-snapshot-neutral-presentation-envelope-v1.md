# ADR 0473: Dual-budget portfolio-snapshot neutral presentation envelope v1

- Status: accepted as an unmounted research-only candidate
- Date: 2026-08-25
- Scope: synthetic contract presentation only

## Context

The v9 dual-budget portfolio-snapshot reconciliation closes a local contract
boundary. Its raw document is not a frontend contract: it does not define a
stable presentation order, a bounded disclosure shape, or a separate permission
stage. A local `PASS` can therefore be misread as external data maturity or
execution authority if a future consumer renders the raw document directly.

The missing boundary is demonstrated with a synthetic, read-only source shape:
the raw v9 shape has no `axis_order` or `stages`; the presentation envelope adds
both without invoking market data, runtime state, paper trading, or live trading.

## Decision

Add
`strategy_correlation_cluster_dual_budget_portfolio_snapshot_presentation_envelope_v1`
as a service-layer candidate with these properties:

1. It invokes the exact v9 verifier with a detached verification context.
2. It binds the v9 schema, static fingerprint, reconciliation hash, and current
   implementation fingerprint.
3. It emits only a bounded summary. Positions, portfolio snapshots, return
   panels, market-data envelopes, and verification contexts are not projected.
4. It fixes the presentation order to `SOURCE -> GAP -> MATURITY -> PERMISSION`.
5. It keeps external provider identity, external source truth, external
   freshness, formal market evidence, and profitability unproven.
6. It keeps frontend mounting, consumer activation, formal registration,
   current admission, runtime activation, paper, live, and trading locked.
7. Its verifier reconstructs the complete envelope and rejects a correctly
   resealed authority promotion.

`status=PASS` means only that an exact local v9 `PASS` was projected. The
`PERMISSION` stage remains `LOCKED` and carries no execution or activation
authority.

## Consumer-first activation order

1. Keep this envelope unmounted and outside all current registries.
2. Let a future consumer accept only this exact schema and verification receipt.
3. Require the consumer to render the four axes in the declared order and to
   treat all authority fields as immutable locks.
4. Add an HTTP candidate only after its response contract preserves the bounded
   projection and fail-closed unknown behavior.
5. Consider registry or current activation only under a separate ADR and a new
   adversarial review. This ADR grants no such activation.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Raw v9 document lacks presentation stages | Envelope supplies the exact four-axis order |
| Expected source hash is malformed or mismatched | `UNKNOWN_SOURCE`, no source hash disclosed |
| Source schema or fingerprint drifts | `UNKNOWN_SOURCE` |
| Exact source verifier fails or raises | `UNKNOWN_SOURCE` |
| Local v9 status is not `PASS` | Presentation remains blocked and permission locked |
| Local v9 status is `PASS` | Local state is visible, but all activation and trading locks remain |
| Raw portfolio or verification inputs are supplied | They are not projected |
| Authority is promoted and the envelope is resealed | Exact reconstruction rejects it |
| Promotional wording is introduced | Contract tests reject `READY`, profit, buy, or sell wording in visible stages |

## Non-effects

- No service, browser, scheduler, publication flow, backtest, blind test, paper
  task, or live task is started.
- No current pointer or evidence artifact is written or reissued.
- The natural-forward chain remains
  `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
- Legacy pack-v5 public reads remain `UNKNOWN`/null.
- No profitability claim or trading permission is created.
