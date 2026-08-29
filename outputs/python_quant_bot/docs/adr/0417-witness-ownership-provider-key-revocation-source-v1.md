# ADR0417: Witness ownership provider key revocation authority source v1

## Status

Accepted as an unmounted, synthetic, research-only revocation-source candidate. It does not publish or persist a revocation, update an active key, call an authority or provider, activate current/runtime, or authorize paper, live, writer, migration, or trading.

## Context

ADR0416 requires a `revocation_snapshot_hash` in the dual-signed key-rotation claim, but that hash is caller supplied. Old/new key signatures bind the hash; they do not prove that an independent revocation authority issued, published, or persisted the referenced snapshot.

## Decision

Add an exact revocation authority set containing three structurally distinct authority profiles and a 2-of-3 signature policy. Authority IDs, keys, and organization-claim hashes must be unique, and authority keys must differ from the provider key. These structural differences do not prove authority identity or independence.

Add a revocation snapshot generated before the ADR0416 rotation claim. It binds provider, old/new key hashes, previous/next epochs, rotation nonce, policy, monotonic revocation sequence, predecessor snapshot, and reason code. It deliberately excludes the rotation claim/event hash to avoid a hash cycle. ADR0416 then binds the resulting snapshot hash.

Add domain-separated authority statements and an evaluator that exactly rebuilds the authority set, snapshot, ADR0416 dual-signed rotation evidence, and field-level snapshot-to-rotation binding before accepting a local 2-of-3 signature quorum.

A valid local quorum may set `local_revocation_authority_signature_quorum_verified=true` and `revocation_snapshot_bound_to_rotation=true`. It must keep authority organization identity, authority key continuity, independence source truth, snapshot source/publication/persistence, trusted revocation clock, provider key-control continuity, and external conformance false. Admission remains `BLOCKED`.

## Adversarial matrix

- ADR0416 dual signature passes while revocation source remains false.
- duplicate authority ID/key/organization or provider-key reuse: authority set rejected.
- boolean/nonmonotonic sequence, invalid predecessor, epoch gap, same key, or wrong epoch-zero old key: snapshot rejected.
- wrong authority key: signed statement rejected.
- invalid signature, duplicate authority, or one statement: quorum blocked.
- snapshot hash or field binding differs from ADR0416 rotation: blocked.
- statement order changes do not alter evidence.
- resealed permission promotion: exact rebuild verifier rejects it.
- valid local 2-of-3 signatures: candidate passes while all external source-truth and authority fields remain blocked.

## Consequences and limits

ADR0417 removes the unconstrained caller-hash ambiguity from the local controlled-rotation evidence chain. It does not establish real authority identities, independent organizations, key continuity, revocation publication, trusted time, persistence, provider update, external conformance, profitability, execution, or trading authority.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and not reissued.
