# ADR 0156: Report22 candidate capability registration-v10

- Status: Accepted, unactivated candidate capability registration
- Date: 2026-08-22

## Context

Registration-v9 preregistered report22 while truthfully recording that no
consumer or builder existed at that point. ADR0154 and ADR0155 subsequently
implemented a verifier-only consumer and deterministic in-memory builder.
Rewriting registration-v9 would erase that chronology and create compatibility
drift.

## Decision

Add registration-v10 as a successor whose source is registration-v9. It
hash-binds a capability policy containing the exact report22 verifier schema,
builder input schema, callable names and availability scope.

Candidate availability means only that the in-memory verifier and builder are
callable under their exact contracts. It does not mean:

- targeted validation is embedded in the registration;
- validation has authority over admission;
- migration assessment or execution exists;
- fresh migration is allowed;
- a writer, formal registry binding or current path exists.

Those fields remain explicitly false. Registration-v9 remains unchanged and
continues to record its original preregistration state.

## Adversarial requirements

- Invalid or resealed registration-v9 blocks registration-v10.
- Capability-policy drift fails exact reconstruction.
- Native aliases and authority escalation fail closed.
- Building registration-v10 does not mutate registration-v9.
- Callable availability cannot imply validation or activation authority.
- No migration, writer, activation or current function is exported.

## Boundary

This registration records candidate code availability only. It does not run or
embed tests, execute migration, persist report22, activate current, reissue
pointer-v2, change the public single-look chain, prove market authenticity or
profitability, or authorize paper/live trading.
