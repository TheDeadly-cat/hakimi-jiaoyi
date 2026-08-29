# ADR 0024: Protocol-v8 global-independence preregistration

- Status: Accepted, preregistration-only
- Date: 2026-08-21
- Registration: `strategy-correlation-protocol-registration-v6`
- Policy: `strategy-correlation-global-independence-policy-v1`
- Target: report schema 19 / `strategy-matrix-protocol-v8`

## Context

The report-19 consumer can verify cross-dimension vote compression, but a
consumer alone does not freeze the policy before evidence is observed. Protocol
v8 therefore needs a preregistration that inherits the independently verified
protocol-v7 registration and fixes the report-19 schemas, graph definition,
exact-search algorithm, limits, and evidence thresholds.

## Decision

Registration-v6 accepts only an exact, independently verified registration-v5.
Its policy freezes:

- conflicts as any shared parent stratum across all registered dimensions;
- exact maximum independent set, with no approximation fallback;
- exact limits of 24 clusters and 250,000 search nodes;
- at least two globally independent votes and a fixed 60 percent fraction;
- both registered and passing independent capacities;
- independently verified report 18, caller-supplied base report hash, and
  caller-supplied registry bindings;
- exact global gate-v2 reconstruction and contract-status/decision separation;
- native JSON type exactness for version and authority constants.

The registration is package-only, matching the existing protocol chain. It is
not a formal registry and does not add a report writer, persistence, scheduler,
pointer mutation, paper authority, live authority, or current activation.

## Activation order

1. Keep report19 and protocol-v8 verification consumer-only.
2. Add a separately reviewed formal protocol-v8 registry asset.
3. Add persistence and a schema19 sole writer with migration tests.
4. Re-run independent contract and authority review.
5. Consider current-pointer activation only after every prerequisite passes;
   this ADR does not authorize it.

## Consequences

The policy can now be preregistered before any report19 evidence is consumed,
without implying that a real registry or writer exists. Research, simulation,
backtest, and natural-forward evidence remain non-profitability evidence and do
not grant paper or live trading permission.
