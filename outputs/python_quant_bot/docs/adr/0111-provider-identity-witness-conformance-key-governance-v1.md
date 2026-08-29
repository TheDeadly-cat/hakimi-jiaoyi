# ADR 0111: Provider identity witness conformance and key governance v1

## Status

Accepted as an inactive, fail-closed research contract. It is not connected to current evidence, UI, server, engine, CLI, paper, or live paths.

## Context

ADR0108 verifies that two preregistered keys signed internally consistent occurrence-cardinality and time-window claims. ADR0109 verifies that those claims remain stable over an exact bounded checkpoint prefix. Neither contract proves that the witness implementations conform to a public protocol, that their test suites are complete, or that their keys were independently generated, rotated, checked for revocation, and held in separated custody domains.

A further ordinary signature would only move the trust assumption. The missing boundary is a versioned consumer that binds the exact witness implementations and audit suites to independent conformance and governance auditor roles while continuing to state that those auditors are not externally trusted by this repository.

## Decision

Add an inactive `registration-v1` and `evaluation-v1` consumer.

The registration preregisters:

1. Exact ADR0108 registration and ADR0109 longitudinal-evaluation receipt hashes and source fingerprints.
2. Occurrence-provider and time-authority entity, key, public-key hash, and implementation hash bindings.
3. Separate conformance and governance auditor entities, keys, and public-key hashes; all four witness/auditor key roles must be distinct.
4. Role-specific audit run IDs, suite IDs, suite hashes, and minimum exact test-vector counts.
5. Key ceremony transcript, rotation policy, key epochs and predecessor commitments, revocation registry, custody policy, validity interval, and audit-age limits.

The evaluation:

1. Reruns the ADR0108 registration verifier and both ADR0109 registration and longitudinal-evaluation verifiers.
2. Requires the audited witness identities and key hashes to equal the ADR0108 registration.
3. Verifies two exact-shape Ed25519 conformance receipts against the independent conformance-auditor key. Each receipt must bind its target implementation, suite, exact vector count, zero failed vectors, source receipts, preregistration, and bounded timestamps.
4. Verifies one exact-shape Ed25519 governance receipt against the separate governance-auditor key. The receipt must bind the ceremony transcript, key epochs and predecessor commitments, validity interval, a bounded revocation snapshot with both target keys claimed non-revoked, and separated custody domains.
5. Rejects unknown fields, Python boolean/integer aliases, role or key collisions, source drift, implementation or suite drift, partial test passes, stale or future audit times, revoked keys, custody collapse, and signature or public-key drift.

The highest state is `SIGNED_WITNESS_CONFORMANCE_AND_KEY_GOVERNANCE_CLAIMS_VERIFIED_EXTERNAL_AUDITOR_TRUST_UNPROVEN`.

## Proof boundary

This state proves only that locally supplied receipts, signed by preregistered audit keys, make internally consistent claims about named implementation hashes, named audit-suite hashes, test-vector counts, and key-governance records. It does not prove that either auditor is independent or authoritative, that a suite is complete, that an implementation hash corresponds to deployed code, that a ceremony or custody event occurred, that a revocation registry is complete, or that supplied timestamps are externally correct.

Therefore external witness trust, external auditor trust, index completeness, global uniqueness, freshness, replay absence, complete history, observation admission, parameter-selection authority, promotion, paper permission, and live permission remain false in every output.

## Consumer-first activation order

1. Keep this consumer inactive and exercise it only with pure synthetic supplied receipts.
2. Define immutable external implementation manifests, protocol suites, test vectors, key-ceremony records, rotation records, revocation snapshots, and custody records without changing this consumer.
3. Obtain genuinely independent audit keys and receipts, then repeat the adversarial contract matrix against those detached artifacts.
4. Assess auditor provenance and suite completeness separately. A valid signature alone cannot satisfy this step.
5. Require a new migration ADR and explicit authorization before any truth-bearing field or current consumer can change.

## Adversarial acceptance matrix

The targeted matrix covers exact registration shape, source verifier enforcement, source receipt and witness-key binding, auditor role separation, canonical Ed25519 signatures, implementation and suite drift, exact vector counts, zero-failure enforcement, audit duration and age, key validity, genesis and rotated predecessor commitments, non-revocation claims, revocation snapshot age, custody separation, deterministic sealing, and negative authority preservation.

No backtest, market data, runtime state, service, browser, scheduler, paper path, or live path is used.

## Validation evidence

- Static fingerprint: '20260822-provider-identity-witness-conformance-key-governance-contract-2'.
- Consumer SHA-256: '8F5DB9A2C03A8DE3294266C1613190C05F98265783C1021CFE1915B81723E75F'.
- Targeted synthetic contract matrix: 47/47 PASS.
- Contract-2 independent public-API matrix: 14/14 PASS, comprising one positive chain and thirteen adversarial fail-closed cases.
- Combined ADR0111/ADR0112 in-memory Python compilation: 4/4 PASS.
- Factor-calibration family: 1002/1002 PASS across 47 explicitly selected classes; failures 0 and errors 0.
- Lean validation: 20 checks listed and 20 planned; executed 0, completed 0, reused 0, runtime mutations false, paper false, and live false. Plan hash: '3c78ae65dccb1b7fa7f946b35fb59e413b793a1dbd6d7c4a4fbbe782a6d1fe6c'.
- Explicit active-entrypoint audit: 43 source files checked and zero references to this consumer or its strongest state.
- No fresh validation, backtest, market-data task, runtime task, service, browser, scheduler, paper task, or live task was run.

## Result

The strongest synthetic state is 'SIGNED_WITNESS_CONFORMANCE_AND_KEY_GOVERNANCE_CLAIMS_VERIFIED_EXTERNAL_AUDITOR_TRUST_UNPROVEN'. The receipts bind implementation hashes, suite hashes, exact test-vector outcomes, ceremony and rotation commitments, a bounded non-revocation claim, and custody separation. They do not establish auditor independence, suite completeness, deployment identity, external time truth, uniqueness, freshness, replay absence, complete history, profitability, or any trading permission.

## Contract-2 registration binding correction

The initial contract-1 registration receipt projected only selected evidence fields. Coordinated changes to an omitted registration field and downstream signed receipts could therefore reuse the old registration receipt. Contract-2 adds the strict canonical hash of the complete normalized registration to every registration receipt.

- Test SHA-256: '2B263EF044900A9A72357CC525E3E6CFB99C734ACD611185E2777C8790FE6901'.
- Direct registration-drift and coordinated-drift tests fail closed at 'audit_registration_receipt_invalid'.
- The source and receipt schema names remain v1, while the static implementation fingerprint explicitly advances to contract-2.
- This correction does not activate the consumer or promote external trust, uniqueness, freshness, paper, or live authority.
