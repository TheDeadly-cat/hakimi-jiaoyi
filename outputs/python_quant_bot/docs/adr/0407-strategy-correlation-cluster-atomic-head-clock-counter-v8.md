# ADR0407: Atomic head and clock-counter effective budget v8

Date: 2026-08-24

Status: Accepted as an unmounted synthetic contract

## Context

ADR0406 removes the independent evaluation-time argument and binds time to an exact signed clock claim. v7 still receives the expected snapshot current-state hash as an independent caller argument, and the signed clock counter has no predecessor state. A pure synthetic proof held policy, transition, current snapshot state, snapshot claim, and evaluation time constant while changing only the signed counter from 41 to 900. Both v7 evaluations returned local `PASS`; both correctly reported counter continuity and atomic current-head persistence as false.

This leaves two related provenance gaps: no exact previous counter controls the signed clock claim, and no signed compare-and-swap state transition derives the snapshot head supplied to v7. A signature over a commit receipt can bind these values and their arithmetic, but it still cannot prove that a real store performed an atomic durable write.

## Decision

Add an unmounted v8 successor with five strict state-source documents:

1. `strategy-correlation-atomic-head-store-provider-preregistration-v1` preregisters store provider ID, key ID, Ed25519 SPKI hash, trust domain, account scope, store epoch, implementation claim, and exact compare-and-swap rules.
2. `strategy-correlation-atomic-head-state-v1` commits policy, state revision, commit index, clock counter, clock evidence, snapshot state, snapshot claim, and transition.
3. `strategy-correlation-atomic-head-commit-claim-v1` verifies an exact previous state and derives revision, commit index, and counter as exact previous-plus-one values before constructing the candidate next state.
4. `strategy-correlation-atomic-head-signed-commit-receipt-v1` carries the exact state-store Ed25519 key and signature candidate.
5. `strategy-correlation-atomic-head-commit-signature-evidence-v1` verifies the preregistered key hash and signature while redacting raw key and signature material.

`strategy-correlation-cluster-effective-bet-budget-v8` has no independent expected snapshot-state hash or clock-counter argument. It derives both from the exact signed commit claim, binds them to clock evidence, snapshot transition, policy, snapshot claim, and account scope, and then rebuilds v7. v7 and v8 public admission remain blocked.

## Invariants

- Provider, previous state, commit claim, signed receipt, evidence, and v8 output are strict canonical documents.
- State revision, commit index, and clock counter are strict integers and advance by exactly one; booleans are rejected.
- The commit claim exact-binds expected previous-state hash and derived next-state hash.
- The derived state exact-binds clock evidence, snapshot state, snapshot claim, transition, policy, account scope, store epoch, and provider.
- v8 derives the v7 expected snapshot state and counter from the signed receipt; neither is an independent v8 argument.
- Clock evidence counter must equal the derived atomic-state counter.
- Signed stale clock evidence still preserves v7 freshness blocking.
- Ed25519 SPKI and signature use canonical encodings and exact hashes.
- Local store-key signature and transition arithmetic do not set atomicity, durability, crash-recovery, provider identity, or implementation facts.
- v7 and v8 public `admission_status` remain `BLOCKED` even when local contract status is `PASS`.
- Outputs redact raw keys, signatures, and positions.
- No filesystem, database, cache, log, network, market, account, runtime, scheduler, CAS operation, or writer is accessed.
- All current, migration, writer, paper, and live authority remains false.

## Consumer-first activation order

1. Keep provider, state, receipt, evidence, and v8 unmounted and without a `current` alias.
2. Validate only with pure synthetic states and keys.
3. Specify an authenticated read protocol that pins the latest signed receipt rather than allowing a caller to select an old receipt.
4. Implement atomic compare-and-swap, durability barriers, crash recovery, rollback detection, and epoch rotation in an isolated state-store adapter.
5. Independently attest store provider identity and implementation before setting any source-truth fact.
6. Bind the clock provider's counter issuance transaction to the same reviewed state transition.
7. Add neutral report-schema consumers before any current activation consideration.
8. Require explicit authorization for later runtime activation. No activation can grant paper or live authority.

## Adversarial matrix

- Same v7 subject and time with counters 41 and 900: demonstrates the inherited gap.
- Exact previous state and signed commit receipt: local v8 pass with public admission blocked.
- Counter 900 against a derived next counter of 41: blocks.
- Wrong snapshot state, snapshot claim, transition, policy, or account scope: blocks.
- Signed stale clock evidence: v7 freshness block is preserved.
- Wrong store signing key or tampered commit claim: blocks.
- Provider drift, boolean aliases, and resealed promotions under stale expected hashes: fail closed.
- Outputs are deterministic, input-immutable, and redacted.
- Production source contains no private key, state I/O, network, or runtime access.

## Consequences and non-claims

v8 removes independent raw snapshot-head and counter inputs and binds both to an exact signed previous-plus-one state transition. It does not prove that the receipt is the latest receipt, that a real atomic compare-and-swap occurred, that bytes were durably persisted, that crash recovery is correct, or that the store provider is genuine. It also does not prove clock or snapshot source truth, execution, profitability, runtime integration, migration safety, writer authorization, paper authorization, or live authorization.

The natural-forward public chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 is not reissued.
