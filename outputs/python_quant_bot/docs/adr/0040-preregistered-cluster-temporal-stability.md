# ADR 0040: Preregistered cluster temporal stability

Date: 2026-08-21

## Status

Accepted as a consumer-only synthetic research gate.

## Context

A deterministic synthetic chain produced complete-link PASS and full-window
stability PASS with a full adjusted absolute interval lower bound above 0.75, while
the middle third of the same 60 returns had absolute correlation below 0.75. The
existing full-window gate therefore cannot establish that clustered dependence is
present throughout the preregistered observation interval.

## Decision

Add a temporal stability policy, audit, and gate using three contiguous,
non-overlapping, oldest-to-newest windows of 20 completed daily returns.

Every within-cluster pair and window belongs to one Bonferroni family. Each window
recomputes Pearson correlation, lag-1 effective observations, and a Fisher interval.
Every adjusted absolute lower bound must be at least 0.75 and effective observations
must be at least 12. Sign is intentionally ignored because both positive and negative
dependence invalidate independence; magnitude must remain stable in every window.

Singleton clusters create an empty temporal hypothesis family, so this layer adds no
pair-window blocker. This does not promote an upstream-blocked chain: any source,
complete-link, or full-window stability block is preserved. The gate is consumer-only
and has no report writer or current authority.

## Consequences

- Full-window averaging cannot hide a weak preregistered subwindow.
- Window count, boundaries, family scope, correction, threshold, and effective-N
  method are frozen before any report integration.
- The gate replays completed prices from the verified source audit and never reads
  market data or runs a return backtest.
- The full-window verifier receives the exact complete-link asset explicitly; coherent resealing cannot reconstruct a different upstream chain.
- A future report extension and protocol registration remain separate migrations.
