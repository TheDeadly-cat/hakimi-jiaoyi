# ADR0408: Authenticated latest-head read effective budget v9

Date: 2026-08-24

Status: Accepted as an unmounted synthetic contract

## Context

ADR0407 binds snapshot head and clock counter to an exact signed previous-plus-one commit receipt. v8 still accepts whichever valid receipt the caller supplies. A pure synthetic chain created valid commit 101 and then valid commit 102. Both passed v8 independently, and commit 101 continued to pass after commit 102 existed. v8 correctly reported atomic persistence as false, but it had no authenticated latest-read or rollback-floor input.

A signed latest-read can bind a query, clock evidence, observed receipt, state hash, and monotonic floor. It cannot by itself prove that the signer is a genuine store, that the reply is globally latest, or that storage is durable. Those remain separate source-truth and runtime claims.

## Decision

Add an unmounted v9 successor with four strict latest-read documents:

1. `strategy-correlation-authenticated-latest-head-checkpoint-v1` commits a monotonic rollback floor for commit index, clock counter, state revision, accepted state hash, and accepted commit-evidence hash.
2. `strategy-correlation-authenticated-latest-head-read-claim-v1` binds query ID, signed clock evidence and time, observed state/receipt, and the previous checkpoint. It derives a candidate next checkpoint.
3. `strategy-correlation-authenticated-latest-head-signed-read-v1` carries the exact atomic-store Ed25519 key and signature candidate.
4. `strategy-correlation-authenticated-latest-head-read-signature-evidence-v1` verifies the preregistered store key while redacting raw key and signature material.

`strategy-correlation-cluster-effective-bet-budget-v9` verifies the signed read, binds its observation and query clock to v8, requires the next checkpoint to be exact, rebuilds v8, and keeps public admission blocked.

## Invariants

- Checkpoint, read claim, signed read, read evidence, and v9 output are strict canonical documents.
- Commit index cannot fall below the checkpoint floor.
- Clock-counter and state-revision deltas must equal the commit-index delta.
- A same-index read must match both accepted state and commit-evidence hashes exactly.
- An advanced read must advance both state and commit-evidence hashes.
- Query clock evidence and evaluation timestamp must equal the clock evidence consumed by v8.
- Observed receipt hash, atomic state hash, commit index, counter, and revision must equal v8.
- A new checkpoint rejects an old signed read built against an earlier checkpoint.
- Local read signature and rollback arithmetic do not set provider identity, globally latest, persistence, durability, or crash-recovery facts.
- v8 and v9 public `admission_status` remain `BLOCKED` even when local contract status is `PASS`.
- Outputs redact raw keys, signatures, and positions.
- No filesystem, database, cache, log, network, market, account, runtime, scheduler, read service, CAS operation, or writer is accessed.
- All current, migration, writer, paper, and live authority remains false.

## Consumer-first activation order

1. Keep checkpoint, read, evidence, and v9 unmounted and without a `current` alias.
2. Validate only with pure synthetic receipt chains and keys.
3. Define who owns and persists the checkpoint hash; caller-selected old checkpoints cannot establish latestness.
4. Implement authenticated latest-head reads in an isolated adapter with replay nonce, epoch, durability, and rollback recovery policy.
5. Independently attest store provider identity and implementation before setting source-truth or latestness facts.
6. Define multi-process and disaster-recovery behavior before any runtime observation.
7. Add neutral report-schema consumers before current activation consideration.
8. Require explicit authorization for later runtime activation. No activation can grant paper or live authority.

## Adversarial matrix

- Valid commit 101 remains selectable after valid commit 102 exists: demonstrates the inherited gap.
- Exact signed read over commit 101 and floor 100: local v9 pass with public admission blocked.
- Checkpoint advanced through commit 102, then old read replayed: blocks.
- Commit below floor, same-index equivocation, counter-delta mismatch, or revision-delta mismatch: rejected.
- Read observation or query clock drift: blocks.
- Wrong store signing key, stale clock, provider drift, boolean aliases, or resealed promotion: fails closed.
- Outputs are deterministic, input-immutable, and redacted.
- Production source contains no private key, read I/O, network, or runtime access.

## Consequences and non-claims

v9 adds an authenticated monotonic read contract and explicit rollback floor. It does not prove the checkpoint supplied by the caller is the newest checkpoint, that a real store answered the query, that the answer is globally latest, that storage is durable, or that crash recovery is correct. It also does not prove clock, snapshot, or broker source truth, execution, profitability, runtime integration, migration safety, writer authorization, paper authorization, or live authorization.

The natural-forward public chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 is not reissued.
