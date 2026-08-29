# ADR 0069: Candidate residual-energy temporal stability gate

- Status: Accepted as an unmounted candidate
- Date: 2026-08-28
- Scope: Calibration-only factor residual diagnostics

## Context

A pure synthetic calibration path preserves exact full-window registered betas and exact beta values in all four contiguous folds. G0 is MATCH, H0 is STABLE_CANDIDATE with zero beta drift, and H1 is BOUND_LOCAL_ONLY_STABILITY_GUARDED. Nevertheless, residual mean-square energy can be small in the first folds and orders of magnitude larger in later folds. H0 and H1 expose no equivalent residual-energy fact.

## Decision

Add I0 as a parallel, unmounted candidate gate that consumes and replays the official H0 verifier over the complete replay, registration, and calibration-observation context. H0 remains frozen. I0 owns only the new residual-energy statistic and its projection.

For each registered identity, calculate residuals from the registered beta and factor return. Partition observations into the same version-fixed four contiguous count folds with at least five rows per fold. Calculate full-window and fold residual MSE, then calculate each fold's absolute MSE deviation divided by full-window MSE. If full-window residual MSE is zero, all fold residual energies are necessarily zero and dispersion is defined as zero.

The maximum allowed normalized residual-energy dispersion is fixed at 0.75 inclusive. The threshold is a candidate governance guardrail selected without a return ranking, parameter search, or profitability comparison. Any change requires a new schema and fingerprint.

H0 BLOCK remains BLOCK. A verified H0 STABLE_CANDIDATE with any identity above the I0 threshold becomes BLOCK. Public output contains only fold-size bounds, maximum dispersion, unstable-identity count, zero-residual-identity count, source hashes, and a private residual-energy ledger hash.

## Consequences

RESIDUAL_ENERGY_STABLE_CANDIDATE means only that this diagnostic found no violation under the fixed threshold. It is not residual stationarity proof, factor correctness, causality, future-performance evidence, profitability evidence, paper authorization, or live authority.

I0 has no route, scheduler, pointer, Electron bridge, presentation, mount, or activation decision. G0, H0, H1, H2, the natural-forward chain, legacy pack-v5 UNKNOWN behavior, and pointer-v2 fields, hash contract, and no-auto-reissue behavior remain unchanged.
