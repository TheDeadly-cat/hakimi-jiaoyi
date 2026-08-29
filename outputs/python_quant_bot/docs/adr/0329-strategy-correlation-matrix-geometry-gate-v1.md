# ADR 0329: Strategy correlation-matrix geometry gate v1

## Status

Accepted as a pure-synthetic, unmounted strategy gate candidate. It is not
consumer activation, market evidence, profitability evidence, or trading
permission.

## Existing gap proof

The existing correlation matrix contract validates symbols, pair structure,
overlap, and bounded pairwise correlations. An explicit source search found no
PSD, eigenvalue, or Cholesky geometry check in
`exchange_terminal/services/strategy_correlation*.py`.

A three-symbol synthetic matrix with correlations `0.9`, `0.9`, and `-0.9` is
pairwise bounded, symmetric under the contract representation, and has unit
diagonal. The existing public matrix verifier returns `PASS`. Its analytic
determinant is `-2.888`, so it cannot be a valid correlation matrix.

Complete-link, cross-cluster edge uncertainty, common support, membership,
multi-window stability, strata, downside-tail, multiplicity, and cross-lag gates
do not replace a matrix geometry check. Pairwise edge validity is not global PSD
validity.

## Decision

Add an unmounted geometry gate with contract hash:

`ecefe7b0fe09edc3bb5d5b925b4acb731930b3e91af91edc8790c45cfa24b863`

For the frozen `AAA/BBB/CCC` test registration, the preregistration hash is:

`cf84bbb32813af7a2230a9e7cdd764b4536c6010ab839ca23d4978e85df71ace`

The gate:

1. Reuses the existing matrix verifier as its first prerequisite.
2. Requires a preregistered symbol order and fixed, non-overridable thresholds.
3. Reconstructs the full symmetric unit-diagonal matrix from every unordered
   pair and rejects missing, duplicate, non-finite, or out-of-bound input.
4. Computes all eigenvalues with a deterministic pure-Python symmetric Jacobi
   solver.
5. Blocks when any eigenvalue is below the fixed `-1e-10` PSD tolerance.
6. Returns UNKNOWN if the upstream matrix contract fails, reconstruction fails,
   or the eigensolver does not converge.
7. Emits geometry evidence and canonical hashes without source returns or market
   data.

## Consumer-first activation order

This ADR activates nothing. Any future integration must preserve this order:

1. Verify the upstream correlation matrix contract.
2. Evaluate matrix geometry.
3. Run complete-link audit and cluster gate.
4. Run stratified/multi-window stability gates.
5. Run effective-bet budget.
6. Consider presentation only after independent parity and adversarial review.

No compatibility path may treat a missing geometry document as PASS. Existing
consumers remain unchanged until a separately reviewed version binds this gate.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Pairwise-valid matrix with negative determinant | BLOCK |
| Identity matrix | PASS |
| Positive equicorrelation matrix | PASS |
| Rank-one all-ones matrix | PASS within tolerance |
| Missing, duplicate, non-finite, or out-of-bound pair | UNKNOWN or no input |
| Symbol-order drift | UNKNOWN |
| Caller widens PSD tolerance | Preregistration verification fails |
| Gate or eigenvalue mutation | Verification fails |
| More than 64 symbols | No preregistration |

## Consequences

This closes a global geometry blind spot before clustering and budget logic.
Passing the gate only means that the supplied synthetic matrix is consistent
with a correlation geometry under the frozen tolerance. It does not prove data
quality, stationarity, future stability, market validity, or profitability.

Natural-forward evidence, legacy pack-v5 `UNKNOWN`, pointer-v2, HTTP/runtime
locks, and paper/live locks remain unchanged.
