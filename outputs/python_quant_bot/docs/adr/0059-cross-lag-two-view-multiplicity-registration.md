# ADR 0059: Preregistered raw/residual two-view multiplicity gate

- Status: design accepted; implementation not started.
- Date: 2026-08-21.
- Scope: pure synthetic preregistration and read-only candidate evaluation.
- Authority: descriptive only. No current admission, pointer write, paper/live action, profitability claim, or automatic consumer activation.

## Context

C0 evaluates every preregistered cross-stratum pair at lags `[-2, -1, 1, 2]` and applies a two-sided Bonferroni/Fisher-z bound within one view. F0 evaluates C0 independently on raw and residual views. Looking at both families while retaining the original per-view alpha does not control a single familywise error rate across both views.

The existing generic strategy-correlation multiplicity registration covers cross-cluster pairs only. It does not bind raw/residual view count, cross-lag family, F0 residual replay, or the F0/F1 contracts. It must not be reused by alias.

C0 full output retains correlation, effective sample size, lag, pair identity, and adjusted lower for every test. F0 intentionally projects only aggregate raw/residual summaries, so a downstream F1 receipt cannot recompute a two-view adjustment.

## Pure synthetic gap evidence

### Family inflation

- Per-view family size: 4 tests for one cross-stratum pair and four fixed lags.
- Two-view family size: 8 tests.
- At correlation `0.9185` and effective sample size `20`, the per-view four-test adjusted absolute lower is `0.750266889215`, which reaches the fixed `0.75` dependence threshold.
- Under the preregistered eight-test two-view family, the same input produces `0.724078648693`, below the threshold.
- If two independent families each operate at family alpha 0.05, their combined error probability is `0.0975`; the union bound is `0.10`.

Therefore separate per-view correction cannot be presented as a globally registered two-view family.

### Residual replay bridge

A deterministic common-factor-only fixture proved that candidate residual rows can be supplied without making them public and can be bound to F0 exactly:

- F0 residual input hash: `709b4fbad5ff6dfeeda9eae289d5b881a927677ec2e98f3d1fbb58cc98c93f16`.
- Raw C0 evaluation hash: `d9e4896a5442106cb064c96b56e08ef0294381e7639fba97782d1ef242e2277f`.
- Residual C0 evaluation hash: `1c752b1c1902214a08ea0270810f99beb17b730f2bc634dc1739b67f2d914b20`.
- Raw and residual full C0 documents each contain four lag results.
- F0 public raw/residual projections contain no lag results.

The strict canonical hash of the supplied residual rows matched F0's sealed `residual_input_hash`, and both full C0 documents exactly verified against their respective rows.

## Decision

Add a preregistration contract and a separate pure two-view evaluation contract. Freeze C0, F0-v1, F0-v2, F1-v1, and F2 unchanged.

## Registration contract

- Module: `exchange_terminal/services/strategy_correlation_cross_lag_two_view_multiplicity_registration.py`.
- Schema: `strategy-correlation-cross-lag-two-view-multiplicity-registration-candidate-v1`.
- Static fingerprint: `20260822-cross-lag-two-view-multiplicity-registration-1`.
- Hash field: `registration_hash`.
- Views: exact ordered list `RAW`, `RESIDUAL`.
- Lags: exact ordered list `-2`, `-1`, `1`, `2`.
- Family alpha: canonical decimal text `0.05`.
- Dependence threshold: canonical decimal text `0.75`.
- Method: `BONFERRONI_TWO_SIDED_FWER_RAW_RESIDUAL_V1`.

The builder accepts only preregistered strata and the expected stratum-assignment hash. It does not accept aligned observations, returns, factor rows, residual rows, evaluations, clocks, or runtime state.

It strictly derives and seals:

- stratum-assignment hash;
- sorted identity-order hash without exposing identities;
- cross-stratum pair count;
- lag count;
- per-view test count = pair count times lag count;
- view count = 2;
- global test count = per-view test count times view count;
- fixed alpha, threshold, method, schemas, fingerprint, and locked authority.

`registration_built_from_pre_evaluation_inputs=true` is a structural fact. `registration_timing_attested=false` remains false because process ordering alone is not an external temporal receipt.

## Two-view gate contract

- Module: `exchange_terminal/services/strategy_correlation_cross_lag_two_view_multiplicity_gate.py`.
- Schema: `strategy-correlation-cross-lag-two-view-multiplicity-gate-candidate-v1`.
- Static fingerprint: `20260822-cross-lag-two-view-multiplicity-gate-1`.
- Hash field: `evaluation_hash`.

Inputs:

- exact two-view registration and expected registration hash;
- exact F0-v2 diagnostic and expected diagnostic hash;
- preregistered strata, raw aligned observations, residualization registration, factor observations, and their expected hashes;
- candidate residual aligned observations and expected F0 residual-input hash.

Evaluation order:

