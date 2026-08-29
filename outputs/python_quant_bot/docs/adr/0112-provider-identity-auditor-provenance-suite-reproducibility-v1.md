# ADR 0112: Provider identity auditor provenance and registered-suite reproducibility v1

## Status

Accepted as an inactive, fail-closed research contract. It is not connected to current evidence, UI, server, engine, CLI, paper, or live paths.

## Context

ADR0111 verifies signatures over claims about witness implementations, conformance suites, vector counts, key ceremony, rotation, revocation, and custody. A valid audit signature still does not identify the auditor's organization or control group, establish absence of conflicts, show the finite protocol requirement set, prove bidirectional vector coverage, or demonstrate reproduction by separately controlled runners.

A scoped audit found zero provenance, requirement-manifest, vector-corpus, or dual-runner contracts in twelve provider-identity services and forty-three explicit active source files. A pure synthetic ADR0111 call also showed that nine such dimensions are absent from its fourteen evaluation parameters.

## Decision

Add an inactive registration and evaluation consumer that validates actual finite manifests and signed per-vector results rather than accepting aggregate completeness booleans.

The registration pins:

1. Exact ADR0111 registration and evaluation receipt hashes and source fingerprint.
2. Six ordered roles: source conformance auditor, source governance auditor, provenance registry authority, suite custodian, runner A, and runner B.
3. Distinct entity, key, public-key hash, organization, control-group, and beneficial-owner-disclosure commitments for all roles.
4. Distinct implementation-manifest, environment-manifest, and execution identifiers for both runners.
5. Witness implementation hashes, protocol and suite versions, finite requirement-manifest root and count, vector-corpus root and polarity counts, per-requirement positive/negative minima, and bounded receipt times.

The evaluation:

1. Reruns the ADR0111 evaluation verifier and binds its auditor roles and witness implementation hashes.
2. Verifies a registry-signed exact role list, beneficial-owner disclosures, conflict snapshot, and negative common-control/conflict declarations.
3. Verifies a custodian-signed sorted requirement list and sorted vector corpus. Every vector must reference a registered requirement, identifiers must be unique, roots and counts must match preregistration, and every registered requirement must have the preregistered minimum positive and negative coverage.
4. Verifies two role-specific Ed25519 runner receipts. Each must report every vector exactly once in canonical order, match every expected result hash, pass every vector, skip none, bind its distinct implementation/environment manifest, and satisfy bounded execution times.
5. Requires both runner result-transcript roots to agree while their signed receipts remain distinct.

The highest state is `SIGNED_PROVENANCE_AND_DUAL_RUNNER_REGISTERED_SUITE_COVERAGE_CLAIMS_VERIFIED_EXTERNAL_REGISTRY_TRUST_UNPROVEN`.

## Proof boundary

The consumer proves coverage only relative to the supplied, preregistered finite requirement set. It does not prove that the requirement set exhausts the real protocol. Registry signatures and distinct declared organizations do not prove actual independence or beneficial ownership. Manifest hashes do not prove that the hashed implementation was deployed. Supplied timestamps do not prove external time truth.

Therefore external registry trust, auditor independence, true suite completeness, deployed-code identity, external time truth, uniqueness, freshness, replay absence, complete history, profitability, observation admission, promotion, paper permission, and live permission remain false.

## Consumer-first activation order

1. Keep this consumer inactive and use only pure synthetic supplied manifests and receipts.
2. Publish an immutable protocol requirement manifest and vector corpus without changing this consumer.
3. Obtain externally governed provenance, ownership, control-group, and conflict-registry evidence.
4. Run the complete corpus through two genuinely separate implementations and environments, then submit detached signed receipts.
5. Review whether the registered requirement set is externally complete and whether role independence is credible.
6. Require a new migration ADR and explicit authorization before any truth-bearing field or current consumer can change.

No backtest, market data, runtime state, service, browser, scheduler, paper path, or live path is used.

## Validation evidence

- Static fingerprint: '20260822-provider-identity-auditor-provenance-suite-reproducibility-contract-1'.
- Consumer SHA-256: '03CD4626500DF807D5557BD1261530FFAE4EF70920705D31C15580E4FD4452CC'.
- Test SHA-256: 'C3D7AD7D7C9E51670D7C1301B76118AFED296CE479142804F3C613163FA43EFB'.
- Pure synthetic gap chain: ADR0111 strongest state observed while nine provenance, ownership, corpus-root, coverage-map, and dual-runner dimensions remained outside its fourteen evaluation parameters.
- ADR0112 targeted matrix: 51/51 PASS.
- Combined ADR0111/ADR0112 targeted matrix: 98/98 PASS.
- Independent public-API matrix: 16/16 PASS, comprising one positive chain and fifteen adversarial fail-closed cases.
- Combined in-memory Python compilation: 4/4 PASS.
- Factor-calibration family: 1002/1002 PASS across 47 classes; failures 0 and errors 0.
- Lean validation: 20 listed, 20 planned, 0 executed, 0 completed, 0 reused, runtime mutations false, paper false, and live false. Plan hash: '3c78ae65dccb1b7fa7f946b35fb59e413b793a1dbd6d7c4a4fbbe782a6d1fe6c'.
- Explicit active-entrypoint audit: 43 files and zero references to ADR0111 or ADR0112 consumers and strongest states.
- No fresh validation, backtest, market-data task, runtime task, service, browser, scheduler, paper task, or live task was run.

The registration receipt binds the strict canonical hash of the complete normalized registration. Coordinated registration and provenance drift is rejected before any provenance, suite, or runner claim can be accepted.

## Result

The strongest synthetic state is 'SIGNED_PROVENANCE_AND_DUAL_RUNNER_REGISTERED_SUITE_COVERAGE_CLAIMS_VERIFIED_EXTERNAL_REGISTRY_TRUST_UNPROVEN'. It proves exact coverage and dual-runner agreement only relative to the supplied preregistered finite requirement set. External registry trust, actual auditor independence, true protocol completeness, deployed-code identity, external time truth, profitability, and all trading authority remain unproven or false.
