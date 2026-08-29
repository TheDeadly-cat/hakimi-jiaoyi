# ADR0416: Witness ownership provider key continuity and dual-signed rotation v1

## Status

Accepted as an unmounted, synthetic, research-only key-rotation candidate. It does not update provider preregistration, activate a key, persist state, mount runtime/current, or authorize paper, live, writer, migration, or trading.

## Context

ADR0413 proves that one preregistered provider key signed one domain-separated operation receipt. It correctly leaves provider key-control continuity false. A single possession event cannot authorize a replacement key, prove old-key revocation, establish key epochs, or prevent a caller from substituting a new key profile.

No existing source module defines provider key rotation, revocation, or continuity for this ownership-state chain.

## Decision

Add a versioned key-continuity state containing provider identity binding, monotonic key epoch, active SPKI hash, predecessor state hash, and last rotation-event hash. Genesis epoch zero must exactly match the ADR0413 provider preregistration key.

Add a rotation claim that:

- exactly verifies the previous key state;
- increments key epoch by one;
- requires a different next key;
- binds a rotation nonce, revocation-snapshot hash, preregistered reason code, rotation event, and exact next-state candidate;
- requires old-key and new-key signatures over the same domain-separated message.

A valid evaluation may set local old/new key possession and dual-signature arithmetic facts true. It must keep organization continuity, key-control continuity source truth, revocation source, trusted rotation clock, key-state persistence, provider implementation update, and external conformance false. Admission remains `BLOCKED`.

The implementation reuses the shared strict Ed25519 public parser and contains no private key, custom base64/SPKI parser, storage, network, provider call, runtime, or migration action.

## Adversarial matrix

- ADR0413 signature passes while key continuity remains false.
- genesis active key differs from preregistration: rejected.
- boolean/nonmonotonic epoch, same-key rotation, invalid reason, or malformed hashes: rejected.
- claim drift in nonce, revocation snapshot, old/new key, epoch, event, or next state: rejected.
- wrong old or new public key: signed candidate rejected.
- invalid old signature, invalid new signature, or signatures over another domain: evidence blocked.
- old claim replayed against its next state: rejected.
- resealed permission promotion: exact rebuild verifier rejects it.
- valid dual signature: local candidate passes while all external source-truth and authority fields remain blocked.

## Consequences and limits

ADR0416 closes local unilateral replacement-key substitution for the controlled dual-signature rotation path. It does not cover loss of the old key, independently verify compromise recovery, prove revocation publication, persist the active key epoch, verify organization continuity, update ADR0413/ADR0414 consumers, prove profitability, or authorize any trading capability.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and not reissued.
