# ADR0478: Replay cursor provider preregistered-key signed receipt v1

## Status

Accepted as an unmounted, synthetic, research-only contract. It does not activate a provider, mutate a replay cursor, or grant current, runtime, paper, live, writer, execution, profitability, or trading authority.

## Context

The replay-cursor provider port defines an immutable compare-and-advance command and a structural result. The preregistration contract names `incumbent-snapshot-replay-cursor-provider-signed-receipt-v1` as its target receipt schema, but no implementation previously consumed that target. A local caller could therefore construct an unsigned `ADVANCED` result with arbitrary revision and cursor hashes. Existing signed-registration evidence proves only local possession of a preregistered key for the registration message; provider identity, registration, implementation, challenge consumption, external invocation, durability, and linearizability remain unverified.

## Decision

Add one unmounted provider receipt contract with three exact documents:

- a receipt claim that first verifies the existing signed-registration evidence and binds the preregistration, registration claim, signed registration, command, result, registry identity, outcome, revision, and replay-cursor transition;
- a signed receipt using the preregistered Ed25519 key over the raw SHA-256 bytes of the domain-separated receipt claim;
- deterministic verification evidence that may observe local key possession while keeping every external source-truth and permission fact false.

Every command and result dataclass field is projected into a strict canonical snapshot. Optional structural provider receipt content is bounded, hashed, and never copied into the claim or public evidence. `ADVANCED` must observe the command base cursor and return its proposed cursor. Rejected outcomes must return the observed cursor unchanged. The implementation reuses the shared strict Ed25519 parser and contains no private key, provider adapter, I/O, network, runtime, database, cache, log, or environment access.

## Consumer-first activation order

1. Existing exact replay-cursor intent, command, and structural result contracts.
2. Existing provider preregistration and signed-registration verification evidence.
3. ADR0478 exact command/result receipt claim.
4. ADR0478 preregistered-key signed receipt and exact evidence verifier.
5. Independent provider identity, implementation provenance, challenge consumption, conformance, durability, linearizability, rollback, and consume-once evidence.
6. Separately reviewed and explicitly authorized current transition.

ADR0478 completes steps 3 and 4 only. It is not mounted into `current`.

## Adversarial matrix

- unsigned caller-constructed `ADVANCED` result: reproduced as the pre-ADR0478 gap;
- command hash or registry identity substitution: rejected;
- incoherent base, observed, proposed, or returned cursor: rejected;
- raw provider receipt payload substitution: changes the bounded content hash and cannot leak through public evidence;
- wrong key with a valid Ed25519 signature: blocked by the preregistered key hash;
- modified, short, or noncanonical signature/key encoding: blocked or rejected;
- signature replay from another claim/domain: blocked;
- changed registration evidence or preregistration: exact upstream verifier rejects it;
- resealed and re-signed permission promotion: exact claim/evidence rebuild rejects it;
- valid preregistered-key receipt: local verification passes while admission and all external authority remain blocked.

## Consequences and limits

ADR0478 closes the local unsigned-result substitution gap at the contract boundary. It does not show that any provider was invoked, that any state was committed, or that the operation was atomic, durable, linearizable, rollback resistant, or consume-once. It does not establish provider identity, implementation, registration, independence, execution, profitability, paper, live, or trading permission.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and is not reissued.
