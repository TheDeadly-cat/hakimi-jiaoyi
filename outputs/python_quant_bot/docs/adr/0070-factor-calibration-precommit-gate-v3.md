# ADR 0070: Precommit gate v3 composes beta and residual-energy guards

- Status: Accepted as an unmounted candidate
- Date: 2026-08-29
- Scope: Future-only factor residualization precommit governance

## Context

A pure synthetic path produces G3 BOUND_LOCAL_ONLY, H0 STABLE_CANDIDATE, H1 BOUND_LOCAL_ONLY_STABILITY_GUARDED, and I0 BLOCK for residual-energy instability. H1 and I0 share exact H0, replay, registration, and calibration-observation hashes, but H1-v2 contains no I0 hash or decision. A downstream consumer could therefore cite H1 while omitting a verified I0 block.

## Decision

Add a separately versioned precommit v3 gate. It invokes the official H1-v2 and I0 verifiers over one complete G3, H0, declaration, report, replay, registration, and calibration-observation context. It cross-binds H0, replay, registration, observation, and fold-count identities.

The positive state is `BOUND_LOCAL_ONLY_DUAL_STABILITY_GUARDED`. It requires H1 BOUND_LOCAL_ONLY_STABILITY_GUARDED and I0 RESIDUAL_ENERGY_STABLE_CANDIDATE. H1 BLOCK or I0 BLOCK remains BLOCK. Missing, unsupported, invalid, substituted, or coherently tampered sources close UNKNOWN.

V3 does not recompute OLS, fold beta drift, residual energy, precommit timing, or source semantics. It owns only monotone composition, aggregate projection, blocker deduplication, and a new canonical receipt.

## Consequences

Dual stability guarded remains a local candidate description. It is not beta or residual stationarity proof, external timing attestation, formal registration issuance, future-performance evidence, profitability evidence, paper authorization, or live authority.

H1-v2, I0, H2, the natural-forward chain, legacy pack-v5 UNKNOWN behavior, and pointer-v2 fields, hash contract, and no-auto-reissue behavior remain frozen. V3 has no issuer, route, scheduler, pointer, Electron bridge, presentation, mount, or activation decision.
