# ADR0276: Membership Source-Baseline Nonce Atomic Reserve Protocol v1

## Status

Accepted as an unmounted, synthetic, research-only protocol contract.

## Context

ADR0275 can block a replay visible in a supplied snapshot. It correctly keeps a
snapshot absence at `UNKNOWN`, because a read followed by a separate write has a
time-of-check/time-of-use race and a caller-supplied snapshot proves neither
durability nor linearizable serialization.

The current call-chain gap proof ran two independent checks against the same
empty snapshot. Both returned `UNKNOWN`; neither produced a durable reserve
receipt or mutated runtime state. The project therefore needs explicit reserve
state-transition semantics before any storage provider can be considered.

## Decision

Add a pure compare-and-swap protocol with five bounded document types:

- immutable synthetic registry state;
- reserve request bound to replay-key, expected-head, and request-nonce hashes;
- deterministic transition receipt;
- local Ed25519 registry-key registration;
- signed transition receipt and redacted verification evidence.

The transition checks duplicate membership before expected-head freshness:

- existing replay key: `ALREADY_RESERVED`, `gate_status=BLOCK`;
- absent key with stale expected head: `COMPARE_AND_SWAP_CONFLICT`,
  `gate_status=UNKNOWN`;
- absent key with matching head: `RESERVED_IN_RETURNED_STATE`,
  `gate_status=UNKNOWN`.

The successful synthetic transition returns a new immutable state with sequence
incremented by one and a previous-head commitment. It never mutates its input.
Two calls against the same old state can still return the same candidate state;
therefore the protocol explicitly sets `atomic_storage_commit_verified=false`.

The signed receipt uses Ed25519 over the raw bytes of the transition receipt
SHA-256 digest. Verification proves possession of the locally registered key
only. It does not prove registry identity, key governance, storage authority,
atomic commit, durability, or linearizable reads. Raw public keys and signatures
are omitted from the evidence projection.

`status=PASS` means document validation or signature verification completed.
Only `gate_status` carries blocking/progression semantics, and this version has
no `gate_status=PASS` path.

## Consumer-first activation order

1. Keep the pure protocol and verifier unmounted.
2. Add an exact ADR0274-to-ADR0275 replay-key adapter.
3. Define a registry provider port with atomic compare-and-swap/reserve behavior.
4. Require independently authenticated authority registration and key rotation.
5. Require durable commit and linearizable read evidence from the provider.
6. Add a later receipt version that can distinguish authenticated durable
   commit from a signed synthetic claim.
7. Review HTTP registration and neutral UI projection separately.

## Adversarial matrix

- exact sequential replay: `BLOCK`;
- stale expected registry head: `UNKNOWN` conflict;
- two calls from the same old state: equal synthetic outputs, no storage claim;
- tampered state or replay-key commitment: rejection;
- wrong registry public key: signature rejection;
- tampered signature: signature rejection;
- resealed durability promotion: `UNKNOWN`;
- signed synthetic reserve: signature valid, progression still `UNKNOWN`;
- signed duplicate reserve: `BLOCK`;
- raw public key or signature in public evidence: forbidden.

## Non-claims

This protocol does not read or write a database, cache, file, service, browser,
or scheduler. It does not prove durable persistence, atomic storage execution,
linearizable concurrency, registry identity, key governance, reviewer identity
or independence, HTTP/UI/current activation, paper/live authority, market
validity, strategy performance, or profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
