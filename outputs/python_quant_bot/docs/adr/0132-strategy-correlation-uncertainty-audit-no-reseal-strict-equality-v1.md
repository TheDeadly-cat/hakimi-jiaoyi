# ADR 0132: Strategy correlation uncertainty audit no-reseal strict equality v1

## Status

Accepted as verifier-only research hardening. This decision does not activate a
writer, register a route, admit a current artifact, or authorize paper/live use.

Static fingerprint:
20260822-strategy-correlation-uncertainty-audit-no-reseal-strict-equality-1

## Context

A no-reseal attack keeps the original audit_hash while replacing exactly one
boolean leaf with integer 0 or 1. Python container equality can then treat the
attacked document as equal to its canonical rebuild even though the JSON types
differ.

The real uncertainty-audit synthetic document contains 201 boolean leaves.
Before this decision, 11 attacks passed verification:

- four policy control fields
- three cross-cluster pair flags
- four audit-level evidence or authority fields

Strict rebuild prediction rejects all 11. The other 190 attacks were already
blocked by existing hash, policy, authority, or structural checks.

Actual protocol registration v1 and v2 were also tested with 29 no-reseal
attacks and accepted none, so protocol registration remains unchanged.

## Decision

Use strict_json_contract_equal for the uncertainty audit's final exact rebuild
comparison. Leave uncertainty policy equality unchanged because its six attacks
were already blocked.

Keep schemas, builders, audit_hash generation, blocker names, matrix replay
verification, status vocabulary, and permissions unchanged.

## Compatibility and authority

This hardening does not change the natural-forward evidence chain, legacy
pack-v5 UNKNOWN behavior, pointer-v2 fields or hash contract, current admission,
route registration, profitability claims, paper authorization, or live
authorization. Verifier PASS remains document-integrity evidence only.
