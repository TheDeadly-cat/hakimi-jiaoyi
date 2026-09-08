# ADR 0510: Verified walk-forward, stability, and multiplicity report binding v1

Date: 2026-08-29
Status: Accepted for dormant research-only implementation

## Context

ADR0509 introduced a canonical frozen Train / Validation / Frozen Test evaluator, cost multipliers, benchmark observations, deterministic verification, and a neutral Markdown renderer. Its renderer intentionally declared that walk-forward, parameter stability, multiple-testing lineage, market-regime slices, and tail/distribution metrics were not yet bound.

The legacy formal research chain already contains producers for several of these concepts, but those producers are coupled to historical runtime artifacts and registries. Reimplementing them inside the canonical package would create a duplicate research boundary; calling them now would violate the source-only, no-runtime continuation boundary.

## Decision

Add validation-evidence-v1 as a canonical supplemental evidence contract and frozen-evaluation-markdown-v2 as a dormant composition renderer.

The contract:

1. binds the exact ADR0509 report through canonical SHA-256;
2. records at least two ordered walk-forward windows with explicit Train, Validation, and Frozen Test index ranges;
3. enforces declared purge and embargo gaps structurally;
4. binds every selected window parameter to an observed preregistered trial;
5. preserves observed and failed trial outcomes in a complete multiple-testing ledger;
6. records a selected parameter and neighboring parameter observations without erasing failed neighbors;
7. records BULL, BEAR, RANGE, and HIGH_VOLATILITY slices, including explicit GAP entries;
8. uses exact native dict, list, str, int, bool, float, and null values only;
9. rejects non-finite source-report floats and subclass-controlled identity values;
10. fixes profitability, blind-test, paper, live, and order-entry authority to exact false.

ADR0509 v1 remains immutable. The v2 renderer first invokes the ADR0509 verifier/renderer, requires all four known not-bound markers to still be present, replaces those markers with explicit v1 evidence bindings, and preserves the tail/distribution gap. This prevents silent base-contract drift.

## Interpretation boundary

BOUND means that an observation has a complete versioned identity and consumer path. OBSERVED means structurally present. GAP means a declared observation failed or is unavailable. None of these states proves profitability, completes a formal blind test, or grants paper/live/order permission.

Synthetic values used by contract tests are fixtures only and must not be reported as strategy performance.

## Consumer-first activation order

1. Dormant exact-native verifier and neutral renderer.
2. Pure synthetic and adversarial contract matrix.
3. A narrow adapter from one existing formal producer, with source artifact digest equality.
4. Deterministic Range, Trend, and Ensemble report generation under separately authorized data use.
5. CLI or UI activation only after producer compatibility and report acceptance are independently proven.

No current CLI, UI, pointer, scheduled job, or legacy formal runner changes in this ADR.

## Preserved invariants

- Research-only capability remains authoritative.
- paper, live, order entry, and legacy optimization remain disabled.
- The single-look public evidence chain is unchanged.
- Legacy pack-v5 public reads remain UNKNOWN/null.
- pointer-v2 is not reissued.
- Presentation remains SOURCE -> GAP -> MATURITY -> PERMISSION.
- No runtime, database, cache, log, credential, service, browser, scheduler, or market task is required.

## Verification contract

Targeted verification covers deterministic ordering and digests, source-report mutation, evidence mutation, exact-native malicious subclasses, non-finite values, purge/embargo violations, duplicate windows, incomplete trial ledgers, failed selection, visible stability/regime gaps, authority escalation, and base-renderer drift.

## Formal search-lineage producer binding

The first producer adapter targets strategy_research_search_lineage v2. Its public contract proves the search-family identity, current and cumulative trial counts, prior-registration count, lineage hash, and fail-closed authority fields. It does not expose per-trial result identities.

The adapter therefore keeps two distinct layers:

- the formal producer artifact is independently verified by its existing verifier and bound by both its lineage hash and a canonical full-artifact SHA-256;
- the ADR0510 multiple-testing ledger retains concrete preregistered trial identifiers and observed/failed outcomes.

The formal current_trial_count must equal the number of concrete preregistered trial identifiers. Both layers are included in evidence_sha256. This closes count/history provenance without claiming that the count-only producer proves each trial result.

## Verified formal report to per-trial ledger projection

The formal strategy research report is the per-trial result producer. After verify_strategy_research_report returns PASS, the application adapter projects every batch_spec variant into one deterministic receipt. Each receipt binds the producer batch_run_hash, variant_id, param_hash, implementation fingerprint, all sorted selection-cell run hashes, the aggregate validation-ranking digest, frozen-test membership, all sorted test-cell run hashes, and the aggregate test-result digest when present.

Execution state and research decision are distinct. A fully observed trial can retain decision_status BLOCK and its exact decision blockers. FAILED remains reserved for missing execution evidence. This prevents an unsuccessful research decision from disappearing or being mislabeled as an execution failure.

The projection requires exactly one preregistered frozen candidate for ADR0510 v1. Reports with zero or multiple frozen selections remain explicit adapter gaps rather than permitting a post-hoc choice. The formal batch_run_hash is stored as producer_report_sha256 and enters the multiple-testing ledger digest.

## Tail and distribution evidence v1

ADR0510 now binds tail-distribution-evidence-v1 to an exact result path inside the supplied ADR0509 report. The verifier resolves that path, hashes both the full source report and selected result, and recomputes the complete artifact before accepting it.

The computation uses only the frozen equity_curve and fills. It defines annualized volatility, Sortino, Calmar, maximum drawdown duration, Profit Factor, win rate, payoff ratio, trade expectancy, turnover, market exposure, historical 95/99 percent VaR and CVaR, monthly and yearly return buckets, return without the best month, PnL without the best trade, and positive-month/trade contribution concentration. The quantile method is historical-nearest-rank-lower-tail-v1 and periods_per_year is an explicit identity-bearing input.

Undefined metrics remain null with explicit GAP codes. Small samples, no downside, no drawdown, no closed trades, one-sided trade outcomes, insufficient month/year buckets, and unavailable positive-contribution denominators are never converted to zero. The first calendar bucket is marked partial_start because the current BacktestReport curve begins after warmup rather than at initial capital.

This closes the ADR0509 tail/distribution not-bound marker only when a recomputable evidence object is supplied. It remains research-only and creates no performance, blind-test, paper, live, or order authority.
