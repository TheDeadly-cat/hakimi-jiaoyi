# ADR 0050: Cross-lag consumer-first activation

- Status: C1 implemented and independently reviewed; C2-C5 not authorized
- Date: 2026-08-21
- Scope: Research evidence only
- Authority: None

## Context

The versioned cross-lag dependence gate is implemented as a pure, synthetic-data
research boundary. It evaluates the preregistered lag family `-2, -1, +1, +2`
across every cross-stratum pair, applies one family-wide multiplicity correction,
and reports conservative dependence evidence.

The current source tree intentionally has no cross-lag report consumer, protocol,
public projection, registry writer, pointer writer, or mounted UI. That absence is
the safe baseline. A gate result must not acquire maturity or permission merely
because a downstream file is added.

## Decision

Activation is consumer-first and monotonic. Each stage must be complete and
adversarially verified before the next stage is introduced.

### Stage C0: Core gate

Current state. The gate remains pure and candidate-only. It performs no file,
database, network, scheduler, paper, or live operation.

### Stage C1: Read-only report consumer v1

The first implementation slice will add only a pure report consumer and its
tests. The consumer must:

- accept exactly one strict canonical cross-lag evaluation;
- invoke the official core verifier rather than duplicate hash or semantic logic;
- reject schema, fingerprint, lag-family, pair-family, count, and authority drift;
- distinguish `NOT_SUPPLIED`, `UNKNOWN`, `OBSERVED_PASS`, and `OBSERVED_BLOCK`;
- expose aggregate evidence only, never raw return series;
- emit the neutral axes `SOURCE`, `GAP`, `MATURITY`, and `PERMISSION`;
- keep `formal_registry_written`, `current_pointer_written`, `paper_authorized`,
  and `live_order_allowed` strictly `false`;
- perform no I/O and accept no path, URL, callback, or writer dependency.

The report schema will be `strategy-correlation-cross-lag-report-v1`. Its hash
will bind the exact source evaluation hash, core schema, core static fingerprint,
preregistered lag family, cross-stratum pair count, lag-test count, dependent-test
count, decision, and every permission field.

### Stage C2: Protocol binding v1

Only after C1 passes an independent adversarial review may a protocol bind the
report to preregistration evidence. The protocol may describe a candidate binding;
it may not write a registry, update a pointer, or infer formal maturity.

### Stage C3: Redacted public projection v1

Only after C2 is complete may a public projection consume the protocol. It must
fail closed to `UNKNOWN` on any invalid, partial, truthy-alias, or mismatched input.
It may expose aggregate counts and neutral state, but not raw series, per-symbol
returns, local paths, or untrusted text.

### Stage C4: Unmounted presentation

A static presentation may be added only after C3. It remains unmounted until its
Node contract proves target scoping, text-only rendering, responsive layout,
reduced-motion behavior, and absence of profit, readiness, activation, paper, or
live implications.

### Stage C5: Formal state

There is no automatic transition to formal state. Any registry or current-pointer
work requires a separate ADR, explicit authorization, a migration contract, and
an independent review. Existing pointers must not be reissued as a side effect.

## Fail-closed adversarial matrix

Stage C1 is incomplete until tests cover all of the following:

| Case | Required result |
| --- | --- |
| Missing evaluation | `NOT_SUPPLIED`, every permission false |
| Non-mapping input | `UNKNOWN`, every permission false |
| Core schema drift | `UNKNOWN` |
| Static fingerprint drift | `UNKNOWN` |
| Broken canonical hash | `UNKNOWN` |
| Coherently resealed metric tamper | `UNKNOWN` |
| Missing, duplicate, reordered, or extra lag | `UNKNOWN` |
| Missing, duplicate, or extra pair-lag result | `UNKNOWN` |
| Pair/count mismatch | `UNKNOWN` |
| Non-finite or pseudo-numeric metric | `UNKNOWN` |
| Boolean/numeric/string authority alias | `UNKNOWN` |
| Decision/evidence mismatch | `UNKNOWN` |
| Extra untrusted field | Not reflected in the report |
| Valid dependent result | `OBSERVED_BLOCK`, not `UNKNOWN` |
| Valid independent result | `OBSERVED_PASS`, still candidate-only |

At least one tamper test must first assert that the selected source metric is
nonzero before changing it, so a no-op mutation cannot masquerade as verifier
coverage.

## Consumer-first acceptance order

1. Pure synthetic gap proof.
2. Versioned C1 schema and official-verifier dependency.
3. C1 positive, negative, and coherent-reseal tests.
4. Independent adversarial review of C1.
5. Lean list/dry-run registration with zero executed checks.
6. Baseline-document synchronization.
7. Consider C2 in a separate change.

No backtest, natural-forward result, simulation, or unit test is profitability
evidence or trading authorization.

## Consequences

This order keeps the core gate useful while preventing a partial downstream chain
from being mistaken for maturity. It also avoids copying verifier logic into UI or
protocol layers and gives each later stage a single, narrow trust boundary.

## C1 implementation evidence

- Consumer: `strategy_correlation_cross_lag_report_consumer.py`
- Contract: `strategy-correlation-cross-lag-report-consumer-verification-v1`
- Static fingerprint: `20260821-cross-lag-report-consumer-1`
- Targeted consumer tests: 15/15 passed
- Core gate plus consumer tests: 32/32 passed
- Independent field-level probe: redaction, I/O denial, verifier-exception
  fail-closed behavior, and native-boolean authority locks passed
- Lean v2: 9 planned, 0 completed, 0 executed, 0 reused; runtime mutation,
  paper authorization, and live-order authority remain false

This evidence closes C1 only. It does not activate C2-C5 and does not create or
update a registry, pointer, scheduler, service, paper account, or live authority.
