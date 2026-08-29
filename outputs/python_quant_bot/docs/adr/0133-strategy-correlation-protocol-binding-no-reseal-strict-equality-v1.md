# ADR 0133: Strategy correlation protocol binding no-reseal strict equality v1

## Status

Accepted as verifier-only research hardening. This decision does not perform a
registry transaction, activate a writer, admit a current artifact, or authorize
paper/live use.

Static fingerprint:
20260822-strategy-correlation-protocol-binding-no-reseal-strict-equality-1

## Context

A pure synthetic protocol binding assessment contains 19 boolean leaves. A
no-reseal attack keeps the original assessment_hash while replacing one boolean
with integer 0 or 1.

Before this decision, 17 attacks passed verification because Python container
equality treats booleans and integers as equal. The two remaining authority
fields were already blocked. Strict rebuild prediction rejects all 17 accepted
attacks.

A separate resealed matrix accepted none of 19 attacks. Actual protocol
registration v1 and v2 also accepted none of 29 no-reseal attacks.

## Decision

Use strict_json_contract_equal for the protocol binding assessment's final
exact rebuild comparison.

Keep assessment schema, builder, assessment_hash generation, blocker names,
source verifier contracts, formal-registry gap, status vocabulary, and
permissions unchanged.

Validation must use the pure synthetic local-chain fixture only. The wider test
module contains temporary SQLite and report-artifact scenarios and is outside
this light-test slice.

## Compatibility and authority

This hardening does not change the natural-forward evidence chain, legacy
pack-v5 UNKNOWN behavior, pointer-v2 fields or hash contract, current admission,
route registration, formal registry state, profitability claims, paper
authorization, or live authorization.
