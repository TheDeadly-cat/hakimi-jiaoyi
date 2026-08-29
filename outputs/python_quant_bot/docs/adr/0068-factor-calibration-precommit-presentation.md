# ADR 0068: Detached H1 precommit and stability presentation

- Status: Accepted as an unmounted candidate
- Date: 2026-08-27
- Scope: Research-only factor calibration evidence presentation

## Context

The G2 calibration presentation consumes G1 and intentionally knows nothing about the later H0 and H1 contracts. A pure synthetic audit confirmed that a verified G2 envelope contains no H1 gate hash, stability-gate hash, drift threshold, drift result, or aggregate instability count. Passing an H1 gate to G2 closes as unsupported.

H1 already emits a strict, aggregate-only, versioned decision receipt with explicit missing, unsupported, invalid, block, and local-binding states. Adding another report consumer would duplicate H1 state mapping without introducing a new trust boundary.

## Decision

Add a separately versioned Python presentation envelope that directly invokes the official H1 verifier over the complete G3, H0, declaration, report, replay, registration, and calibration-observation context. The envelope carries an exact deep copy of the verified H1 gate and only its aggregate provenance hashes.

Add a detached browser model and card. The browser verifies strict canonical hashes, exact schemas, aggregate privacy, cross-links, locked authority, and semantic state shape. It does not replay OLS, fold partitioning, source verifiers, or precommit timing rules.

The visual signature is a four-segment contiguous-fold instrument rail. It truthfully shows that four count folds exist while keeping identity and fold-beta ledgers private. The card preserves SOURCE, GAP, MATURITY, and PERMISSION order and uses no success-green, READY language, trading controls, storage, network calls, or mount API.

## Consumer-first activation order

1. Keep H1, the envelope, and the card unmounted.
2. Validate Python source semantics and browser transport semantics independently.
3. Prove real Python-to-Node parity for guarded, blocked, missing, not-supplied, and tampered states.
4. Add any future route or UI mount only through a separate activation ADR and current-chain decision.

## Consequences

`BOUND_LOCAL_ONLY_STABILITY_GUARDED` remains a local candidate description. It is not beta-stability proof, external timestamp attestation, formal registration issuance, future-evaluation permission, profitability evidence, paper authorization, or live authority.

G2, G3-v1, H0, H1, the natural-forward chain, legacy pack-v5 UNKNOWN behavior, and pointer-v2 fields, hash contract, and no-auto-reissue behavior remain unchanged.
