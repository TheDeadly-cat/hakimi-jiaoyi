# ADR0405: Snapshot continuity and freshness effective budget v6

Date: 2026-08-24

Status: Accepted as an unmounted synthetic contract

## Context

ADR0404 binds portfolio equity and positions to an exact Ed25519-signed snapshot. It intentionally leaves snapshot sequence continuity and freshness false. A pure synthetic call through the existing v5 consumer showed the practical consequence: the exact same sequence-8 snapshot, observation timestamp, signature, and evidence document can be evaluated twice and returns the same local `PASS` both times. The evidence still says continuity and freshness are unverified, but no consumer check prevents an older signed snapshot from being selected after a newer head exists or after its permitted age has elapsed.

This is a provenance and risk-budget integrity gap. A valid signature proves only possession of the preregistered local key over exact bytes. It does not prove that a snapshot is the latest account state, that a supplied evaluation time is trustworthy, or that a state transition was atomically persisted.

## Decision

Add an unmounted v6 successor with four strict, versioned documents:

1. `strategy-correlation-portfolio-snapshot-admission-policy-v1` preregisters an exact `previous + 1` sequence rule, strictly increasing observation time, maximum age, maximum future skew, and exact externally expected current-head hash rule.
2. `strategy-correlation-portfolio-snapshot-admission-state-v1` commits to one policy, provider, account scope, state revision, last snapshot claim hash, last sequence, and last observation time.
3. `strategy-correlation-portfolio-snapshot-admission-transition-v1` verifies the previous state and v5 signature evidence, checks sequence advancement and freshness arithmetic, and emits a candidate next state.
4. `strategy-correlation-cluster-effective-bet-budget-v6` rebuilds v5, requires the transition's next-state hash to equal an independently supplied expected current-head hash, binds the exact snapshot to that head, and rechecks freshness at consumer evaluation time.

The contract intentionally permits repeated read-only evaluations of the same current head while it remains inside the preregistered age window. Once an external current head advances, an older transition fails the exact-head check. This avoids incorrectly treating a portfolio snapshot as a one-use token while still preventing selection of an obsolete head.

## Invariants

- All sequence numbers, revisions, and millisecond timestamps are strict integers; booleans are rejected.
- Candidate sequence must equal the previous sequence plus exactly one.
- Candidate observation time must be strictly greater than the previous observation time.
- Candidate snapshot claim hash must differ from the previous claim hash.
- Transition and consumer ages are checked against the exact preregistered maximum age and future-skew bounds.
- Consumer evaluation time cannot precede transition evaluation time.
- Policy, state, transition, signature evidence, v5 budget, provider, account scope, and snapshot hashes are exact-bound and strictly canonical.
- Equity and positions still come only from the signed v5 claim. v6 accepts no caller equity or positions.
- Outputs redact raw positions, public keys, and signatures.
- No system clock, network, filesystem, runtime state, database, cache, log, market data, account data, scheduler, or writer is accessed.
- A local contract `status` may be `PASS`, but predecessor and v6 public `admission_status` remain `BLOCKED`; local arithmetic cannot promote current admission authority.
- All current, migration, writer, paper, and live authority remains false.

## Consumer-first activation order

1. Keep policy, state, transition, and v6 budget unmounted and without a `current` alias.
2. Validate only with pure synthetic documents and exact expected hashes.
3. Add a separately reviewed read-only clock attestation boundary; do not infer trust from a caller-supplied integer.
4. Add a separately reviewed atomic compare-and-swap current-head store and crash-recovery contract; do not infer persistence from a candidate next-state document.
5. Add provider identity, implementation conformance, and broker/source-truth evidence independently.
6. Add report-schema consumers before any current activation consideration.
7. Require explicit authorization for any later runtime activation. No activation can grant paper or live authority.

## Adversarial matrix

- Same signed v5 snapshot accepted twice without v6: demonstrates the inherited gap.
- Exact sequence and monotonic observation time: local transition passes.
- Old transition against an advanced external current-head hash: blocks.
- Repeated read of the same current head inside the age window: deterministic pass.
- Snapshot older than the maximum at transition or consumer evaluation: blocks.
- Snapshot beyond future-skew tolerance: blocks; exact boundary passes.
- Skipped or duplicate sequence: blocks.
- Nonmonotonic observation time: blocks.
- Consumer clock rollback before transition evaluation: blocks.
- Valid transition with a blocked v5 risk budget: remains blocked.
- Tampered signature evidence, provider registration, policy, state, transition, or v6 result: exact verification fails closed.
- Resealed promotions with stale expected hashes: fail closed.
- Boolean aliases for numeric fields: rejected.
- Outputs are deterministic, input-immutable, and redacted.

## Consequences and non-claims

v6 closes the pure consumer-contract gap for explicit sequence transition, bounded age arithmetic, and exact current-head selection. It does not prove the supplied clock is trustworthy or that the expected current head was atomically persisted. It also does not prove provider identity, implementation conformance, broker/source truth, execution, profitability, runtime integration, migration safety, writer authorization, paper authorization, or live authorization.

The natural-forward public chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 is not reissued.
