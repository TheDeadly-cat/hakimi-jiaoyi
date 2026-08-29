# ADR 0404: Signed Portfolio Snapshot Effective Budget v5

- Status: Accepted for isolated synthetic research only
- Date: 2026-08-24
- Supersedes: nothing
- Activates current: no

## Context

ADR0403 prevents a caller from labeling an arbitrary proposal as risk reduction, but v4 still accepts equity and before-positions directly from the caller. A pure synthetic comparison showed that the same positions and proposal BLOCK at equity 5,000 but PASS when the caller claims equity 10,000. V4 correctly reports that position-snapshot provenance is unverified.

The projected after-state used for a reduction is deterministic and does not need to be presented as an observed post-trade state. The remaining provenance boundary is the current before snapshot and its equity.

## Decision

Add an unmounted v5 successor containing:

1. A portfolio-snapshot provider preregistration binding provider ID, key ID, Ed25519 SPKI hash, trust domain, account-scope hash, and implementation claim.
2. A strict snapshot claim containing normalized equity, unique position rows, snapshot ID, sequence, and claimed observation time.
3. A signed snapshot candidate and redacted local verification evidence.
4. A v5 consumer whose public API has no independent equity or positions parameters. It extracts both exclusively from the exact signed claim and rebuilds v4.

The local signature proves possession of the preregistered key only. It does not prove provider identity, broker truth, implementation conformance, sequence continuity, observation-time authority, freshness, or execution.

## Consumer-first activation order

1. Preregister a snapshot provider identity and key hash.
2. Build and sign one immutable before snapshot.
3. Verify the signature and bind that exact claim to v5.
4. Rebuild v4 using only snapshot equity and positions.
5. Add provider identity, source truth, sequence continuity, and freshness evidence before any mounted consumer.
6. Do not switch current, write pointers, activate runtime gates, or grant paper/live/writer authority in this ADR.

## Adversarial matrix

Sixteen cases cover the caller-equity gap, exact blocked preregistration, local key-signature evidence, low-equity blocking, high-equity local binding, equity tampering, wrong-key self-signature, signature tampering, invalid/duplicate position rows, boolean and non-finite aliases, metadata aliases, provider drift, signed-before risk reduction, transition mismatch, verifier promotion, redaction, determinism, input immutability, and absence of private-key/I/O/system-clock/runtime dependencies.

## Consequences

- V5 consumers cannot override signed snapshot equity or positions through parallel function parameters.
- A registered key can still sign false data; local PASS therefore remains distinct from source truth, provider identity, freshness, continuity, execution, profitability, and trading permission.
- V4 remains unmounted and unchanged. V5 is also unmounted pending independent provenance and activation review.
- The natural-forward public chain remains audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2.
- Legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 is not reissued.
