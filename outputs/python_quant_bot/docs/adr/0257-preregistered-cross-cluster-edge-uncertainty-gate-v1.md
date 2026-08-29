# ADR 0257: Preregistered cross-cluster edge uncertainty gate-v1

## Status

Accepted as an isolated, unmounted research-only gate candidate on 2026-08-23.

## Context

The multi-window stratified stability gate-v2 proves that registered windows use
stable cluster partitions and strata topology. It does not receive pairwise
sample counts or uncertainty bounds. A pure synthetic read-only proof passed 5/5:

1. the stable three-window gate-v2 fixture passed;
2. low-sample and high-sample pair evidence were materially different;
3. gate-v2 produced identical outputs because neither evidence set entered its
   call contract;
4. preregistration-v2 and gate-v2 exposed no sample, confidence, or uncertainty
   key;
5. the evaluator exposed no pair-uncertainty parameter.

Therefore a stable partition can still overstate independent bets when a
cross-cluster positive-correlation estimate is sparse or its confidence interval
overlaps the clustering floor. Widening gate-v2 would mix topology stability with
statistical edge uncertainty and invalidate the existing versioned boundary.

## Decision

Add a distinct preregistered cross-cluster edge uncertainty gate-v1.

The preregistration freezes:

- trade identity and cluster-partition hashes;
- a canonical symbol-to-cluster mapping;
- every derived cross-cluster symbol pair;
- a positive-correlation floor in integer micros;
- a one-sided Fisher-z coefficient in integer micros;
- minimum sample count and registration sequence.

The evidence document must be sealed after registration, cross-bind the trade and
partition hashes, have a strictly later sequence, and cover every derived
cross-cluster pair exactly once in canonical order. Missing, extra, same-cluster,
duplicate, reversed, malformed, or spliced pairs fail closed to UNKNOWN without
partial pair results.

For each cross-cluster pair the gate computes:

`tanh(atanh(observed) + z / sqrt(sample_count - 3))`

and rounds the one-sided upper confidence bound to integer correlation micros.
The pair is blocked when:

- observed positive correlation is at or above the frozen floor;
- sample count is below the frozen minimum; or
- the upper confidence bound is at or above the frozen floor.

Only pairs below all three conditions pass. This conservative gate does not claim
that a passing pair is independent; it only says the preregistered positive-edge
uncertainty condition did not block that research component.

## Scope limits

- v1 covers non-negative positive-dependence correlation estimates only.
- It does not validate correlation-matrix positive semidefiniteness.
- It does not estimate correlations or access market data.
- It does not choose symbols, clusters, thresholds, sample windows, or z values.
- It does not handle negative-correlation hedge claims.
- It is not connected to gate-v2, adapter-v7, presentation-v8, HTTP, UI, current,
  paper, or live paths.

Those boundaries require later, separately versioned consumer-first decisions.

## Fail-closed and authority behavior

Unknown source contracts expose no pair results or summary values. Known PASS and
BLOCK documents are sealed and exact-rebuild verifiable. Every output fixes
current, runtime-gate, writer, paper, and live authority to false. Input builders
canonicalize ordering but do not authorize threshold or universe changes after
the externally pinned preregistration hash.

The output records that no historical market data or runtime asset was accessed,
source documents are not embedded, and profitability is not proven.

## Adversarial matrix

The targeted matrix covers high-sample clear pairs, low-sample uncertainty
overlap, observed threshold equality, insufficient samples, missing/extra pairs,
duplicates, source hash and sequence splices, substituted preregistration pins,
invalid numeric types, deterministic source builders, bounded output, input
immutability, and resealed permission promotion.

## Compatibility and authority

- strict canonical implementation pin:
  `cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412`
- gate-v2 remains unchanged at:
  `0756cc0d0338170e80bd2b3672ecd6a65542953e2c0dc92a48c05229e0f7902f`
- natural-forward artifact versions and pointer-v2 remain unchanged;
- legacy pack-v5 public reads remain UNKNOWN/null;
- no output is profitability evidence or trading authorization.

## Consequences

The project gains a narrow statistical guard against counting weakly estimated
cross-cluster edges as independent bets. It also adds one more preregistered input
and conservative block path. That cost is intentional and preferable to hidden
confidence assumptions inside topology or exposure gates.
