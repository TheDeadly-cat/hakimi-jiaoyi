# ADR0384: Incumbent Snapshot Replay Cursor Provider Port v1

## Status

Accepted as an unmounted interface contract with a test-only in-memory
conformance candidate.

## Context

ADR0380 can produce a deterministic compare-and-swap transition, but it cannot
prove that a storage provider executed the transition atomically. ADR0381-0383
project and present that limitation without promotion.

The repository already has `AntiReplayRegistryPortV1`, which is exact-bound to a
different source-baseline namespace, witness, challenge, issuance, policy, and
consumption-request schema. Mapping replay-cursor transitions into that command
would require fabricated claims and would create compatibility drift.

## Decision

Add a domain-specific `ReplayCursorProviderPortV1` with one operation:
`compare_and_advance(command)`.

The immutable command is built only by rerunning the exact ADR0380 simulation
against its base cursor. It binds the stream, projection preregistration,
ADR0379 result fingerprint, attestation, ADR0380 intent and request nonce,
synthetic transition receipt, exact base cursor, exact proposed cursor, and a
canonical command hash.

The immutable result has three structural outcomes:

- `ADVANCED`;
- `DUPLICATE_REJECTED`;
- `CONFLICT_REJECTED`.

It carries registry id/revision and observed/returned cursor hashes, but no
field claiming external linearizability, durability, registry identity, paper
authority, or live authority.

Production code defines no provider implementation. A lock-protected in-memory
fake exists only in tests to exercise structural conformance, duplicate-first
ordering, conflict handling, and two-thread behavior. Its outcome is evidence
about that local fake only.

## Consumer-first activation order

1. Keep the port unmounted and the memory fake test-only.
2. Define a provider identity and capability preregistration contract.
3. Define authenticated durable receipt evidence and key rotation.
4. Run an external provider conformance suite against an explicitly authorized
   temporary provider.
5. Add a later result/receipt verifier that cannot promote v1 structural
   results.
6. Review HTTP/current activation separately.

## Adversarial matrix

- exact base cursor advances once in the memory fake;
- sequential duplicate rejects before stale-base conflict;
- changed but still-fresh cursor conflicts;
- two local threads produce one advance and one duplicate;
- blocked ADR0379 evidence cannot build a command;
- wrong expected hashes cannot build a command;
- tampered command fields or schema aliases are rejected;
- invalid result enum, revision, schema, or cursor-hash relation is rejected;
- the specialized fake does not satisfy the unrelated generic anti-replay port;
- production interface contains no provider, lock, storage, network, route, or
  current-pointer implementation.

## Non-claims

This port and memory fake do not prove an external provider, process-level or
distributed atomicity, durable commit, linearizable reads, provider identity,
real holdings, wall-clock freshness, current activation, strategy performance,
profitability, paper authority, or live authority.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. pointer-v2 remains unchanged
and is not reissued.
