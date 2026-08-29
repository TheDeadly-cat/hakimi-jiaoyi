# ADR0406: Signed evaluation clock effective budget v7

Date: 2026-08-24

Status: Accepted as an unmounted synthetic contract

## Context

ADR0405 adds exact sequence transition, current-head binding, and freshness arithmetic. Its v6 consumer still receives `evaluated_at_unix_ms` as an independent caller argument. A pure synthetic proof used the same signed snapshot, transition, and current-head commitment twice: a caller-selected age of 500 milliseconds produced local `PASS`, while a later age of 5000 milliseconds was blocked as stale. The v6 result correctly reported `trusted_evaluation_clock_verified=false`, but the API still allowed the caller to choose the value that controls freshness.

This is a provenance gap, not a clock-format gap. A signed time claim can bind a value to a preregistered key and exact budget subject, but a local key signature alone cannot prove provider identity, clock implementation, counter continuity, or time-source truth.

## Decision

Add an unmounted v7 successor with four new strict documents:

1. `strategy-correlation-evaluation-clock-provider-preregistration-v1` preregisters clock provider ID, key ID, Ed25519 SPKI hash, trust domain, account scope, and implementation claim hash.
2. `strategy-correlation-evaluation-time-claim-v1` binds an attestation ID, clock counter, evaluation timestamp, policy hash, transition hash, current-state hash, and snapshot-claim hash.
3. `strategy-correlation-evaluation-time-signed-attestation-v1` carries the exact Ed25519 public-key and signature candidate.
4. `strategy-correlation-evaluation-time-signature-evidence-v1` verifies the preregistered key hash and signature while redacting raw key and signature material.

`strategy-correlation-cluster-effective-bet-budget-v7` has no independent evaluation-time parameter. It extracts the timestamp only from the exact signed claim, verifies subject and account-scope binding, rebuilds v6 with that timestamp, and requires v6 local `PASS` while preserving v6 public admission authority as `BLOCKED`.

## Invariants

- The clock provider registration, claim, signed candidate, evidence, and v7 output are strict canonical documents.
- All external expected hashes are exact lowercase SHA-256 values.
- Clock counter and evaluation timestamp are strict integers; booleans are rejected.
- Public-key SPKI and signature use canonical base64; SPKI must be canonical DER Ed25519 and the signature must be exactly 64 bytes.
- Signature verification covers the raw 32-byte SHA-256 digest of the exact clock claim.
- The clock claim binds policy, transition, current head, snapshot claim, purpose, and account scope.
- v7 accepts no independent evaluation-time, equity, or positions argument.
- A signed stale time preserves v6 freshness blocking.
- Local clock-signature `PASS` does not set trusted-clock or time-source-truth facts.
- v6 and v7 public `admission_status` remain `BLOCKED` even when local contract status is `PASS`.
- Outputs redact raw clock public keys, signatures, and snapshot positions.
- No system clock, network, filesystem, runtime state, database, cache, log, market data, account data, scheduler, or writer is accessed.
- All current, migration, writer, paper, and live authority remains false.

## Consumer-first activation order

1. Keep all clock and v7 documents unmounted and without a `current` alias.
2. Validate only with pure synthetic keys, claims, and existing synthetic snapshot contracts.
3. Independently attest clock provider identity and implementation; do not infer either from key possession.
4. Bind clock-counter continuity to the separately reviewed atomic current-head state source.
5. Define rollback, crash-recovery, counter-gap, and dual-clock discrepancy policy before runtime observation.
6. Add neutral report-schema consumers before any current activation consideration.
7. Require explicit authorization for any later runtime activation. No activation can grant paper or live authority.

## Adversarial matrix

- Same v6 subject with caller-selected 500ms versus 5000ms age: demonstrates the inherited gap.
- Exact signed clock subject and account scope: local v7 pass with public admission blocked.
- Signed stale time: v6 freshness block is preserved.
- Wrong policy, transition, current-head, or snapshot subject hash: blocks.
- Wrong account scope: blocks.
- Wrong signing key, tampered claim, malformed base64, or wrong signature length: blocks or is rejected.
- Provider drift and resealed promotions under stale expected hashes: fail closed.
- Boolean counter or timestamp aliases: rejected.
- Outputs are deterministic, input-immutable, and redacted.
- Production source contains no private key, system-clock call, I/O, network, or runtime access.

## Consequences and non-claims

v7 removes the independent caller-time argument and cryptographically binds the selected evaluation time to the exact v6 subject. It does not establish that the clock provider is who it claims to be, that its implementation is conformant, that the counter is continuous, that the timestamp is true, or that the current head is atomically persisted. It also does not prove snapshot source truth, execution, profitability, runtime integration, migration safety, writer authorization, paper authorization, or live authorization.

The natural-forward public chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 is not reissued.
