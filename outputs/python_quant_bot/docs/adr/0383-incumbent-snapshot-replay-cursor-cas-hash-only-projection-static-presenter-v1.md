# ADR0383: Replay Cursor CAS Projection Static Presenter v1

## Status

Implemented as additive, isolated, and deliberately unmounted static assets.

## Context

ADR0382 closes the exact Python-to-JavaScript verification handoff for ADR0381.
The next consumer can therefore present CAS evidence without trusting a bare
projection or inventing runtime authority.

## Decision

Add a strict static presenter that accepts only the exact four-field ADR0382
envelope. It validates every ADR0381 key, hash shape, fixed authority and
redaction record, outcome-to-gate mapping, safe integer, sequence relationship,
consumer status, and expected projection hash equality.

Invalid input returns a fixed UNKNOWN model without reflecting caller values.
Accepted models are deeply frozen and rendered markup escapes every value.

The isolated visual language is a CAS switchboard with observed, candidate, and
returned sequence nodes, a competition rail, hash-lineage ledger, and explicit
commit gaps. Tide blue indicates a synthetic observation, amber an unresolved
conflict, and rust a block. No success green is used.

## Neutral vocabulary

- `未核验`;
- `回放阻断`;
- `序列阻断`;
- `并发竞争未闭合`;
- `合成游标观察`;
- `SOURCE -> GAP -> MATURITY -> PERMISSION`;
- `模拟未授权 · 实盘永久硬锁`;
- `不构成提交、持仓、准入、信号、订单或收益结论`.

The presenter never uses READY. It has no DOM, network, storage, route,
runtime-loader, pointer, mount, or publication API and remains absent from the
current index.

## Cross-language evidence

Python builds real ADR0382 envelopes for synthetic advance, CAS conflict, and
duplicate block, then passes each through stdin to the actual Node presenter.
Node accepts exact envelopes with unchanged gate semantics. Mutated authority or
attacker text returns fixed UNKNOWN, and redacted Python material cannot be
recovered from the view model or markup.

Node tests additionally prove exact schemas, impossible sequence rejection,
escaping, deep immutability, responsive CSS, focus-visible treatment,
reduced-motion handling, and deliberate non-mounting.

## Non-claims

These tests do not prove browser rendering, assistive-technology behavior,
native zoom, storage CAS, durability, linearizability, provider identity,
current activation, real holdings, wall-clock freshness, strategy performance,
profitability, paper authority, or live authority.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. pointer-v2 remains unchanged
and is not reissued.
