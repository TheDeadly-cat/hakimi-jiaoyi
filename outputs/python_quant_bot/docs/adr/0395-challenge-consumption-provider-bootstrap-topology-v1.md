# ADR 0395: Challenge-consumption provider bootstrap topology v1

## Status

Accepted as an isolated, pure synthetic non-circular topology and unexecuted genesis-admission plan. It does not register a provider, consume a challenge, or grant runtime or trading authority.

## Context

ADR0394 binds signed clock observations to the exact ADR0393 dual-signature handoff but correctly keeps current time, freshness, and replay consumption false. Using the ADR0391 candidate provider to consume its own registration challenge would be circular self-authorization.

The adjacent ADR0276 nonce reserve protocol cannot serve as a bootstrap root. It explicitly proves only a synthetic state transition and local key possession, while durability, linearizability, authority identity, governance, and storage authentication remain false.

A pure synthetic gap probe of ADR0391 confirmed that its preregistration contains no bootstrap-root topology, candidate-key exclusion, or declared trust-domain separation.

## Decision

Freeze an offline threshold genesis-admission topology with these structural requirements:

1. Two to seven root authorities, each with exact identifier, DER-SPKI hash, trust-domain claim, and governance-implementation claim.
2. Unique root identifiers, key hashes, and trust domains.
3. A threshold of at least two signatures and a strict majority of root members.
4. Candidate provider key, operator claim, and trust domain excluded from every root member.
5. Exact binding to ADR0391 preregistration and the ADR0394 clock-binding implementation.
6. A separate genesis-admission namespace and future threshold claim/receipt schemas.
7. Twelve frozen external cases, all with executed false and observed null.

Structural separation prevents obvious self-reference but does not verify real-world root identity, key possession, governance, organizational independence, threshold signatures, replay storage, genesis creation, provider conformance, or registration.

Production code accepts only identifiers and hashes. It contains no raw public keys, signatures, private keys, provider calls, file or clock reads, network, storage, runtime assets, services, browsers, or schedulers.

## Consumer-first activation order

1. Keep ADR0395 isolated and preserve all current consumers.
2. Independently authenticate each root identity, key lifecycle, governance implementation, and organizational independence.
3. Add an exact threshold-signed genesis-admission claim and replay key.
4. Prove atomic, durable, linearizable one-time genesis creation with an independent observer.
5. Complete all ADR0391 provider conformance cases and signed receipt checks.
6. Rotate normal challenge consumption away from genesis governance.
7. Consider a versioned current consumer only under separate authorization.

## Adversarial matrix

Tests cover candidate key/operator/trust-domain self-reference, duplicate root identity/key/domain, non-integer and weak thresholds, root-count bounds, canonical authority ordering, preregistration drift, re-sealed governance promotion, topology mutation, unexecuted plan integrity, root-key drift, material redaction, input immutability, and forbidden production capabilities.

## Consequences

ADR0395 closes the topology-level circularity gap only. No external root, threshold signature, current time, freshness, consume-once, provider conformance, profitability evidence, or trading permission is created. The natural-forward chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 fields and hashes, and neutral SOURCE -> GAP -> MATURITY -> PERMISSION UI remain unchanged.
