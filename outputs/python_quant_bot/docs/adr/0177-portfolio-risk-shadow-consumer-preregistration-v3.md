# ADR0177: Portfolio-risk shadow consumer preregistration v3

Status: Accepted as an inactive research-only preregistration on 2026-08-22.

## Context

ADR0175 immutably preregisters a successor shadow consumer after pinning the
local matrix derivation, native cutoff manifest, and completed-session
freshness policy. It remains BLOCKED because provider key control, external
data issuance, provider replay evidence, external time, the application
consumer, the versioned risk-service input, independent review, and current
authorization are absent.

ADR0176 now supplies a versioned content-issuance replay contract. It can verify
the signatures and Merkle properties of supplied synthetic evidence, but no
concrete ADR0176 registration, checkpoint, proofs, or occurrence audit has been
bound to a shadow call. Its external registry and auditor authority, durable
publication, global uniqueness, runtime consumption enforcement, and future
replay absence also remain unproven.

## Decision

Add immutable preregistration v3 as a successor to v2. v3:

- verifies v2 through the public v2 verifier and pins the exact v2
  preregistration hash;
- pins the ADR0176 implementation, lifecycle dependencies, schema family,
  verification state, log protocol, scan policy, cardinality policy, and
  content identity policy;
- reuses the existing provider identity, dataset attestation, lifecycle,
  registry-key, and occurrence-auditor stacks;
- extends future shadow inputs with the exact ADR0176 source and evidence
  schemas;
- preserves v2's three closed local blockers exactly;
- records ADR0176 under newly pinned local capabilities rather than pretending
  that replay evidence has already been bound;
- retains provider_replay_registry_unchecked and adds explicit external,
  durable-publication, runtime-consumption, and future-replay blockers;
- remains BLOCKED and grants no operational authority.

## Why the fourth blocker is not closed

An implementation source hash and schema pin prove contract identity, not a
registry fact. Closing provider_replay_registry_unchecked would require an
exact ADR0176 verification document plus its registration, pinned checkpoint,
successor checkpoint, inclusion proof, consistency proof, occurrence audit,
expected hashes, and reference time. External trust would still remain
separate after those local inputs passed.

## Consumer-first activation order

1. Bind authenticated provider identity, key control, and data issuance.
2. Supply and reverify the exact ADR0176 registration, checkpoints, proofs, and
   occurrence audit for one future shadow evaluation identity.
3. Verify external registry and auditor authority plus durable checkpoint
   publication.
4. Authenticate the external time authority used by freshness evaluation.
5. Implement an isolated application shadow consumer v3 with no legacy route
   replacement.
6. Conduct an independently authorized synthetic shadow review.
7. Version the risk-service input contract.
8. Consider current only through a separate explicit authorization; never
   auto-reissue pointer-v2.

## Adversarial matrix

The v3 matrix covers source implementation drift, manifest missing/extra/type
aliases, v2 context drift, mandatory v2 public verification, immutable v2
blocker inheritance, exact three-item local closure, ADR0176 contract versus
evidence separation, schema and policy pins, versioned input uniqueness, UI
exclusion, activation order, external and runtime false facts, authority locks,
provider-stack reuse, input immutability, deterministic rebuild, coherent
resealing, v2 tamper, and production API exclusion of private/runtime assets.

## Compatibility

ADR0177 changes no v1 or v2 document, report, writer, server, engine, CLI, UI,
paper, live, or pointer behavior. The natural-forward chain remains
audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2. Legacy pack-v5 public reads remain UNKNOWN.
pointer-v2 fields and hash contract remain unchanged, and no pointer is
automatically reissued.

## Claim calibration

Passing tests establish only deterministic local contract behavior. ADR0177
does not prove provider data truth, external key custody, external registry
completeness, time authority, robustness, profitability, paper authorization,
live authorization, or current admission.
