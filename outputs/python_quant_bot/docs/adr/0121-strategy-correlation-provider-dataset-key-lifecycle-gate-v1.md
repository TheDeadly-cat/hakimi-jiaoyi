# ADR0121: Strategy correlation provider dataset-key lifecycle gate v1

Status: Accepted as an inactive research-only candidate on 2026-08-22.

## Context

ADR0120 verifies a detached Ed25519 signature from a dataset-content key that is locally registered against one provider and one ADR0119 composition. It intentionally has no lifecycle input. A pure synthetic call showed that changing an external status snapshot from `revoked=false` to `revoked=true` leaves the ADR0120 result byte-for-byte unchanged because its public evaluator has no reference time, rotation epoch, previous-key commitment, revocation snapshot, or governance-key parameter.

That is correct for the immutable ADR0120 signature contract, but it is insufficient for any future consumer. A signature made inside the registered validity window must not be treated as currently usable when a later independently signed lifecycle receipt reports revocation, broken provider binding, or failed custody separation.

## Decision

Add a detached consumer-first composition layer with three versioned contracts:

- `strategy-correlation-provider-dataset-key-lifecycle-registration-v1`
- `strategy-correlation-provider-dataset-key-lifecycle-governance-receipt-v1`
- `strategy-correlation-provider-dataset-key-lifecycle-gate-v1`

The registration replays ADR0120 through its public verifier and binds the provider, dataset key ID/hash, dataset registration and attestation hashes, rotation epoch, previous-key commitment, rotation policy, revocation registry, custody policy, freshness limits, and a fourth Ed25519 governance key.

The governance key role is `PROVIDER_DATASET_KEY_LIFECYCLE_GOVERNANCE`. Its public key must differ from the dataset-content, identity-registry, and timestamp-adapter keys. The production service accepts only the governance public key and an externally supplied detached signature; it never accepts or generates a private key.

The signed lifecycle receipt can express positive or negative lifecycle state. Evaluation is fail closed unless all of the following hold:

- ADR0120 is reverified from its complete source context.
- Registration and receipt expected hashes match.
- The governance signature verifies over the strict canonical receipt digest and domain.
- Rotation epoch and previous-key commitment match the preregistration.
- The receipt and revocation snapshot are fresh at an explicit reference time inside the dataset-key validity window.
- The signed receipt says the dataset key is not revoked.
- The signed receipt affirms provider-key binding, dataset-key custody, and custody-domain separation.

The strongest state is `SIGNED_DATASET_KEY_BINDING_NONREVOCATION_AND_CUSTODY_CLAIMS_VERIFIED_EXTERNAL_GOVERNANCE_TRUST_UNPROVEN`. This wording distinguishes verified signed claims from externally proven custody or registry truth.

## Consumer-first activation order

1. Keep ADR0121 detached from current reports and active entrypoints.
2. Exercise synthetic positive, revoked, stale, rotated, collision, custody-denial, tamper, and expected-pin cases.
3. Separately register a real external governance key and durable revocation source under an authorized migration.
4. Add a new versioned report consumer that treats missing or invalid lifecycle evidence as UNKNOWN.
5. Add a neutral SOURCE -> GAP -> MATURITY -> PERMISSION presentation only after the report contract is stable.
6. Consider current-pointer migration only through a separate explicit decision; never auto-reissue pointer-v2.

## Adversarial matrix

The v1 matrix covers source-verifier bypass, all four key-role collisions, invalid key IDs, genesis/rotated epoch rules, previous-key collisions, bool-as-int freshness aliases, malformed signatures, wrong signing keys, expected-pin drift, signed revocation, signed binding denial, signed custody denial, custody-domain collision, stale receipts, stale revocation snapshots, validity-window escape, source drift, coherent output resealing, output redaction, deterministic replay, and production API private-key exclusion.

## Authority and compatibility

The gate remains disconnected from reports, writers, server, engine, CLI, UI, paper, and live paths. It writes no pointer and grants no admission or trading authority. The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 fields, hash contract, and no-auto-reissue behavior remain unchanged.

## Validation evidence

- Synthetic gap proof: ADR0120 returns the same verified result before and after an external in-memory revoked flag because lifecycle inputs are absent.
- Targeted ADR0121 contracts: 26/26 PASS.
- In-memory compile: 2/2 PASS.
- Independent public-API adversarial matrix: 18/18 PASS.
- Direct ADR0119/ADR0120/ADR0121 family: 67/67 PASS across three TestCase classes.
- Research lean: 15 listed/planned, 0 executed/completed/reused; ADR0121 TestCase and service source occur once; runtime mutation, paper, and live are false.
- Eight explicit active entrypoints contain zero ADR0121 references.
- Static fingerprint: `20260822-strategy-correlation-provider-dataset-key-lifecycle-gate-1`.

## Remaining boundary

The receipt proves that a locally registered governance key signed lifecycle claims. It does not prove external governance authority, HSM or organizational custody, revocation-registry durability, complete rotation history, authoritative time, replay absence, provider data issuance truth, robustness, profitability, paper authorization, or live authorization. Durable lifecycle receipt publication and replay/uniqueness evidence are separate future contracts.
