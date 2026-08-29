# ADR 0032: Protocol-v9 cluster-stability preregistration

- Status: Accepted for preregistration-only implementation
- Date: 2026-08-21

## Context

Report20 now verifies one within-cluster stability gate per report19 identity, but registration-v6/protocol-v8 does not freeze the report20 schema, the external stability binding, the familywise correction, or the writer prerequisites. Designing a writer before those properties are preregistered would permit policy drift after evidence is observed.

## Decision

Add `strategy-correlation-protocol-registration-v7` with `strategy-correlation-cluster-stability-report-policy-v1`, targeting report20 and `strategy-matrix-protocol-v9`. Registration-v7 embeds and independently verifies registration-v6. The policy fixes the stability policy/audit/gate schemas, within-cluster family scope, Bonferroni two-sided familywise correction, source-BLOCK preservation, exact preregistration/matrix/selection binding, one gate per report identity, caller-supplied gate and report19 hashes, and native JSON type exactness.

Report20 must not copy the source uncertainty audit, correlation matrix, selection cells, or returns into report entries. Writer activation additionally requires verified report19 and registry bindings, verified report20, exact stability rebuilds, a sole report20 writer, formal registry activation, and a migration audit.

## Consequences

The policy is frozen before any writer exists. Registration status is PREREGISTERED, while formal registry binding, writer availability, current admission, paper authorization, and live authority remain false. Registration-v6 and report19 remain immutable and replayable.
