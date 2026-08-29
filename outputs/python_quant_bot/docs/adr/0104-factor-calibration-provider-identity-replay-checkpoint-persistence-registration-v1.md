# ADR 0104: Provider identity replay checkpoint persistence registration v1

## Status

Accepted as an inactive research-only preregistration candidate. No persistence
provider, local I/O, database, runtime store, network operation, producer, or
`current` integration is implemented.

## Context

ADR 0103 verifies checkpoint consistency against a caller-supplied pinned
checkpoint. That pin is not durable or authoritative merely because it is an
input. Existing cluster-stability formal persistence is strategy-specific,
contains no provider, and explicitly rejects supplied provider evidence. Reuse
would merge research-artifact persistence with replay-registry lineage.

## Decision

Preregister a separate checkpoint persistence consumer boundary. The contract
binds the sealed ADR 0102 replay registration and fixes:

- a distinct persistence provider, namespace, adapter, and implementation hash;
- a persistence-provider signing key role separate from provider receipt,
  identity registry, and replay registry key roles;
- exact pinned-asset, write-receipt, and reopen-receipt schemas;
- canonical SHA-256 and strict base64url Ed25519 contracts;
- distinct write/reopen sessions;
- exactly one record after reopen;
- exact canonical record-hash replay;
- write-before-reopen ordering;
- external-receipt-only mode with no local I/O.

The highest state is `PERSISTENCE_ADAPTER_REGISTERED_RECEIPTS_UNOBSERVED`.
Registration does not imply a write, reopen, durable store, or authoritative
future pin.

The static fingerprint is
`20260928-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-checkpoint-persistence-registration-1`.

## Authority boundary

Persistence provider checked, durable write/reopen, session separation,
authoritative pin, replay registry checked, replay absence, uniqueness, provider
identity, admission, selection, paper, and live authority all remain false.

## Consumer-first activation order

1. Land and adversarially test this exact registration.
2. Implement a write/reopen receipt verifier with strict signatures, distinct
   sessions, cardinality one, and exact record replay.
3. Add isolated synthetic provider fixtures only after the verifier exists.
4. Establish independent provider trust and durable-store evidence.
5. Compose a verified persisted asset into ADR 0103 under a separate decision.
6. Keep uniqueness/freshness, presentation, and `current` as later boundaries.

## Consequences

This closes preregistration only. It does not prove durability, uniqueness,
freshness, profitability, or trading permission.

## Validation

- Targeted synthetic registration tests: 20/20.
- Independent key-role and policy matrix: 15/15.
- Factor-calibration family: 732/732.
- In-memory compile: 2/2.
- Lean list/dry-run: planned 19, executed 0, runtime mutations false.
- Active integration references: 0.

These checks prove only the sealed preregistration implementation. They do not
prove any write, reopen, durable storage, external provider trust, uniqueness,
freshness, profitability, or trading authorization.