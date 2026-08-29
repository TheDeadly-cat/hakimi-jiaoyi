# ADR0122: Strategy correlation provider dataset-key lifecycle replay gate v1

Status: Accepted as an inactive research-only candidate on 2026-08-22.

## Context

ADR0121 verifies a signed lifecycle claim at an explicit reference time, but it intentionally leaves `lifecycle_receipt_replay_registry_checked=false`. A pure synthetic call reused the exact same lifecycle governance receipt at two valid reference times; both evaluations passed, while the lifecycle receipt hash remained identical and the public API had no registry, checkpoint, inclusion, consistency, or occurrence-audit input.

Historical signature validity and lifecycle freshness therefore do not establish that the receipt was registered once, that a checkpoint is append-only, or that an index scan observed exactly one occurrence.

## Decision

Add four detached, versioned consumer contracts:

- `strategy-correlation-provider-dataset-key-lifecycle-replay-registration-v1`
- `strategy-correlation-provider-dataset-key-lifecycle-replay-pinned-checkpoint-v1`
- `strategy-correlation-provider-dataset-key-lifecycle-replay-checkpoint-v1`
- `strategy-correlation-provider-dataset-key-lifecycle-replay-occurrence-audit-v1`
- `strategy-correlation-provider-dataset-key-lifecycle-replay-gate-v1`

The registration reverifies ADR0121 and binds the source lifecycle verification and receipt hashes, replay registry identity/namespace, adapter implementation hash, strict Merkle domains, genesis root, freshness windows, and two new Ed25519 roles. The replay-registry checkpoint key and occurrence-auditor key must be distinct from each other and from the dataset-content, identity-registry, timestamp-adapter, and lifecycle-governance keys.

The gate requires an expected pinned prior checkpoint, a signed successor checkpoint, a real domain-separated Merkle inclusion proof for the lifecycle receipt, and a real append-only consistency proof from the pinned checkpoint. It separately verifies an occurrence auditor signature over the checkpoint, both proof hashes, a complete `[0, tree_size)` scan claim, one occurrence at the verified leaf index, index snapshot commitment, and explicit checkpoint/scan/reference times.

The production service accepts no private key, runtime store, database, cache, network source, or secret. It does not emit raw public keys, signatures, proofs, or index contents.

## Claim calibration

The strongest state is `SIGNED_APPEND_ONLY_CHECKPOINT_INCLUSION_AND_EXACTLY_ONE_OCCURRENCE_CLAIM_VERIFIED_EXTERNAL_REGISTRY_TRUST_UNPROVEN`.

Actual cryptographic verification proves checkpoint signature, receipt inclusion, consistency from the supplied pin, and the auditor signature. The full-scan and exactly-one properties remain signed claims. External registry authority, auditor authority, durable publication, index completeness, global uniqueness, split-view absence, and future replay absence remain false or unproven.

## Consumer-first activation order

1. Keep ADR0122 detached from current reports and all active entrypoints.
2. Exercise non-genesis inclusion/consistency plus malformed, forked, rollback, duplicate, incomplete-scan, stale, collision, signature, and expected-pin cases.
3. Specify durable external checkpoint publication and independent observer consistency under a separate contract.
4. Accumulate multiple checkpoints before claiming longitudinal coverage.
5. Add a new report schema that maps missing or invalid replay evidence to UNKNOWN.
6. Add neutral SOURCE -> GAP -> MATURITY -> PERMISSION presentation only after the report contract is stable.
7. Require a separate migration decision for current; never auto-reissue pointer-v2.

## Validation evidence

- Synthetic gap proof: one lifecycle receipt passes ADR0121 at two reference times while registry-checked remains false and replay inputs are absent.
- Targeted ADR0122 contracts: 28/28 PASS.
- In-memory compile: 2/2 PASS.
- Independent public-API adversarial matrix: 20/20 PASS.
- Direct ADR0119/ADR0120/ADR0121/ADR0122 family: 95/95 PASS across four TestCase classes.
- Research lean: 15 listed/planned, 0 executed/completed/reused; ADR0122 TestCase and service source occur once; runtime mutation, paper, and live are false.
- Eight explicit active entrypoints contain zero ADR0122 references.
- Static fingerprint: `20260822-strategy-correlation-provider-dataset-key-lifecycle-replay-gate-1`.

## Compatibility and remaining boundary

ADR0122 changes no report, writer, server, engine, CLI, UI, paper, live, or pointer behavior. The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`; legacy pack-v5 public reads remain UNKNOWN; pointer-v2 fields, hashes, and no-auto-reissue behavior remain unchanged.

Durable public checkpoint availability, independent consistency observers, complete-history coverage, rotation-chain continuity, authoritative time, global uniqueness, future replay absence, profitability, and every trading authority remain separate gaps.