1. Verify registration from preregistered strata only.
2. Exactly verify F0-v2 against the complete F0 context.
3. Require the strict canonical hash of candidate residual rows to equal both the expected residual-input hash and F0-v2 `residual_input_hash`.
4. Evaluate and exactly verify C0 on raw rows and residual rows.
5. Require the full raw and residual C0 evaluation hashes to equal F0-v2 nested source hashes.
6. Require exact registered view, lag, pair, per-view-test, and global-test counts.
7. Recompute every Fisher-z lower bound using family alpha divided across the single registered raw+residual family.
8. Seal only aggregate per-view and combined summaries plus provenance hashes. Do not expose residual rows, identities, returns, or pair/lag results.

## Statistical formula

For absolute correlation `r`, effective sample size `n_eff`, global test count `m`, and family alpha `alpha`:

- `z = atanh(abs(r))`.
- `se = 1 / sqrt(n_eff - 3)`.
- `z_critical = NormalDist().inv_cdf(1 - alpha / (2 * m))`.
- `lower = tanh(max(0, z - z_critical * se))`.

The implementation uses the same fixed C0 minimum effective sample, correlation threshold, decimal-text normalization, and two-sided family semantics. A contract test must reproduce every source C0 lower when `m` equals the registered per-view count before using the global count.

No p-value is invented or inferred from the aggregate F0 projection.

## Monotonic source-block rule

Global recalibration is descriptive and can never relax an exact C0 or F0 source BLOCK.

- `global_recalibrated_decision` reports the combined-family calculation.
- `gate_decision` is BLOCK if raw C0, residual C0, F0 diagnostic, or global recalibration is BLOCK.
- If a source BLOCK would become non-dependent under the larger family, add `SOURCE_C0_BLOCK_PRESERVED_AFTER_GLOBAL_RECALIBRATION`.
- `source_block_preserved=true` whenever any exact source BLOCK exists.
- A global PASS means only that this candidate combined family detected no threshold exceedance. It does not prove independence.

This asymmetry prevents multiplicity changes from erasing previously sealed safety blockers.

## Aggregate output

Observed output contains:

- registration, F0-v2, residual-input, raw C0, and residual C0 hashes;
- exact family alpha, method, threshold, views, lags, pair count, and test counts;
- raw and residual aggregate source decisions/counts;
- raw and residual globally recalibrated dependent counts and maximum adjusted lower;
- combined global dependent count and recalibrated decision;
- monotonic gate decision, reason, blockers, maturity, facts, locked authority, schema, fingerprint, and evaluation hash;
- a strict hash of the private recalculated test ledger, not the ledger itself.

UNKNOWN output is fixed, aggregate-only, authority-locked, and exactly replayable. Caller-controlled text is never reflected.

## Locked authority

Only `descriptive_only` is true. At minimum these remain false:

- `registration_timing_attested`
- `factor_calibration_attested`
- `sequence_timing_attested`
- `strata_timing_attested`
- `global_independence_proven`
- `raw_independence_proven`
- `residual_independence_proven`
- `candidate_activation_allowed`
- `current_admission_allowed`
- `current_pointer_written`
- `paper_authorized`
- `live_order_allowed`
- `profitability_claim_allowed`

The gate may set the non-authority fact `global_two_view_multiplicity_registered=true` only after exact registration and family replay succeed.

## Consumer-first versioning

1. Freeze this ADR and synthetic evidence.
2. Implement and validate the preregistration builder/verifier using strata-only inputs.
3. Implement and validate the two-view gate with the residual hash bridge and exact dual C0 replay.
4. Add a read-only aggregate F3 consumer if needed.
5. Keep F1-v1 immutable. Any consumer that changes `global_two_view_multiplicity_registered` must be a new `strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v2` contract consuming exact F0-v2 plus F3.
6. Keep the F2 envelope/model immutable. A future presentation must use a new envelope/model version and remain unmounted first.
7. Register targeted tests and syntax in lean; run list/dry-run without receipts or fresh execution.
8. Synchronize the three baseline documents.
9. Do not modify current pointers, scheduled evidence, server routes, app.js, or mounted UI.

## Adversarial matrix

