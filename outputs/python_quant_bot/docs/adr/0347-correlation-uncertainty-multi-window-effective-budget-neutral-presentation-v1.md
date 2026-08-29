# ADR 0347: Correlation uncertainty multi-window effective-budget neutral presentation v1

## Status

Accepted as an unmounted static presentation candidate. It is not connected to `app.js`, CSS, DOM, HTTP, runtime assets, or current pointers.

## Context

ADR 0345 supplies conservative multi-window dependence components. ADR 0346 prevents a risk-increasing effective-budget evaluation from running when those components cross the preregistered cluster partition. Their Python documents contain detailed audit and budget structures that should not be copied directly into a frontend model.

The terminal needs a bounded, neutral projection that distinguishes a cross-cluster veto, a reduction-only path, a verified research-budget contract, and a verified budget block while preserving the permanent permission boundary.

## Decision

Add `strategy_correlation_uncertainty_multi_window_effective_budget_neutral_presentation_v1.js` as a UMD module with a colocated pure Node contract test.

The presenter accepts exactly two bounded plain-JSON documents:

1. `uncertainty_cluster_gate`
2. `uncertainty_budget_binding`

The documents are limited to depth 24, 65,536 values, 256 object keys, 4,096 array entries, and 8,192 characters per string. Cycles, accessors, symbols, custom prototypes, sparse arrays, non-finite numbers, prototype-sensitive keys, and additional top-level documents fail closed.

The presenter pins the ADR 0345 and ADR 0346 schema versions, static fingerprints, contract hashes, and reviewed source hashes. It requires the ADR 0346 embedded gate hash, status, dependence-edge count, cross-cluster count, and component count to match ADR 0345 exactly. Any true authority-like boolean or explicit authority-promotion marker changes the projection to `UNKNOWN`.

Backend status and decision strings are not passed through to UI consumers. They are normalized to one of:

1. `CROSS_CLUSTER_DEPENDENCE_VETO`
2. `RISK_REDUCTION_ONLY`
3. `RESEARCH_BUDGET_CONTRACT_OBSERVED`
4. `RESEARCH_BUDGET_BLOCK_OBSERVED`
5. `DOWNSTREAM_BUDGET_CHAIN_BLOCK`
6. `UNKNOWN`

Even known local evidence has top-level status `BLOCKED`, because current, DOM, HTTP, runtime, writer, paper, and live authority remain false. The fixed axis order is:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

`SOURCE` contains only pinned contract/source hashes, embedded receipt hashes, local document hashes, and a local document-set hash. Metrics are bounded counts only. Window receipts, pair assessments, trusted budget documents, prices, and return series are not embedded.

## Consumer-first activation order

1. Keep the presenter unmounted and validate only pure synthetic JSON under Node.
2. Independently review cross-binding, normalization, non-disclosure, and authority-lock behavior.
3. Define a separately preregistered host adapter if a real static consumer is still desired.
4. Review accessibility and browser rendering before any DOM mount.
5. Any app registration, CSS change, current-pointer change, or runtime activation requires a distinct authorization decision.

## Adversarial matrix

The colocated contract covers the research-budget view, cross-cluster veto, exact reduction-only normalization, verified budget block, gate-hash substitution, count substitution, contract drift, nested authority promotion, cycles, accessors, custom prototypes, oversized strings, raw-document non-disclosure, fixed authority, deterministic sealing, resealed output promotion, promotional-word absence, and absence of DOM or network operations.

## Consequences

The frontend now has a bounded model that can explain why correlated assets were grouped or vetoed without exposing research inputs or implying execution authority. No visual, browser, accessibility, market, or runtime claim follows from this unmounted contract.

This synthetic presentation evidence is not issuer authenticity, market validation, strategy performance evidence, public-release authorization, or trading permission.
