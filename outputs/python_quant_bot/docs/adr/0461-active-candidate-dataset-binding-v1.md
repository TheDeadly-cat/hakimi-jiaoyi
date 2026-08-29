# ADR 0461: Active candidate dataset binding v1

- Status: Accepted
- Date: 2026-08-25
- Scope: Active research candidate registry production and loading

## Context

The active registry stores `dataset_hash` and `dataset_last`, but the loader did
not compare those fields with the bound frozen candidate. In an isolated
synthetic activation, both the generic registry verifier and the full loader
returned `PASS` after the dataset fields were changed and the unkeyed registry
hash was recomputed.

## Decision

Introduce `active-candidate-dataset-binding-v1` as a compatible v3
sub-contract:

1. New active registries declare the dataset-binding version.
2. The loader rebuilds `dataset_hash` and `dataset_last` from the exact candidate
   file already bound by filename, file SHA-256, and candidate hash.
3. Any registry/candidate dataset mismatch blocks the complete load.
4. Unknown non-empty sub-contract versions block generic registry verification.
5. Legacy v3 registries without the new version field remain readable only when
   their existing dataset fields exactly match the frozen candidate.

The outer `active-portfolio-candidate-v3` version remains unchanged to avoid an
unnecessary migration. Existing registry hashes are not rewritten or reissued.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| New isolated activation | Declares binding v1 and loads PASS |
| Resealed dataset hash | Complete load BLOCK |
| Resealed dataset last date | Complete load BLOCK |
| Matching legacy v3 without sub-contract field | PASS |
| Unknown sub-contract version | Generic verification and load BLOCK |

## Boundaries

- Tests create candidates and registries only in isolated temporary directories.
- No user registry or formal report directory is read or modified.
- No market task, backtest, service, browser, scheduler, runtime database, paper
  order, or live order is started.
- Active research remains research-only; paper/live remain unauthorized.
