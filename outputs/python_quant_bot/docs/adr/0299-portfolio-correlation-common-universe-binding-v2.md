# ADR 0299: Portfolio correlation common-universe binding v2

## Status

Accepted as an additive, synthetic, research-only admission candidate. The v1
contract, current writer, host assets, routes, and paper/live permissions remain
unchanged.

## Proven gap

The v1 portfolio correlation admission independently verifies a legacy base
admission and the correlation evidence chain, but it does not compare the base
report's tradable universe with the correlation preregistration symbols.

A pure synthetic reproduction used a valid base report for `CCC` and `DDD` with
valid correlation evidence for `AAA` and `BBB`. Both the v1 candidate and its
exact verifier returned `PASS`. The result proves that individually valid but
different universes can be cross-spliced and interpreted as one admission.

This is not a market result or profitability claim. It is a deterministic
contract counterexample.

## Decision

Add `portfolio-correlation-admission-v2` as a versioned wrapper with an early
common-universe boundary. It takes one native-JSON snapshot of all documents and
identity arguments, then evaluates these ordered tiers:

1. `INPUT_IDENTITY`
2. `REPORT_UNIVERSE`
3. `CORRELATION_PREREGISTRATION`
4. `COMMON_UNIVERSE`
5. `V1_ADMISSION`
6. `PERMISSION`

The report universe and correlation preregistration must each verify exactly.
Their symbol lists must contain unique, non-blank native strings. Comparison is
order-insensitive but cardinality-sensitive:

`sorted(report.tradable_symbols) == sorted(preregistration.symbols)`

Subset, superset, duplicate, and disjoint-universe cases fail closed. When the
common-universe tier blocks, v1 is not built or verified and remains explicitly
`NOT_EVALUATED`. This prevents later correlation gates from manufacturing
secondary evidence after the binding failure.

If the common universe passes, v2 builds and exact-verifies the unchanged v1
candidate from the same snapshot. A v1 block remains a v2 block and preserves
the v1 first-blocking tier as bounded diagnostic metadata.

The v2 output stores source, universe, symbol-set, binding, preregistration, and
v1 candidate hashes. It does not embed the source report, correlation evidence,
or symbol lists.

## Compatibility

`portfolio-correlation-admission-v1` remains byte-for-byte unchanged. Existing
consumers retain their behavior. v2 is not accepted by the v1 JavaScript rail,
delivery adapter, host fragment, route, writer, or current admission path.

## Consumer-first activation order

1. Build and independently verify v2 from pure synthetic inputs.
2. Register the exact v2 schema, implementation, verifier, and v1 dependency.
3. Add a separate in-memory delivery adapter that accepts only exact v2 output.
4. Add a versioned rail consumer that presents `COMMON_UNIVERSE` explicitly.
5. Review the unmounted descriptor and permission language independently.
6. Only a later explicit migration may change a host import or current consumer.

No step automatically activates the next step.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Same symbols in a different valid order | v2 research `PASS` if v1 passes |
| Disjoint report and correlation universes | `COMMON_UNIVERSE` block; v1 `NOT_EVALUATED` |
| Report subset or superset | `COMMON_UNIVERSE` block |
| Duplicate report symbol | `REPORT_UNIVERSE` block |
| Missing or malformed universe contract | fail closed before preregistration use |
| Non-native mapping or cyclic input | `INPUT_SNAPSHOT` block |
| Matching universe with high correlation | v1 block preserved by v2 |
| Strategy identity cross-splice | v1 exact gate block preserved by v2 |
| Candidate resealed after permission promotion | exact v2 verifier rejection |
| Source authority promotion | permission remains blocked |

## Residual boundary

The legacy base report does not carry a strategy, variant, or lane identity.
This ADR therefore proves and enforces common tradable-universe identity, not a
new identity claim for the legacy report. The existing selection-cell and v1
gate identity checks remain responsible for strategy, variant, and lane binding.

## Permission and evidence boundary

The v2 candidate is consumer-only and research-only. It performs no file, DB,
cache, network, runtime, DOM, browser, scheduler, writer, or trading operation.
Current activation, automatic internal backtest activation, paper authorization,
live orders, and profitability claims remain false.

The public natural-forward evidence chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
