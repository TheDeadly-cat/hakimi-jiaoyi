# ADR0411: Witness anti-replay ownership effective budget v11

Date: 2026-08-24

Status: Accepted as an unmounted synthetic contract

## Context

ADR0409 adds a two-of-three checkpoint witness quorum. The witnesses sign an exact checkpoint subject but do not jointly own a sequence state. A pure synthetic chain produced valid commit 102, a valid v9 latest-read, and a valid new witness quorum while the old commit-101 v10 result continued to pass. v10 correctly reported global latestness as false, but it could not prove that participating witnesses had advanced anti-replay state.

An ownership transition can require each participating witness sequence to advance by exactly one and bind a fresh attestation ID to the previous ownership-state hash. It still cannot prove that witnesses durably persist the next state or refuse to sign from an older state.

## Decision

Add an unmounted v11 successor with four strict ownership documents:

1. `strategy-correlation-witness-anti-replay-ownership-state-v1` records one ordered sequence and last-attestation hash for each preregistered witness, plus ownership epoch, revision, predecessor state, and last v10 quorum evidence.
2. `strategy-correlation-witness-anti-replay-ownership-claim-v1` verifies the previous state, increments participating witness sequences by exactly one, leaves nonparticipants unchanged, binds a fresh attestation ID and exact v10 subject, and derives the next ownership state.
3. `strategy-correlation-witness-anti-replay-signed-ownership-quorum-v1` requires signature rows to exactly match the two or three participating witnesses.
4. `strategy-correlation-witness-anti-replay-ownership-quorum-evidence-v1` verifies every ownership-transition signature while redacting raw keys and signatures.

`strategy-correlation-cluster-effective-bet-budget-v11` binds the ownership transition, participants, v10 quorum, checkpoints, and commit index, rebuilds v10, and preserves public admission as blocked.

## Invariants

- Ownership state contains exactly one ordered row for every preregistered witness.
- Sequence and revision fields are strict integers; booleans are rejected.
- Participating witness sequences advance by exactly one and use a fresh attestation ID.
- Nonparticipating witness sequence and last-attestation hash remain unchanged.
- Two or three sorted, unique participants are required.
- Signature rows exactly equal participant IDs; signatures cannot be borrowed from nonparticipants.
- Ownership claim binds previous state, ownership epoch, v10 quorum evidence, checkpoints, and commit index.
- Replaying an old ownership attestation against the derived next state fails exact verification.
- Local sequence arithmetic and signatures do not set persistence, witness identity, real anti-replay ownership, independence, or global latestness facts.
- v10 and v11 public `admission_status` remain `BLOCKED` even when local contract status is `PASS`.
- Shared strict Ed25519 public parsing from ADR0410 is reused.
- No filesystem, network, witness service, database, cache, log, market, account, runtime, scheduler, state write, or writer is accessed.
- All current, migration, writer, paper, and live authority remains false.

## Consumer-first activation order

1. Keep ownership state, claim, evidence, and v11 unmounted and without a `current` alias.
2. Validate only with pure synthetic witness states and keys.
3. Specify durable ownership-state custody for every witness; caller-provided old states cannot establish anti-replay truth.
4. Define witness refusal, concurrent signing, equivocation, outage, replacement, epoch rotation, and recovery policy.
5. Independently attest witness identity, implementation, key custody, and failure-domain independence.
6. Implement authenticated state persistence only in isolated witness adapters after the source contracts are reviewed.
7. Add neutral report-schema consumers before current activation consideration.
8. Require explicit authorization for later runtime activation. No activation can grant paper or live authority.

## Adversarial matrix

- New commit/read/quorum exists while old v10 remains selectable: demonstrates the inherited gap.
- Exact two-witness sequence transition and signatures: local v11 pass with public admission blocked.
- Replay against advanced ownership state: blocks.
- One participant, mismatched signature participants, wrong signing key, subject drift, duplicate rows, or boolean sequence: blocks or is rejected.
- A blocked v10 quorum cannot be promoted by ownership signatures.
- Resealed promotions under stale expected hashes fail closed.
- Outputs are deterministic, input-immutable, and redacted.
- Production source contains no private key, state I/O, network, or runtime access.

## Consequences and non-claims

v11 introduces an exact previous-plus-one witness ownership transition and makes anti-replay state an explicit contract. It does not prove the previous state supplied by the caller is current, that witnesses durably store the next state, that they reject rollback requests, or that witness identity and independence are genuine. It also does not prove global latestness, real CAS, durability, clock/snapshot/broker source truth, execution, profitability, runtime integration, migration safety, writer authorization, paper authorization, or live authorization.

The natural-forward public chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 is not reissued.
