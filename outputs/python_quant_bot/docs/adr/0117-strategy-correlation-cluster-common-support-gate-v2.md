# ADR 0117: Strategy correlation-cluster common-support gate v2

## Status

Accepted as an inactive, fail-closed research candidate. It does not replace or activate the v1 gate and is not connected to current reports, selection writers, paper, or live paths.

## Context

The v1 correlation matrix binds a Pearson value and overlap count for every symbol pair. It does not bind which completed daily observations form each overlap or require all pairs to use one listwise-complete index.

A pure synthetic three-symbol example gives every pair 40 observations while assigning each pair a disjoint 40-date set. The global three-way intersection is zero, yet v1 has no common-index hash and passes three singleton clusters when all selection cells pass. Pair counts alone therefore cannot establish that cluster independence was evaluated on comparable observations.

## Decision

Add a versioned common-support matrix and gate:

1. Require one canonical, strictly increasing, unique ISO-date list shared by every symbol pair.
2. Require between 40 and 60 common completed-daily-return observations, matching the existing minimum overlap and lookback bounds.
3. Project only the common observation count and strict-canonical index hash; do not project dates or returns.
4. Build every v1 pair overlap from the same verified common count, then replay the existing v1 topology and cluster-vote gate.
5. Bind the v1 preregistration hash, v2 matrix hash, common-index hash/count, and replayed source gate hash in a sealed v2 output.
6. Fail before the source gate when the common index is missing, malformed, mismatched, under-supported, overlong, unsorted, duplicated, or noncanonical.
7. Keep writer activation, admission, paper, and live false even when the research gate status is PASS.

The common observation policy is `LISTWISE_COMPLETE_COMPLETED_DAILY_RETURNS`.

## Proof boundary

The gate proves that the supplied correlations and one supplied observation-index commitment are contractually bound to a common support set. It does not independently recompute correlations from returns, prove that dates are genuine market sessions, establish data-provider truth, show out-of-sample robustness, or prove profitability.

## Activation order

1. Keep v2 inactive and use only synthetic matrices and date indexes.
2. Add an independently verified correlation-derivation receipt that binds returns to the common index.
3. Review calendar/session and data-provider evidence separately.
4. Require a new migration ADR and explicit authorization before any report writer or selection consumer switches from v1.

No market data, K-line task, backtest, browser, service, scheduler, paper path, or live path is used.

## Validation evidence

1. The targeted v2 contract matrix passes 16/16, and the service and test compile in memory 2/2.
2. An independent public-API matrix passes 15/15. It reproduces the v1 zero-global-common-date gap and rejects index mismatch, too-short and too-long support, unsorted, duplicate, and noncanonical dates, matrix drift, and authority injection.
3. The independent matrix also confirms that v2 preserves the v1 topology, cluster-vote, and coverage blockers after common support is verified.
4. The narrow core correlation-cluster family passes 24/24 across the v1 and v2 TestCase classes. This v2 slice is not part of the provider-identity factor-calibration family, which was intentionally not rerun.
5. The research lean profile lists and dry-runs 15 grouped checks. The v2 TestCase and service source each occur once; executed, completed, and reused counts are zero; runtime mutation, paper, and live flags are false.
6. Eight explicit active entrypoints contain zero v2 module, schema, fingerprint, or policy references. The candidate remains disconnected from current consumers.

Implementation fingerprints:

- Static fingerprint: `20260822-strategy-correlation-cluster-common-support-gate-2`.
- Service SHA-256: `6CF64F044CA3474C8E3E3E26FD14A4A18D3724235A1ECA15DC7D05610D651570`.
- Test SHA-256: `B668A4BB906FB40B6E23D3E2E67275C94256CBAA1025E2618AEAF9FE0B26E481`.

The current natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 fields, hash contract, and no-auto-reissue behavior are unchanged.
