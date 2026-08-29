# ADR 0103: Provider identity assertion replay receipt verifier v1

## Status

Accepted as an inactive research-only candidate. It is not connected to
`current`, ADR 0100 facts, admission, paper, or live paths.

## Context

ADR 0102 preregisters the consumer boundary for an external append-only replay
registry. Registration alone cannot establish that an assertion was logged or
that a checkpoint extends a previously pinned view.

## Decision

Add a verifier that consumes the exact ADR 0102 registration and sealed
registration receipt, a strict raw Ed25519 public key, a signed checkpoint, an
assertion inclusion proof, and a consistency proof from a caller-supplied pinned
checkpoint.

Leaf hashes bind the raw 32-byte assertion receipt digest to the preregistered
leaf domain. Internal nodes bind ordered child hashes to the preregistered node
domain. Checkpoint signatures bind strict canonical JSON to the preregistered
checkpoint domain. Inclusion and consistency use binary Merkle tree semantics
for arbitrary positive tree sizes, including non-power-of-two trees.

The public key must hash to the separately registered replay-registry trust-root
key hash. Provider receipt, identity-registry, and replay-registry key roles
remain separate.

The highest state is
`REPLAY_CHECKPOINT_SIGNATURE_INCLUSION_AND_CONSISTENCY_VERIFIED_EXTERNAL_TRUST_UNPROVEN`.
It proves only local cryptographic checks against supplied candidate inputs.
It does not prove that the replay registry is externally authoritative, that
checkpoint time is true, or that the assertion is unique or absent elsewhere.

The static fingerprint is
`20260927-cross-lag-factor-calibration-long-horizon-provider-identity-assertion-replay-receipt-verifier-1`.

## Fail-closed boundary

Malformed shape, extra fields, non-native integers, noncanonical encodings,
wrong key roles, signature failure, wrong or extra inclusion/consistency nodes,
rollback, genesis drift, split-view roots, and bool/int output aliases fail to
`UNKNOWN`.

All authority fields remain false, including replay-registry checked, replay
absence, assertion uniqueness, provider identity, admission, selection, paper,
and live authority.

## Activation order

1. Validate this verifier with synthetic adversarial fixtures.
2. Specify uniqueness and freshness semantics separately; inclusion is not a
   no-replay proof.
3. Implement a producer only after verifier and split-view defenses are stable.
4. Establish independent external registry trust, checkpoint time, and durable
   prior-checkpoint persistence.
5. Wire ADR 0100 and presentation/current only under a later decision.

## Consequences

This closes the local signature, inclusion, and append-only consistency
verification slice. It does not establish profitability or trading permission.

## Validation

- Targeted synthetic contract tests: 26/26.
- Independent nine-leaf adversarial matrix: 18/18.
- Factor-calibration family: 712/712.
- In-memory compile: 2/2.
- Lean list/dry-run: planned 19, executed 0, runtime mutations false.
- Active integration references: 0.

These checks validate only the candidate implementation and fail-closed contract.
They do not establish external registry trust, time, uniqueness, replay absence,
profitability, or trading authorization.