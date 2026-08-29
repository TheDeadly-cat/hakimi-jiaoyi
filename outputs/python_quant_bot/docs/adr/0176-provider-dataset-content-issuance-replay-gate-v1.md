# ADR0176: Provider dataset content issuance replay gate v1

Status: Accepted as an inactive research-only candidate on 2026-08-22.

## Context

ADR0120 verifies a provider dataset-content signature. ADR0121 verifies signed
dataset-key lifecycle claims, and ADR0122 verifies one occurrence of the
lifecycle receipt in a supplied append-only registry view. None of those
contracts registers the dataset-content attestation itself.

A pure synthetic, read-only call evaluated one valid ADR0120 attestation twice
with the same source context. Both results were byte-for-byte equal, reused the
same attestation hash, exposed no issuance, sequence, occurrence, checkpoint, or
nonce field, and kept current admission and writer activation false. ADR0122
cannot close that gap because its Merkle leaf accepts only the lifecycle receipt
hash.

## Decision

Add a detached content-issuance replay layer with five v1 contracts:

- strategy-correlation-provider-dataset-content-issuance-replay-registration-v1
- strategy-correlation-provider-dataset-content-issuance-replay-pinned-checkpoint-v1
- strategy-correlation-provider-dataset-content-issuance-replay-checkpoint-v1
- strategy-correlation-provider-dataset-content-issuance-replay-occurrence-audit-v1
- strategy-correlation-provider-dataset-content-issuance-replay-gate-v1

The registration reverifies the exact ADR0120 attestation and ADR0122 lifecycle
replay result. It reuses ADR0122's already separated replay-registry and
occurrence-auditor key roles instead of inventing another signing hierarchy.
Content evidence uses a distinct registry namespace, leaf domain, node domain,
checkpoint signature domain, occurrence signature domain, and genesis root.

The immutable content identity is the pair of attestation hash and future
evaluation ID hash. No caller-selected nonce or issuance ID participates in the
leaf, so a duplicate occurrence cannot evade equality by changing an unrelated
identifier.

The gate requires:

- exact expected hashes for registration, pinned checkpoint, successor
  checkpoint, and occurrence audit;
- a signed successor checkpoint and real non-genesis Merkle inclusion proof;
- a real append-only consistency proof from the supplied pinned checkpoint;
- a separately signed complete [0, tree_size) scan claim;
- exactly one occurrence at the inclusion-proven leaf index;
- an index snapshot root equal to the signed checkpoint root;
- evidence times ordered after the ADR0122 occurrence audit;
- freshness limits no weaker than ADR0122;
- no private key, store, database, cache, network, runtime, or secret input.

## Claim calibration

The strongest state is
SIGNED_CONTENT_ISSUANCE_CHECKPOINT_INCLUSION_AND_EXACTLY_ONE_OCCURRENCE_CLAIM_VERIFIED_EXTERNAL_REGISTRY_TRUST_UNPROVEN.

Local cryptography proves the supplied checkpoint signature, Merkle inclusion,
append-only consistency from the supplied pin, and occurrence-auditor
signature. Complete-scan and exactly-one properties remain signed claims.
External registry authority, external auditor authority, provider issuance
truth, durable publication, global uniqueness, split-view absence, runtime
consumption enforcement, and future replay absence remain false or unproven.

## Consumer-first activation order

1. Keep ADR0176 detached from reports, writers, server, engine, CLI, UI, paper,
   live, and current pointers.
2. Exercise positive, duplicate, incomplete-scan, root-split, inclusion,
   consistency, stale, signature, expected-pin, time, authority, and redaction
   cases with pure synthetic fixtures.
3. Bind ADR0176 into a new immutable shadow-consumer preregistration successor;
   do not modify ADR0169 or ADR0175 in place.
4. Specify durable external checkpoint publication and independent consistency
   observers before treating the local signed claim as external issuance truth.
5. Add runtime consumption-idempotency enforcement under a separate versioned
   service-input contract.
6. Add a report consumer that maps missing or invalid issuance evidence to
   UNKNOWN.
7. Add neutral SOURCE -> GAP -> MATURITY -> PERMISSION presentation only after
   the report contract is stable.
8. Require an explicit migration decision for current and never auto-reissue
   pointer-v2.

## Adversarial matrix

The v1 matrix covers the preexisting double-evaluation gap, source-verifier
bypass, source lineage, namespace separation, inherited freshness ceilings,
time ordering, expected hashes, non-genesis inclusion and consistency tamper,
wrong checkpoint and auditor keys, signed duplicate claims, signed incomplete
scans, detached index roots, stale checkpoints, stale scans, delayed audits,
reference-time drift, authority injection, bool-as-int aliases, deterministic
content identity, output redaction, coherent output resealing, and production
API private-key exclusion.

## Compatibility

ADR0176 changes no report, writer, server, engine, CLI, UI, paper, live, or
pointer behavior. The natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
Legacy pack-v5 public reads remain UNKNOWN. pointer-v2 fields and hash contract
remain unchanged, and no pointer is automatically reissued.

## Validation acceptance

Acceptance requires the targeted ADR0176 class, the ADR0120 through ADR0122
dependency family, a separately orchestrated public-API adversarial matrix, and
in-memory compilation to pass. These checks remain research-only engineering
evidence and cannot establish external provider truth, profitability, paper
authority, or live authority.