| ID | Case | Required result |
| --- | --- | --- |
| F3-01 | Valid strata-only registration | Exact pair/view/lag/global family counts |
| F3-02 | Registration API receives no rows or returns | Structural pre-evaluation fact only |
| F3-03 | Invalid, subclass, duplicate, or single-stratum mapping | Fixed UNKNOWN registration |
| F3-04 | Expected strata or registration hash mismatch | Exact verification false |
| F3-05 | Critical `0.9185`, `n_eff=20` fixture | Four-test lower above threshold; eight-test lower below |
| F3-06 | Common-factor-only F0 fixture | Raw source BLOCK preserved; global result descriptive |
| F3-07 | True residual-lag fixture | Raw/residual source BLOCK preserved |
| F3-08 | Raw PASS / residual PASS fixture | Candidate global PASS; no independence authority |
| F3-09 | Suppression fixture | Residual source BLOCK preserved |
| F3-10 | Residual row hash mismatch | Fixed UNKNOWN gate |
| F3-11 | Removed, duplicated, reordered, or extra residual row | Fixed UNKNOWN gate |
| F3-12 | Raw row, strata, registration, factor, or expected-hash mismatch | Fixed UNKNOWN gate |
| F3-13 | F0-v1 or malformed F0-v2 supplied | Fixed UNKNOWN gate |
| F3-14 | F0 nested raw/residual evaluation hash mismatch | Fixed UNKNOWN gate |
| F3-15 | View order, lag family, or pair count drift | Exact verification false |
| F3-16 | Per-view/global test-count drift | Exact verification false |
| F3-17 | Alpha, threshold, or correction-method drift | Exact verification false |
| F3-18 | Formula parity at per-view family count | Reproduce every source C0 adjusted lower |
| F3-19 | Pseudo-boolean, subclass container, non-finite or unsafe numeric value | Fixed UNKNOWN/false |
| F3-20 | Added authority alias or true permission | Exact verification false |
| F3-21 | Re-sealed registration or gate metric/hash/blocker tamper | Exact verification false |
| F3-22 | Observation, identity, return, beta, factor, residual, or lag-result leak | Test failure |
| F3-23 | File, socket, SQLite, time, random, or UUID use | Test failure |
| F3-24 | Runtime/server/CLI/Electron/UI source reference | Must remain zero before activation |

## Activation gates

Implementation is not activation. F3 remains candidate-only until an external temporal receipt attests registration before evaluation, factor calibration is separately attested, sequence/strata timing is attested, a versioned consumer closes, independent adversarial review passes, and explicit authorization is granted. None of those conditions authorizes paper/live trading.

The natural-forward chain remains unchanged: `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`, and pointer-v2 fields/hash semantics remain untouched and are not reissued.

## Consequences

- Raw/residual multiplicity becomes an explicit preregistered family rather than an implied conjunction of two per-view gates.
- F0 residual rows remain private but are cryptographically bound and replayable for the gate.
- C0 and F0 contracts remain immutable.
- Existing source BLOCK decisions remain monotonic.
- No return backtest or new profitability number is generated.

## F3 implementation closure: unmounted candidate

This section supersedes the earlier design-stage implementation status. The accepted registration and gate are now implemented as candidate-only, unmounted contracts:

- registration schema: `strategy-correlation-cross-lag-two-view-multiplicity-registration-candidate-v1`
- registration fingerprint: `20260822-cross-lag-two-view-multiplicity-registration-1`
- gate schema: `strategy-correlation-cross-lag-two-view-multiplicity-gate-candidate-v1`
- gate fingerprint: `20260822-cross-lag-two-view-multiplicity-gate-1`
- correction: `BONFERRONI_TWO_SIDED_FWER_RAW_RESIDUAL_V1`
- exact views: `RAW`, `RESIDUAL`; exact lags: `-2`, `-1`, `1`, `2`
- family alpha: `0.05`; dependence threshold: `0.75`

The gate verifies the registration, F0-v2 diagnostic, residual-input hash, and exact dual C0 replay hashes. It then recomputes each lag statistic from the hash-bound raw or residual observation rows with C0's pre-formatting shift, Pearson, effective-sample-size, Fisher-z, and decimal helpers. It never derives a new lower bound from the rounded public C0 correlation. Per-view parity must still match the sealed C0 projection exactly before the global two-view family is evaluated.

Only aggregate view summaries and a private recalculation-ledger hash are public. Identity-level rows and full-precision correlations are not projected. Global recalibration is monotone: it can add a block but cannot relax a source C0 or F0 block.

Synthetic critical-point evidence remains descriptive: at `r=0.9185`, `n_eff=20`, the four-test lower bound is `0.750266889215`, while the preregistered eight-test lower bound is `0.724078648693`. Two separately tested 5 percent families would otherwise have a combined false-positive probability of `0.0975` under independence and a union-bound ceiling of `0.10`; neither is acceptable as independent evidence.

Validation evidence:

- registration targeted contracts: `15/15 PASS`
- gate targeted chain: `35/35 PASS`
- independent synthetic probe: OBSERVED, source-BLOCK preservation, tamper-to-UNKNOWN, determinism, aggregate-only projection, and locked authority all PASS
- C0 -> F0-v1 -> F0-v2 -> registration -> F3 matrix: `152/152 PASS`
- explicit activation-path references: `0`

This is not current activation. F1-v1 and F2 remain frozen, the natural-forward single-look chain is unchanged, legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 is neither changed nor automatically reissued. No backtest return, profitability claim, paper authority, or live authority follows from this candidate.
