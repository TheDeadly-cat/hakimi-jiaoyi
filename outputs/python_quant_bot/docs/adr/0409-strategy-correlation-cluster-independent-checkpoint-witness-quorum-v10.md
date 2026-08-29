# ADR0409: Independent checkpoint witness quorum effective budget v10

Date: 2026-08-24

Status: Accepted as an unmounted synthetic contract

## Context

ADR0408 adds a signed latest-head read and rollback checkpoint. The checkpoint itself remains caller-selected. A pure synthetic proof advanced the valid checkpoint floor to commit 102, then continued to supply checkpoint 100 and its old read for commit 101. v9 still returned local `PASS`, while correctly reporting latest-head source truth as false.

A single store signature and a caller-selected checkpoint therefore remain one correlated control surface. The minimum independent boundary is a preregistered quorum of witnesses from distinct trust and failure domains, all signing the exact same latest-read subject. Such a quorum reduces single-key and single-domain control but does not prove witness identity, actual independence, or global latestness.

## Decision

Add an unmounted v10 successor with four strict witness documents:

1. `strategy-correlation-checkpoint-witness-set-preregistration-v1` fixes exactly three witnesses, a two-signature quorum, unique witness/key IDs, and unique trust/failure domains.
2. `strategy-correlation-checkpoint-witness-quorum-claim-v1` binds witness round, time, previous and next checkpoint, latest-read evidence, atomic receipt/state, clock evidence, account scope, commit index, counter, and revision.
3. `strategy-correlation-checkpoint-signed-witness-quorum-v1` carries one to three sorted, unique Ed25519 signature rows.
4. `strategy-correlation-checkpoint-witness-quorum-signature-evidence-v1` verifies every supplied signature and requires at least two valid witnesses while redacting raw keys and signatures.

`strategy-correlation-cluster-effective-bet-budget-v10` requires the exact quorum evidence, binds it to v9 and the atomic-store scope, verifies distinct preregistered domains, rebuilds v9, and preserves public admission as blocked.

## Invariants

- The witness set contains exactly three rows sorted by witness ID.
- Witness ID, key ID, SPKI hash, trust domain, and failure domain are all unique.
- Minimum quorum is exactly two; duplicate signature witnesses are rejected.
- Every supplied signature must be valid. Invalid signatures cannot be ignored to manufacture quorum.
- Every witness signs the same strict canonical claim hash.
- Witness round equals the observed commit index.
- Quorum subject exactly matches v9 checkpoints, latest-read evidence, atomic receipt/state, clock evidence, account scope, commit index, counter, revision, and time.
- Two or three valid signatures may pass locally; one signature blocks.
- Preregistered domain distinctness does not set real witness-independence truth.
- v9 and v10 public `admission_status` remain `BLOCKED` even when local contract status is `PASS`.
- Outputs redact raw witness keys, signatures, and snapshot positions.
- No filesystem, network, witness service, database, cache, log, market, account, runtime, scheduler, read, CAS, or writer is accessed.
- All current, migration, writer, paper, and live authority remains false.

## Consumer-first activation order

1. Keep witness set, claim, evidence, and v10 unmounted and without a `current` alias.
2. Validate only with pure synthetic keys and checkpoint chains.
3. Independently verify witness legal/operational identity, implementation, key custody, trust domain, and failure domain.
4. Define witness sequence persistence and anti-replay ownership outside caller-controlled inputs.
5. Define quorum disagreement, equivocation, outage, replacement, and key-rotation policy.
6. Implement authenticated witness transport only in an isolated adapter after source contracts are reviewed.
7. Add neutral report-schema consumers before current activation consideration.
8. Require explicit authorization for later runtime activation. No activation can grant paper or live authority.

## Adversarial matrix

- Checkpoint 102 exists while caller continues checkpoint 100/read 101: demonstrates the inherited gap.
- Exact two-of-three signatures over one subject: local v10 pass with public admission blocked.
- Three-of-three signatures: local pass.
- One signature, duplicate witness, duplicate trust/failure domain, wrong key, or invalid quorum: blocks or is rejected.
- Checkpoint, read, atomic state, clock, account scope, round, or time drift: blocks.
- Boolean aliases and resealed promotions under stale expected hashes: fail closed.
- Outputs are deterministic, input-immutable, and redacted.
- Production source contains no private key, witness I/O, network, or runtime access.

## Consequences and non-claims

v10 replaces a single checkpoint/store assertion with an exact cross-domain two-of-three signature contract. It does not prove the witnesses are genuine or independent, that they persist anti-replay state, or that the witnessed checkpoint is globally latest. It also does not prove real CAS, durability, clock/snapshot/broker source truth, execution, profitability, runtime integration, migration safety, writer authorization, paper authorization, or live authorization.

The natural-forward public chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 is not reissued.
