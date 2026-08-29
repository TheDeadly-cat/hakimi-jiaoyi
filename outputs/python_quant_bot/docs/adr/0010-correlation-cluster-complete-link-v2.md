# ADR 0010: Complete-link correlation clusters for gate v2

Status: Implemented as a consumer-first contract; not activated as current

## Context

The v1 correlation gate rejects high-correlation pairs placed in different preregistered clusters. It does not require every pair inside one cluster to meet the same threshold. A chain with A-B and B-C above threshold but A-C below threshold can therefore pass topology while collapsing three assets into one vote.

This can undercount independent evidence. It is a topology-contract issue, not return evidence and not a reason to repeat historical research.

## Decision

Add `strategy-correlation-cluster-gate-v2` with a separately sealed `strategy-correlation-cluster-complete-link-audit-v1`.

Every pair inside each preregistered cluster must have at least 40 overlapping completed daily returns and absolute Pearson correlation of at least 0.75. Single-member clusters pass vacuously. V1 remains immutable and replayable.

The v2 gate embeds the v1 result and the complete-link audit, supports exact semantic rebuild verification, and permanently reports current admission, current writer activation, paper authorization, and live authority as false.

## Activation order

1. Validate the v1-PASS/v2-BLOCK chain-link counterexample with synthetic inputs.
2. Adopt the v2 verifier in a new report-schema consumer.
3. Add a sole writer only after consumer and migration tests pass.
4. Do not switch current or reinterpret historical v1 evidence.

## Consequences

- Chained clusters no longer collapse weakly related endpoints into one vote.
- Internal overlap and threshold failures are explicit evidence.
- Existing protocol-v5/schema16 and current pointers are unchanged.
- No result authorizes paper or live trading or establishes profitability.
