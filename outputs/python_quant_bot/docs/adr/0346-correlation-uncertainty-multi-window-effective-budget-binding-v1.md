# ADR 0346: Correlation uncertainty multi-window effective-budget binding v1

## Status

Accepted as an unmounted synthetic research binding. It is not current, registered at runtime, or authorized for paper/live execution.

## Context

ADR 0345 conservatively unions every pair that is not `CONFIRMED_LOW` in every preregistered window. The existing effective-budget v3 still computes cluster and strata concentration from the original complete-link partition. Without an explicit prerequisite, a geometry-valid budget document can therefore remain exact while a later uncertainty window shows that two preregistered clusters are plausibly dependent.

Changing the partition dynamically would violate preregistration and would silently alter every downstream strata mapping. The safe consumer behavior is a veto followed by explicit repreregistration, not post-hoc reclustering.

## Decision

Add `strategy_correlation_uncertainty_multi_window_effective_bet_budget_binding_v1.py` as a pure, unmounted binding between ADR 0345 and the existing geometry-bound effective-budget evaluation.

The binding preregistration requires both upstream preregistrations to verify exactly and requires their symbol order and cluster partition to match. It pins both source hashes, both contract hashes, the shared cluster-preregistration hash, the ADR 0345 window-order hash, and the activation sequence.

For a risk-increasing request, the evaluation order is mandatory:

1. Verify the binding preregistration.
2. Verify the exact ADR 0345 gate and all of its window audits.
3. If ADR 0345 is `BLOCK`, return `BLOCK` before invoking the budget verifier and require repreregistration.
4. Only after ADR 0345 is `PASS`, verify the exact geometry-bound effective-budget evaluation.
5. Preserve either the verified budget pass or its verified budget block as research evidence.

For a request marked as risk reduction, an exact ADR 0345 document is still required. An ADR 0345 `BLOCK` may be traversed only when the exact budget evaluation independently rebuilds to `status=PASS` and `decision=RISK_REDUCTION_PATH`. A caller-supplied boolean alone cannot enable this exception.

The binding does not recompute correlations, recluster symbols, alter strata, call a writer, or mount a consumer. It emits ADR 0345 hash/count receipts plus the already verified budget v3 document. It does not embed window audits, matrix replay, prices, or return series.

## Consumer-first activation order

1. Exact binding preregistration.
2. Exact multi-window uncertainty cluster gate.
3. Risk-increase veto on cross-cluster dependence.
4. Exact geometry-bound effective-budget verification.
5. Exact risk-reduction decision for the reduction-only exception.
6. Permanent research-only authority lock.

Any presentation, HTTP, runtime, current, writer, paper, or live integration requires a separate preregistration and authorization decision.

## Adversarial matrix

The synthetic integration contract covers shared-partition binding, all-window-low release, risk-increase short-circuit before budget verification, coherently resealed uncertainty promotion, budget-evaluation authority tamper, preservation of a verified budget block, the exact risk-reduction exception, partition drift, verification-context expansion, resealed output promotion, verifier ordering, source pins, raw-window non-disclosure, and all-false operational authority.

## Consequences

An asset pair or cross-window bridge discovered by ADR 0345 can no longer flow into the research budget as separate preregistered tickets. A changed dependence structure requires a new preregistration. Risk reduction remains possible only through the existing exact reduction decision.

This is synthetic contract evidence only. It is not market validation, strategy performance evidence, issuer authenticity, public-release authorization, or trading permission.
