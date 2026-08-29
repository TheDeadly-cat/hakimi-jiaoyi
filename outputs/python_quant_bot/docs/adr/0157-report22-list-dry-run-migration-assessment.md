# ADR 0157: Report22 list/dry-run migration assessment

- Status: Accepted, non-executing research-only assessment
- Date: 2026-08-22

## Context

Registration-v10 records that the report22 verifier and in-memory builder are
available as candidates, but explicitly records no migration assessment. A
migration boundary is needed before any writer design, while the project policy
permits only list and dry-run analysis and forbids fresh migration.

The existing report21 migration projection is a redacted public summary. It is
not an execution plan and should not be overloaded with internal validation
inputs or mode semantics.

## Decision

Add an internal, sealed migration assessment with exactly two modes:

- LIST verifies registration-v10 and lists three planned steps without accepting
  or evaluating a report22 document.
- DRY_RUN verifies registration-v10, independently verifies a supplied report22
  extension and evaluates migration prerequisites without executing them.

Both modes fix planned to 3 and executed to 0. Runtime, filesystem, cache,
database, network, service and scheduler mutations are all false. FRESH is not
a valid mode.

A structurally valid report22 BLOCK remains a valid dry-run assessment with a
BLOCK report decision. It cannot be promoted to PASS by the migration layer.

## Adversarial requirements

- Registration and report hashes are independently caller-bound.
- Invalid sources and wrong hashes produce BLOCK assessments.
- LIST rejects a supplied report; FRESH raises before assessment.
- Resealed execution, runtime mutation or activation claims fail exact rebuild.
- Native aliases and authority escalation fail closed.
- Inputs are not mutated or embedded.
- No run, fresh, writer or current function is exported.

## Boundary

This assessment does not call lean or any migration command. It does not read or
write runtime state, files, cache or databases, start services, persist report22,
activate current, reissue pointer-v2, change the public single-look chain, prove
profitability or data authenticity, or authorize paper/live trading.
