# ADR 0067: Compose precommit and beta-stability gates

- Status: Accepted for an unmounted versioned candidate
- Date: 2026-08-26
- Scope: G3-v1 plus H0 monotone composition

## Context

G3-v1 binds a future evaluation identity and local precommit hash chain. H0 independently checks contiguous-fold beta stability. A pure synthetic path proves the composition gap: the same G0/G1 source produces G3 `BOUND_LOCAL_ONLY` and H0 BLOCK, with identical replay, registration, and calibration hashes. G3-v1 is frozen and contains no H0 binding.

## Decision

Add H1 as precommit gate v2:

- schema: `strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v2`;
- fingerprint: `20260826-cross-lag-factor-calibration-precommit-gate-2`;
- sources: exact G3-v1 and H0 receipts plus their complete verification contexts;
- calculation policy: none; invoke both official verifiers and cross-bind shared source hashes;
- privacy: aggregate-only projection.

The positive composition is named `BOUND_LOCAL_ONLY_STABILITY_GUARDED`. It requires G3 `BOUND_LOCAL_ONLY` and H0 `STABLE_CANDIDATE`. H0 BLOCK or G3 BLOCK produces v2 BLOCK. Unknown, missing, unsupported, invalid, or context-substituted sources close UNKNOWN.

## Monotonicity

All unique G3 and H0 blockers remain in first-seen order. V2 appends `PRECOMMIT_GATE_V2_NOT_ACTIVATED`. No source blocker is relaxed, and source hashes for replay, registration, and calibration observations must agree across both gates.

## Claim calibration

`STABILITY_GUARDED` means the fixed H0 candidate threshold passed and its hash was bound. It does not prove beta constancy. `BOUND_LOCAL_ONLY` still means the external time anchor is unverified. Formal registration v2 issuance, future evaluation activation, current admission, paper/live authority, and profitability claims remain false.

## Adversarial matrix

Coverage includes stable composition, H0-over-G3 blocking, G3 source blocking, missing/unsupported sources, expected source-gate hashes, coherent G3/H0 reseals, complete-context substitution, cross-hash binding, blocker deduplication without relaxation, aggregate privacy, stability non-proof, authority locks, non-native and non-finite sources, resealed v2 tamper, deterministic output, and denied external state.

## Compatibility and activation

G3-v1 and H0 remain immutable and independently verifiable. H1 is unmounted and absent from routes, services, schedulers, Electron, pointers, and UI. No existing evidence is auto-migrated or reissued. Natural-forward, pack-v5 UNKNOWN, pointer-v2, current denial, paper denial, permanent live lock, and no-profitability boundaries remain unchanged.
