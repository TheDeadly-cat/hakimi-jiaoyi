# ADR0266: Unmounted common-observation basis card-v10

- Status: accepted as an unmounted, descriptor-only consumer candidate
- Date: 2026-08-23
- Authority: research-only, descriptive-only, fail-closed

## Context

ADR0265 introduced an unregistered HTTP candidate-v10 that projects presentation-v10, including the preregistered common-observation basis aggregate. Card-v9 is intentionally pinned to candidate-v9 and has no common-observation contract.

A pure synthetic cross-runtime proof fed a sealed `KNOWN_BLOCKED` candidate-v10 response containing a common sample count into card-v9. Card-v9 rejected the response, returned `UNKNOWN`, hid common, edge, window, metric, signal, and dimension aggregates, and did not access the DOM (`5/5`). This is the required fail-closed gap, not a reason to widen card-v9.

## Decision

Add a separate card-v10, scoped stylesheet, descriptor-only consumer fixture, and adversarial Node contract. Do not modify card-v9 or any mounted application surface.

Card-v10:

- accepts only the exact sealed candidate-v10 response schema and static fingerprint;
- pins presentation-v10, candidate-v10, and strict-canonical implementation hashes;
- validates exact authority, facts, lineage, payload, stage, risk, multi-window, edge, and common-observation shapes;
- cross-checks edge pair coverage, cluster partition hashes, presentation hashes, and common pair-count agreement;
- treats malformed, substituted, unknown, promoted, or contradictory input as `UNKNOWN`;
- exposes only bounded aggregates and short provenance hashes;
- labels the common basis as `DECLARATION ONLY` and `RAW SAMPLES NOT RECOMPUTED`;
- keeps `SOURCE -> GAP -> MATURITY -> PERMISSION`, with maturity `CANDIDATE_ONLY` and permission `UNAUTHORIZED`;
- contains no DOM lookup, mount function, route, network, storage, timer, or execution call.

The consumer fixture generates sealed static markup metadata only. It declares its stylesheet but does not load it, exposes no selector or DOM target, and pins mount mode to `UNMOUNTED`.

## Adversarial matrix

1. Exact locally clear basis remains `LOCAL CLEAR / OUTER BLOCK`.
2. A common-observation basis block remains visible without authority promotion.
3. An edge-uncertainty block survives the additional basis layer.
4. Exact `UNKNOWN` hides every partial aggregate.
5. A substituted response hash fails closed.
6. Extra common-observation fields fail after resealing.
7. Contradictory pair-count agreement fails.
8. Raw-sample recomputation or provenance promotion fails.
9. Forged authority or payload `PASS` fails.
10. Adversarial labels are HTML-escaped.
11. Language remains neutral and stage order remains fixed.
12. The fixture remains sealed, implementation-pinned, descriptor-only, and unmounted.

## Consumer-first activation order

1. Keep candidate-v10 unregistered.
2. Keep card-v10 and its fixture unmounted.
3. If separately authorized, perform browser visual review without route or current admission.
4. Review route registration, mount, and current admission as separate future decisions.

No step is automatically activated by this ADR.

## Consequences and authority boundary

This closes the first JavaScript consumer gap for the common-observation basis without changing runtime behavior. It does not recompute raw observations, prove market truth, prove profitability, authorize paper/live activity, alter the natural-forward evidence chain, promote legacy pack-v5, or reissue pointer-v2. No browser review is claimed.
