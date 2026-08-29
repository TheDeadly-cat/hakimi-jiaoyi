# ADR 0078: Incremental lag-three residual-order stability gate v3

## Status

Accepted as an unmounted research candidate. It is not wired into precommit, current pointers, API routes, or UI.

## Evidence for the gap

A purely synthetic 40-row, four-fold context was generated from the existing public test fixtures. In every fold, a repeating `+,+,-` residual sequence was projected orthogonally to the registered factor exposure. The maximum factor dot-product rounding residue was `7E-51`.

The complete sealed chain produced replay `MATCH`, beta `STABLE_CANDIDATE`, lag-one `RESIDUAL_ORDER_STABLE_CANDIDATE`, and v2 `RESIDUAL_MULTI_LAG_ORDER_STABLE_CANDIDATE`; the v2 verifier returned true. Its lag-one/two aggregate maximum was approximately `0.36237`, while independently computed lag-three coupling exceeded `0.8` in all four folds and reached approximately `0.99446`.

This evidence demonstrates a coverage gap. It is synthetic evidence only and says nothing about profitability or live behavior.

## Decision

Add a versioned incremental v3 gate that:

- re-verifies the complete v2 source context before evaluating anything new;
- requires the complete v1 source document and binds `expected_v1_hash`, the v1 self-hash, and the v2-declared v1 hash before invoking the v2 verifier;
- preserves every verified v2 block monotonically;
- preregisters lag 3 as the only newly evaluated lag;
- publishes only the aggregate maximum across lags 1 through 3;
- keeps identity/fold lag-three values behind a strict-canonical private-ledger hash;
- treats `0.8` as an inclusive ceiling;
- keeps lags above 3 and external calibration timing explicitly unresolved;
- keeps current, paper, live, and profitability authority denied.

The v3 candidate does not claim arbitrary-lag residual independence. It is a finite coverage extension, not a statistical independence proof.

## Consumer-first activation order

1. Validate the v3 evaluator and rebuilding verifier against complete source context.
2. Add a separately versioned precommit v6 composition that cannot relax v5 or v3 blocks.
3. Add an aggregate-only report consumer v6.
4. Add a detached presentation envelope and card only after the consumer contract is frozen.
5. Consider mounting or current admission only through a separate explicit decision.

This ADR authorizes only step 1.

## Adversarial matrix

The targeted contract covers a positive stable context, the complete lag-three evasion chain, source-v2 block monotonicity, missing and unsupported sources, the complete v1 document and every expected hash, v1-to-v2 hash cross-binding, coherently resealed source tampering, context rebinding, aggregate privacy, authority denial, inclusive threshold behavior, zero energy, determinism, verifier tampering, and exact schema/fingerprint/lag registration.
