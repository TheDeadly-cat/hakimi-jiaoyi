# ADR 0155: Report22 deterministic in-memory builder

- Status: Accepted, unactivated research-only builder
- Date: 2026-08-22

## Context

ADR0154 added report22 verification but intentionally provided no construction
path. Hand-assembling a report22 document in downstream code would duplicate
identity joins, permit inconsistent expected hashes and weaken the verifier-only
boundary.

## Decision

Add one deterministic in-memory builder. Each input contains:

- the exact report identity;
- the existing temporal source audit, matrix and selection cells;
- the independently expected temporal-v1 gate hash;
- the independently expected temporal date-grid gate hash.

The builder requires the input identity set to equal the report21 identity set.
It verifies report21 using the derived temporal bindings, rebuilds each date-grid
gate from embedded report19/report20/report21 evidence, compares both expected
hashes, constructs report22 and invokes the report22 verifier before returning.

The builder deep-copies external inputs and does not mutate report21 or caller
bindings. A structurally valid BLOCK gate produces a valid report22 BLOCK
decision. Invalid contracts and hash mismatches raise without returning a
document.

## Adversarial requirements

- The aligned verifier fixture rebuilds byte-for-byte deterministically.
- A 40-common-date fixture builds only a BLOCK decision.
- Wrong temporal-v1 or date-grid expected hashes fail closed.
- Missing, duplicate and extra identities fail closed.
- Native container subclasses, input extras and output aliases are rejected.
- Report21 and caller inputs are not mutated.
- No writer, filesystem I/O, migration or current switch is exported.

## Boundary

The builder returns an in-memory candidate only. It does not persist, publish,
migrate, activate current, reissue pointer-v2, prove external data authenticity
or profitability, or authorize paper/live trading. The public single-look chain
and legacy pack-v5 UNKNOWN behavior remain unchanged.
