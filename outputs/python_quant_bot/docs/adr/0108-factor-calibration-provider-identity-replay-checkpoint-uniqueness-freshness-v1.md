# ADR0108: Provider-identity occurrence cardinality and time-window evidence v1

## Status

Accepted as an inactive, fail-closed research contract. It is not connected to current evidence, UI, server, engine, CLI, paper, or live paths.

## Context

ADR0107 proves either a registered genesis anchor or one exact previous persisted checkpoint segment. It cannot infer that an assertion occurs only once in the registry, that no replay exists, or that checkpoint and scan timestamps are fresh. Existing candle deduplication, duplicate decision suppression, and market-data freshness are different domains and cannot satisfy this gap.

## Decision

Add two consumer-first contracts without implementing a producer:

1. A registration receipt pins distinct occurrence-provider and time-authority roles, source replay and persistence registration hashes, full-scan and exactly-one policies, signature domains, and maximum claimed time windows.
2. An evaluation reruns ADR0107, requires both witness roles to differ from every upstream provider, identity, replay, and persistence key, verifies Ed25519 signatures, and binds the signed claims to the current lineage receipt, checkpoint, assertion digest, and replay leaf index.

The occurrence claim must cover `[0, checkpoint_tree_size)`, claim an index record count equal to the checkpoint tree size, and report exactly one occurrence at the already verified replay leaf index. The time claim must bind the signed occurrence receipt and satisfy `checkpoint_issued_at <= scan_completed_at <= reference_time` within preregistered limits.

## Authority boundary

The highest state is `SIGNED_COMPLETE_OCCURRENCE_CARDINALITY_AND_TIME_WINDOW_CLAIMS_VERIFIED_EXTERNAL_TRUST_UNPROVEN`.

Cryptographic verification proves only that the registered keys signed internally consistent claims. It does not prove that either external role is authoritative, that the occurrence index is complete, that the reference time is externally correct, that future replay is absent, or that the assertion is globally unique or fresh. Therefore `assertion_uniqueness_verified`, `freshness_verified`, `replay_absence_verified`, `complete_history_verified`, observation admission, parameter-selection authority, paper permission, and live permission remain false in every output.

## Activation order

1. Keep this consumer inactive and validate only with pure synthetic supplied receipts.
2. Specify external provider identity and operational conformance separately.
3. Accumulate signed claims over multiple checkpoints without changing current evidence.
4. Add an independent trust and coverage audit before any uniqueness or freshness field can become true.
5. Require a separate migration decision before any current consumer can read a successor projection.

## Validation evidence (2026-10-02)

- Targeted registration and verifier contract: 36/36 PASS.
- Independent public-API chain: 29/29 PASS, including real ADR0103, ADR0105, ADR0106, and ADR0107 verification before the two new signatures.
- Adversarial matrix: incomplete scans, duplicate counts, bool/int aliases, signature/key drift, occurrence binding drift, invalid time ordering, stale windows, source-lineage drift, role collisions, and lineage tampering all fail closed.
- Cross-lag factor calibration family: 847/847 PASS across 43 modules.
- In-memory syntax compilation: 3/3 PASS.
- Lean validation: 19 checks listed; dry-run planned 19, executed 0, runtime mutations false, paper false, live false.
- Explicit active-source references: 0.

The strongest state is `SIGNED_COMPLETE_OCCURRENCE_CARDINALITY_AND_TIME_WINDOW_CLAIMS_VERIFIED_EXTERNAL_TRUST_UNPROVEN`. `assertion_uniqueness_verified`, `freshness_verified`, `replay_absence_verified`, `complete_history_verified`, and every authority field remain false.