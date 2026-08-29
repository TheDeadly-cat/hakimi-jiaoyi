# ADR 0377: Concentration Projection Static Presenter v1

- Status: implemented, additive, unmounted
- Date: 2026-08-24
- Scope: pure static view-model, escaped markup, and isolated CSS
- Authority: none

## Decision

Add a strict presenter for the ADR0376 verification envelope. It validates the
complete ADR0375 schema, fixed status path, metric nullability, integer bounds,
blocker ordering, facts, authority locks, and expected hash equality. Invalid
input returns a fixed `UNKNOWN` model without reflecting caller values.

The visual signature combines a maximum-cluster dominance bar, HHI compass, and
effective-cluster scale. Unknown is muted, both block states use rust, and the
within-limit observation uses tide blue rather than success green.

## Neutral vocabulary

- `未核验`
- `上游暴露阻断`
- `集中度门禁阻断`
- `结构分布观察`
- `SOURCE -> GAP -> MATURITY -> PERMISSION`
- `模拟未授权 · 实盘永久硬锁`
- `不构成分散化、准入、仓位、信号、订单或收益结论`

The presenter never uses `READY`. It has no DOM, network, storage, route,
runtime loader, or pointer API and remains absent from current `index.html`.

## Evidence boundary

Node tests prove strict static presentation, escaping, immutability, responsive
CSS, reduced-motion handling, and deliberate non-mounting only. They do not
prove browser rendering, accessibility technology behavior, diversification
quality, market validity, profitability, or trading authorization.
