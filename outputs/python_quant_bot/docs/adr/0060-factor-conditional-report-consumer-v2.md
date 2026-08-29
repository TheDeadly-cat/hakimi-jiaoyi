# ADR 0060: Factor-Conditional Report Consumer v2

## Status

Accepted for an unmounted candidate implementation. This ADR does not authorize
current activation, a server route, a pointer write, a scheduler, paper trading,
or live trading.

## Context

The v1 factor-conditional report consumer verifies F0-v2 and projects a neutral
SOURCE -> GAP -> MATURITY -> PERMISSION receipt. It predates the preregistered
RAW/RESIDUAL global multiplicity family. A synthetic call proves that v1 can
produce and verify an OBSERVED receipt without receiving a family registration,
an F3 gate, or an expected F3 hash.

F3 closes the statistical family gap, but its candidate gate is intentionally
unmounted. Modifying v1 in place would create compatibility drift for F2 and
would make old verification hashes ambiguous. The next consumer must therefore
be versioned and must compose the frozen v1 receipt with the F3 gate.

## Decision

Add an unmounted v2 verification consumer with these identities:

- schema: `strategy-correlation-cross-lag-factor-conditional-report-consumer-verification-v2`
- fingerprint: `20260822-cross-lag-factor-conditional-report-consumer-2`
- source A: exact F1-v1 receipt plus its expected verification hash
- source B: exact F3 gate plus its expected evaluation hash
- shared source: exact F0-v2 diagnostic and all contexts needed to replay F1
  and F3 independently

The consumer accepts the family registration, preregistered strata, raw rows,
candidate residual rows, residualization registration, and factor observations.
It also requires expected hashes for strata, residualization registration,
factor observations, family registration, F0-v2, residual input, F1-v1, and F3.

## Verification order

1. Validate every expected hash as an exact SHA-256 string.
2. Require native dictionaries for F1-v1, F3, family registration, and F0-v2.
3. Require the embedded F1 and F3 hashes to equal the expected hashes.
4. Rebuild and exactly verify F1-v1 from F0-v2 and the raw/factor contexts.
5. Rebuild and exactly verify F3 from both views and all registrations.
6. Cross-bind F0, raw C0, residual C0, residual-input, factor, residualization,
   family, strata, and identity-order hashes across both verified sources.
7. Project only aggregate F3 family fields and the two source artifact hashes.
8. Seal the exact v2 document with `verification_hash`.

Any failure produces a deterministic UNKNOWN document. A verifier rebuilds the
entire v2 document and compares the strict JSON contract exactly.

## Projection

The OBSERVED projection contains:

- source F1 verification hash and source F3 evaluation hash;
- F0, family, residual-input, raw C0, and residual C0 hashes;
- F1 report/gap/maturity states for provenance;
- correction method, alpha, threshold, view/lag identities, family counts,
  global dependent count, global recalibrated decision, and aggregate view
  summaries from F3;
- a monotone GAP state derived from the verified F3 decision;
- merged blockers, calibrated facts, and a permanently locked authority map.

Identity-level lag rows, full-precision values, and the private F3 recalculation
ledger are not projected. The private ledger remains represented only by its F3
hash-bound evaluation.

## Blocker composition

The v1 blockers `GLOBAL_TWO_VIEW_MULTIPLICITY_NOT_REGISTERED` and
`FACTOR_CONDITIONAL_REPORT_NOT_ACTIVATED` are superseded at this versioned
boundary. They are not copied into v2. F3 timing, factor-calibration, F3
not-activated, and source-dependence blockers remain. v2 adds
`FACTOR_CONDITIONAL_REPORT_V2_NOT_ACTIVATED`.

Removing the stale v1 registration blocker is not a permission relaxation. The
F3 registration and gate must verify first, and all execution/current authority
remains false.

## Monotonic decisions

- F3 `BLOCK` -> v2 `GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED`.
- F3 `PASS` -> v2 `NO_GLOBAL_TWO_VIEW_DEPENDENCE_OBSERVED`, but maturity remains
  candidate and not time-attested.
- F1 or F3 `UNKNOWN`, any verification failure, or any cross-link mismatch ->
  v2 `UNKNOWN`.
- No source block can become a permission or activation signal.

## Adversarial matrix

The candidate implementation must cover at least:

1. pass/pass dual replay;
2. suppression/source-BLOCK preservation;
3. exact schema and fingerprint;
4. F1 expected-hash substitution;
5. F3 expected-hash substitution;
6. F0 expected-hash substitution;
7. family expected-hash substitution;
8. residual-input expected-hash substitution;
9. strata expected-hash substitution;
10. factor expected-hash substitution;
11. residualization-registration expected-hash substitution;
12. F1 field tamper and coherent reseal;
13. F3 field tamper and coherent reseal;
14. F0 or family downgrade/tamper;
15. residual-row removal;
16. residual-row duplication;
17. residual-row reorder;
18. residual-row extension;
19. independently valid but cross-mismatched source artifacts;
20. v2 metric/blocker/fact/authority tamper and coherent reseal;
21. non-native mapping subclasses;
22. non-finite documents;
23. deterministic UNKNOWN replay;
24. denied external I/O and nondeterminism.

## Activation order

1. ADR and synthetic gap proof.
2. F4-v2 consumer and exact verifier.
3. Targeted and independent adversarial review.
4. Research lean list/dry-run integration.
5. A future versioned presentation envelope.
6. A future unmounted UI component.
7. Current activation only under a separate decision and evidence review.

Steps 5-7 are not part of this implementation.

## Invariants

- F1-v1 and F2 remain byte-for-byte frozen.
- F3 remains an unmounted candidate.
- The natural-forward single-look chain is unchanged.
- Legacy pack-v5 public reads remain UNKNOWN.
- Pointer-v2 fields and hash contract remain unchanged and are not reissued.
- Backtests or synthetic evidence do not prove profitability.
- Paper and live remain unauthorized; live stays hard locked.

## F4 implementation closure: unmounted v2 consumer

The v2 composition consumer and exact verifier are implemented without modifying F1-v1, F2, or F3. A pure synthetic gap probe first proved that F1-v1 can issue an OBSERVED receipt with no F3 argument or F3 field. A separate bridge then proved that F1 and F3 can be independently replayed from the same source context.

The implemented consumer verifies both artifacts, rebuilds each source through its native verifier, and cross-binds F0, raw C0, residual C0, residual input, factor observations, residualization registration, family registration, strata, and identity-order hashes. The projection contains aggregate F3 view summaries and source hashes only. F1's stale multiplicity-not-registered blocker is superseded only after F3 verifies; all timing, calibration, not-activated, current, paper, live, and profitability restrictions remain.

Validation evidence:

- in-memory compile: `2/2 PASS`
- F4 targeted adversarial contracts: `18/18 PASS`
- independent pass/BLOCK/tamper-UNKNOWN/cross-link/aggregate/authority probe: PASS
- F0 -> F1 -> F3 -> F4 matrix: `190/190 PASS`
- fixed activation-source files scanned: `19`; F4 references: `0`

The research lean profile now lists the F4 contract class and F4 syntax target. No fresh run or receipt mutation is authorized. A future presentation envelope must be separately versioned; no presentation or current activation is part of F4.
