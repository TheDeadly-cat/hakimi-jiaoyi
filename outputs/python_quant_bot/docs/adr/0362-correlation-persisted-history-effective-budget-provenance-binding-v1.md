# ADR 0362: Correlation persisted-history effective-budget provenance binding v1

## Status

Accepted as a pure, unmounted, synthetic research provenance contract.

## Context

ADR 0346 binds the preregistered multi-window uncertainty cluster gate to effective-budget v3. ADR 0357 verifies a preregistered bounded persisted-checkpoint history prefix, and ADR 0361 proves that its final synthetic fixture can be replayed without persistent source-verifier seams.

No production consumer connects ADR 0357 to ADR 0346. A budget binding can therefore be cryptographically exact without declaring which persisted-history registration was inspected first.

The two current synthetic fixtures also have different `window_order_hash` values. Treating them as the same study would be an unsupported semantic promotion. Exact hash pinning can prove which two artifacts were paired, but cannot prove that their study or window identities are equivalent.

## Decision

Add `strategy_correlation_persisted_checkpoint_history_coverage_effective_budget_provenance_binding_v1.py` as a consumer-first provenance binding.

The preregistration:

1. Re-verifies the ADR 0357 coverage registration receipt.
2. Re-verifies the ADR 0346 binding preregistration and both of its source preregistrations.
3. Pins the history registration receipt, history ID, history study identity, history window order, budget binding preregistration, budget window order, symbol order, cluster partition, and both contract hashes.
4. Uses `EXACT_DUAL_SOURCE_PIN_NO_SEMANTIC_IDENTITY_EQUIVALENCE_CLAIM` as a permanent v1 policy.

The evaluation order is mandatory:

1. Verify the provenance preregistration.
2. Verify the exact bounded-history coverage gate and all lineage inputs.
3. If bounded history is not positive, return before invoking the ADR 0346 verifier.
4. Only after positive bounded history, verify the exact ADR 0346 evaluation.
5. Preserve a verified budget `BLOCK`; otherwise emit a provenance `PASS` that still leaves semantic identity equivalence and every operational permission false.

The output contains only hashes, statuses, bounded checkpoint counts, facts, and an activation trace. It does not embed lineage items, window audits, positions, matrices, prices, returns, or the effective-budget document.

The integration fixture does not trust the simplified ADR 0345 matrix-replay stub. It rebuilds each synthetic window through the real cluster preregistration, completed-price input, and correlation-matrix replay builders, replays every captured call through the original verifier, removes the fixture patch, and only then builds the ADR 0346 PASS and BLOCK sources.

## Consumer-first activation order

1. Exact dual-source preregistration.
2. Exact bounded persisted-history coverage verification.
3. Mandatory short-circuit for non-positive history.
4. Exact uncertainty/effective-budget binding verification.
5. Preserve source budget status.
6. Permanent identity-equivalence and runtime authority lock.

Any semantic study-identity bridge, presentation, HTTP route, runtime mount, writer, current pointer, paper, or live integration requires a separate preregistration and authorization decision.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact history PASS plus exact budget PASS | Provenance `PASS`, identity equivalence unproven |
| Missing middle history segment | `BLOCK`, budget verifier not called |
| Resealed history authority promotion | `UNKNOWN`, budget verifier not called |
| Resealed budget authority promotion | `UNKNOWN` |
| Verified ADR 0346 budget block | Source `BLOCK` preserved |
| Preregistration hash drift | `UNKNOWN` |
| Distinct history and budget window hashes | Both pinned, never equated |

## Evidence boundaries

- Pure synthetic, in-memory, and unmounted.
- No runtime, database, cache, log, service, browser, scheduler, HTTP mount, writer, publication, historical market data, K-line task, G50/G51 task, blind test, paper, or live task.
- A provenance `PASS` proves exact dual-source verification only. It is not semantic study equivalence, complete history, external provider authority, profitability evidence, budget activation, or trading permission.
- Natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
- Legacy pack-v5 public reads and pointer-v2 behavior are unchanged.
- UI and protected frontend assets are unchanged.

## Implementation fingerprints at design time

- ADR 0357 history coverage gate: `f55461b9b7fefc68c71d5f8bb8df84b05d1e731be6a15b39d4ac231c22834fd0`
- ADR 0346 uncertainty/effective-budget binding: `993a28a33e20bc64666ec3229e420a3299257382a25d9ff2d4aaf8da8ffd8918`
- ADR 0361 seam-free history fixture: `be2a921447ed6a0ffb304a0f2806fa30656ca392933d3b1416fa0d623282ce29`
- ADR 0361: `0d05f4910b7be86263c83f3858c1f2085885640d36e31e8214c5b4e0385328cd`

## Consequences

The project now has a production-grade, detached consumer prerequisite from bounded persisted history to the existing effective-budget binding. It prevents budget verification before positive history coverage and prevents exact dual-source pairing from being mislabeled as shared study identity. No active consumer or trading authority is created.
