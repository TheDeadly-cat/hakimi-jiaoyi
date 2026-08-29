# ADR 0065: Future-only factor calibration precommit gate

- Status: Accepted for an unmounted local-binding candidate
- Date: 2026-08-24
- Scope: Future evaluation identity and precommit hash-chain binding

## Context

A verified G1 MATCH report binds the F0-v1 registration, calibration observations, G0 replay, and aggregate beta-ledger hashes. It does not bind a future evaluation identity, declaration timestamp, evaluation-not-before date, or external time-anchor reference. The same G1 hash can therefore be reused under multiple informal evaluation labels.

Creating a formal registration v2 locally would overstate evidence. A caller can fabricate a timestamp or anchor hash, and this repository has no authorized external time-anchor verifier. The next safe step is a verifier-only gate that proves local hash-chain completeness while keeping external timing and formal issuance false.

## Decision

Add two candidate contracts:

- declaration schema: `strategy-correlation-cross-lag-factor-calibration-precommit-declaration-candidate-v1`;
- declaration fingerprint: `20260824-cross-lag-factor-calibration-precommit-declaration-1`;
- gate schema: `strategy-correlation-cross-lag-factor-calibration-precommit-gate-candidate-v1`;
- gate fingerprint: `20260824-cross-lag-factor-calibration-precommit-gate-1`;
- protocol: `FUTURE_FACTOR_RESIDUALIZATION_EVALUATION_V2`.

The service verifies but does not issue declarations. A declaration binds one future evaluation ID, exact G1/G0/registration/calibration hashes, both private beta-ledger hashes, calibration and selection cutoffs, a declared UTC precommit timestamp, an evaluation-not-before date, and an opaque external anchor reference hash.

## Temporal rules

The declared precommit date must be strictly after the calibration cutoff and strictly before the selection cutoff. The evaluation-not-before date must be on or after the selection cutoff. All values are caller-supplied and deterministic; no system clock, file, network, random source, database, or scheduler is consulted.

These ordering checks prove only internal declaration consistency. The external anchor reference is hash-bound but unverified. The output therefore uses `BOUND_LOCAL_ONLY`, never PASS, READY, admitted, or activated.

## Source decisions

- Verified G1 MATCH plus an exact declaration becomes `BOUND_LOCAL_ONLY`.
- Verified G1 BLOCK remains `BLOCK` and retains all source blockers.
- Missing, unsupported, invalid, context-substituted, or tampered declarations/reports close as UNKNOWN.

Every observed output retains G1 blockers and adds:

- `EXTERNAL_PRECOMMIT_TIME_ANCHOR_UNVERIFIED`;
- `FORMAL_RESIDUALIZATION_REGISTRATION_V2_NOT_ISSUED`;
- `FUTURE_EVALUATION_NOT_ACTIVATED`.

## Privacy and authority

The gate exposes only future evaluation/protocol identifiers, declared temporal fields, aggregate facts, and hashes. It excludes calibration rows, identities, factor values/source, returns, and beta values. External timing attestation, formal registration v2 issuance, future evaluation authority, current admission, pointer writes, paper/live authority, and profitability claims remain false.

## Adversarial matrix

Coverage includes MATCH/BLOCK monotonicity, missing/unsupported declarations, expected and broken hashes, every source and beta-ledger binding, cutoff substitution, timestamp and evaluation-window boundaries, evaluation-ID/protocol drift, opaque anchor handling, registration/calibration context substitution, coherently resealed G1 tamper, aggregate privacy, authority locks, non-native and non-finite inputs, resealed gate tamper, deterministic output, and denied external state.

## Compatibility and activation

F0, G0, G1, G2, registration v1, F5, natural-forward artifacts, pack-v5, and pointer-v2 remain unchanged. G3 is unmounted and absent from routes, services, schedulers, Electron, and UI. A separate externally anchored protocol and ADR are required before formal registration v2 can be issued or any future evaluation can be activated.
