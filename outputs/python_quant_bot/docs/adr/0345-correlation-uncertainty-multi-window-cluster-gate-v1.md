# ADR 0345: Correlation uncertainty multi-window cluster gate v1

## Status

Accepted as an unmounted synthetic research candidate. It is not a runtime consumer, current gate, writer, or trading authority.

## Context

The existing matrix geometry gate proves that one point-estimate correlation matrix is positive semidefinite. The existing Fisher-Z uncertainty audit independently classifies each pair as `CONFIRMED_LOW`, `CONFIRMED_HIGH`, `AMBIGUOUS_THRESHOLD`, or `INSUFFICIENT_EFFECTIVE_SAMPLE` for one 60-observation window. The existing multi-window presentation binds stability and budget documents, but it does not make pairwise confidence classifications part of cluster separation.

This leaves a concrete conservative-risk gap: two assets can appear separable in one point estimate even when another preregistered window confirms high absolute correlation, crosses the threshold interval, or lacks enough effective observations. A bridge can also occur across windows, such as A-B in one window and B-C in another, so reviewing each pair or window independently is insufficient.

## Decision

Add `strategy_correlation_uncertainty_multi_window_cluster_gate_v1.py` as a standalone, side-effect-free consumer of the existing strict uncertainty audits.

Preregistration fixes:

1. A sorted symbol order with no duplicates.
2. A complete, non-overlapping, canonical cluster partition.
3. Two to eight unique window identifiers in exact consumer order.
4. The existing uncertainty policy hash and reviewed source hash.
5. The aggregation rule and consumer-first activation sequence.

Evaluation requires a unique expected audit hash for every preregistered window. Each audit must pass the existing exact replay verifier, use the pinned policy, cover every symbol pair exactly once, and carry the same cluster partition. Missing, reordered, duplicated, substituted, or coherently resealed audits fail closed as `UNKNOWN`.

A pair is separable only if every preregistered window says `CONFIRMED_LOW`. `CONFIRMED_HIGH`, `AMBIGUOUS_THRESHOLD`, and `INSUFFICIENT_EFFECTIVE_SAMPLE` all create a conservative dependence edge. Edges are unioned across windows and converted to deterministic connected components. If any edge or resulting component crosses a preregistered cluster, the gate returns `BLOCK`. Dependence wholly contained inside an already grouped cluster may pass this grouping gate, but it grants no downstream authority.

The output contains only audit hash receipts, bounded pair classifications, conservative components, fixed blockers, and all-false operational authority. It does not copy matrix replay, prices, or return series.

## Consumer-first activation order

1. Verify the exact preregistration.
2. Verify every uncertainty audit in preregistered window order.
3. Require every pair in every window.
4. Promote every non-confirmed-low classification to a dependence edge.
5. Union edges across windows and build transitive conservative components.
6. Compare those components with the preregistered partition.
7. Consider an effective-budget consumer only under a separate preregistration and review.
8. Any runtime or current activation remains a distinct authorization decision.

## Adversarial matrix

The synthetic contract covers all-window low separation, one-window confirmed dependence, threshold ambiguity, insufficient effective sample, dependence already contained in one cluster, cross-window bridge transitivity, missing/reordered/reused windows, forged resealed pair classifications, audit-versus-gate partition drift, malformed preregistration, resealed authority promotion, raw-series non-disclosure, and the reviewed upstream source pin.

## Consequences

Highly related assets cannot be counted as separate clusters merely because one window or one point estimate looks benign. The rule is deliberately conservative and may merge more assets than a less defensive estimator. That tradeoff is intentional for this research gate.

The result is synthetic contract evidence only. It does not establish issuer authenticity, window-label authenticity, market validity, strategy performance, paper/live permission, or execution authority.
