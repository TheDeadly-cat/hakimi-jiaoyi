# ADR0413: Witness ownership provider preregistration and signed receipt v1

## Status

Accepted as an unmounted, synthetic, research-only evidence contract. It does not activate a provider, current, runtime, paper, live, writer, migration, or trading authority.

## Context

ADR0412 defines one atomic `compare-consume-and-advance` provider operation and an exact consumer, but its structural provider result and receipt claim can be constructed by any local caller. ADR0412 therefore correctly leaves provider receipt signature, identity, persistence, durability, linearizability, rollback resistance, and external conformance false.

Existing replay-cursor registration code observes a local signature candidate, while the signer source-trust boundary explicitly states that local signature success is not organization identity or external trust. The existing registration code also predates the shared strict Ed25519 public parser. ADR0413 must not copy that parser or reinterpret a local signature as provider source truth.

## Decision

Add two unmounted contracts:

- a provider profile preregistration that fixes registry ID, operator-claim hash, trust domain, Ed25519 SPKI hash, provider implementation claim, ADR0412 port and consumer fingerprints, receipt schemas, and signature format;
- a domain-separated signed operation receipt whose message binds the preregistration hash, exact ADR0412 consumer evaluation, command, consumption key, structural receipt claim, registry ID, returned revision, and returned ownership-state hash.

The signed receipt implementation reuses `strict_ed25519_public_contract_v1`. Production code contains no private key, custom base64 decoder, custom SPKI parser, storage, network, runtime, or provider adapter.

A valid evaluation may set `provider_key_possession_observed=true` and `provider_receipt_signature_verified=true`. It must keep organization identity, key continuity, provider implementation, external conformance, atomic-operation source truth, persistence, durability, linearizable read-after-write, and rollback resistance false. Public admission remains `BLOCKED`.

## Consumer-first activation order

1. ADR0412 exact unmounted consumer.
2. ADR0413 provider profile preregistration.
3. ADR0413 domain-separated signed receipt evidence.
4. Independent organization identity, key continuity, implementation provenance, and provider conformance evidence.
5. Authorized external adapter and real atomic/durable/linearizable/rollback tests.
6. Separately reviewed and authorized current transition.

This ADR completes steps 2 and 3 only.

## Adversarial matrix

- ADR0412 exact result exists without any signature: persistence remains unverified.
- preregistered key hash drift: blocked.
- wrong key with a cryptographically valid signature: blocked.
- modified signature: blocked.
- signature over the raw receipt hash instead of the domain-separated message: blocked.
- noncanonical SPKI or signature base64: rejected.
- command/preregistration mismatch: rejected.
- resealed ADR0412 permission promotion: rejected.
- tampered structural receipt claim: rejected.
- resealed ADR0413 permission promotion: exact rebuild verifier rejects it.
- valid preregistered-key signature: local evidence passes while admission and every external source-truth authority remain blocked.

## Consequences and limits

ADR0413 closes local unsigned-receipt substitution and cross-domain signature replay gaps. It does not prove who controls the key over time, who operates the provider, which implementation ran, whether any external state changed, or whether atomicity, durability, linearizability, rollback resistance, independence, profitability, execution, paper, live, or trading authority exists.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and not reissued.
