# ADR 0153: Temporal date-grid protocol-v11 preregistration

- Status: Accepted, unactivated research-only preregistration
- Date: 2026-08-22

## Context

ADR0151 introduced the exact shared date-grid consumer. ADR0152 bound that
consumer externally to report21 and proved that a report21 PASS cannot remain a
valid upgraded candidate when its date-grid decision is BLOCK.

The existing protocol-v10 registration targets report21 and predates both
contracts. Mutating registration-v8 or protocol-v10 in place would create
compatibility drift and could make old report21 evidence appear preregistered
for a rule it never contained.

## Decision

Add registration-v9 as an independent successor to registration-v8. It targets
report22 and strategy-matrix-protocol-v11, and hash-binds both:

- the exact ADR0151 temporal date-grid gate policy;
- a report policy requiring one independently rebuilt date-grid gate per report
  identity;
- caller-supplied expected date-grid gate hashes;
- the rule that report21 PASS implies every date-grid gate decision is PASS;
- exclusion of replay assets, raw price rows and raw dates from report22.

The registration records the ADR0152 candidate binding schema, but explicitly
sets report22 consumer and writer availability to false. Preregistration does
not claim that report22 can be built or verified.

## Activation prerequisites

- Source registration-v8 independently verifies.
- Date-grid gate and report policy hashes match exactly.
- Report21 and its external hash independently verify.
- Date-grid binding identity sets match report identities exactly.
- Every date-grid gate is rebuilt and independently hash-bound.
- A report22 consumer is implemented and verified.
- A sole writer and migration audit are separately implemented.
- Formal registry activation receives explicit authorization.

## Adversarial requirements

- Source registration drift blocks registration-v9.
- Gate-policy and report-policy reseals cannot change semantics.
- Native numeric aliases and authority escalation fail closed.
- Source registration is not mutated by the builder.
- report22 consumer, writer and current switch remain absent.

## Boundary

This ADR preregisters policy only. It does not implement report22, a writer,
migration, current admission, pointer reissue, market-data authenticity,
profitability evidence, paper permission or live trading authority. The public
single-look chain, legacy pack-v5 UNKNOWN behavior and pointer-v2 remain
unchanged.
