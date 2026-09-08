# Research MVP baseline and acceptance plan

Objective: the supplied 2026-09-05 review, tasks T0–T8 and its minimum behavioral
acceptance table, supplemented by the full `Downloads/development_task_outline.md`
and `Downloads/hakimi_jiaoyi_review_2026-09-05.zip`, read after the user supplied
their local paths. The ZIP outline is byte-for-text identical to the standalone
outline. The initial check only inspected the goal attachment directory; it
did not establish that these files were absent from the computer. Strategy profitability is
not an acceptance criterion. Research-only and permanent paper/live/order locks
remain mandatory.

## Baseline and scope (T0)

- Current worktree: `cf77/哈基米v2交易`, detached `f4bfa8adab07a21b66b341a0b8b2fe1804c537d7`, initially clean.
- Old task: `01a06988-adcf-7aa1-8a19-72af3cbe5ca8`, “哈基米v2交易 CI 修复续作”.
- Original integration tree: `957d/哈基米v2交易` at `4fb6d191b282ea9a0d7136f4b94a9e9d49642178`, 36 status entries retained.
- Existing local prototype: `%TEMP%/hakimi-clean-verify-940b93aaad2c49a7bb14038d66204b4d/pr-a-main`, same f4 baseline, 62 status entries retained.
- 65 modified/untracked prototype files were copied into this new clean worktree.
  The source directories were not modified. This is local integration work,
  not a claim that a newly created worktree originally contained old dirty work.
- PR #1 was read live: OPEN/Draft, head `4fb6d191`, workflow run `33816097849`
  failed. No commit, push, PR edit, merge, or branch-policy change is part of
  this local implementation. A future remote run must be checked at its exact SHA.

Change classes: `src/hakimi_research` is installed research source;
`outputs/python_quant_bot/quant_bot` retains compatibility imports;
`tools` and `tests` are delivery/behavior checks; `.github` is the automated gate;
Electron and server changes restrict existing consumer paths. `docs` records
semantics and evidence; immutable input/report artifacts are under ignored
`artifacts`. Existing `examples` and `archive` retain historical formula/schema
evidence and are not regenerated to conceal numerical changes.

Formal entry: `hakimi-research snapshot-import` → `DatasetSnapshot` →
`ExperimentSpec` → `ExperimentRunner` → `ResearchReport`. `research` and `backtest`
invoke that same offline runner. `replay` recomputes it; `report-show` verifies and
reads one file without launching a service. The older desktop/terminal path is
legacy preview with a distinct execution model, not a second formal entry.

Dependencies: T1 gates are independent; T2 accounting + T3 packaging + T4
snapshot admission precede T5 scoring/runner; T6 measures actual runtime;
T7 limits consumers; T8 uses the installed artifact only after synthetic
behavior and wheel acceptance. No mandatory nine-PR split is imposed.

## Prespecified first descriptive study (T8)

This plan is written before collecting/inspecting the study prices.

- Dataset: public OKX BTC-USDT spot 1h, open timestamps in
  `[2026-08-01T00:00:00Z, 2026-09-01T00:00:00Z)`, cutoff at the end.
- Score: `[2026-08-04T00:00:00Z, 2026-09-01T00:00:00Z)`; preceding 72 rows
  provide context, no warmup positions/fees. Required Dual MA context is 62 rows.
- Fixed Dual MA 20/60, requested position 25%, stop distance 3%, take-profit 8%.
- Initial 10000 USDT; cash/spot only, no leverage; risk position cap35%,
  minimum cash5%, stop-distance cap3%, new-buy daily-loss threshold5%.
- Fee0.08% and slippage0.05% per side. Also run declared cost sensitivities
  2× and 3× both values, preserve every attempt, do not choose parameters.
- End policy: mark remaining inventory at the last scored close without
  fabricated closing fills. Cash reference is zero return/no fees/no trades.
- No fitting, search, formal confirmation, profitability promotion, account
  execution, or automatic follow-on collection. A short single historical
  month is descriptive and cannot establish persistent market advantage.
- Acquisition is an explicit bounded public GET operation. The formal runner
  never imports the collector; replay never fetches missing bars or falls back
  to a cache. Exact bytes/request/time/hash and all out-of-range/uncompleted
  counts are retained. HTTP capture is not cryptographic provider attestation.

## Acceptance evidence map

| Task | Authoritative evidence required |
|---|---|
| T1 | Actual six CI domains + gate behavior for failure/cancel/skip/missing; remote checks separately |
| T2 | First interval loss, equal-price fee loss, partial exits, inventory/fees conservation, risk requested/effective |
| T3 | Ordinary wheel, isolated environment outside checkout, no PYTHONPATH; full CLI workflow |
| T4 | Exact requested-range completeness, uncompleted/duplicate/period/unit rejection, raw-byte replay and immutable versions |
| T5 | Sufficient parameter-dependent context, no warmup fills, future-mutation causality, identical fixed computation |
| T6 | Failed Git status UNKNOWN; installed versions vs lock; actual source/build identity; separate result/report hashes |
| T7 | Safe external protocols, packaged debug disabled, default read-only backend, retired management handlers, read-only report |
| T8 | Prespecified capture/quality/specs/ledgers/reports, independent numerical reconciliation, installed replay receipt |

`tests/test_experiment_runner.py` covers the formal snapshot/CLI/scoring chain;
`tests/test_research_accounting.py` covers the numerical ledger;
the packaging/provenance/persistence tests and `tools/verify_wheel.py` cover
installation and recovery. Historical counts are not current acceptance.
Completion remains unproven until the final evidence audit is filled with
current results; this plan itself does not assert the tasks are complete.

## Detailed-outline amendment (before the expanded study)

The initial three Dual MA cost runs and the first ordinary wheel are retained
under `artifacts/first-descriptive-study`. They are preliminary evidence, not
the full T8 study. This amendment follows reading the detailed outline after
those runs; the data have already been inspected, so no blind/pre-unseen claim
is made. Additional strategy choices follow coverage requested by the outline,
not which strategy performed best in the preliminary sample.

Expanded attempt count: **16** on the same 744-row snapshot and 672-row score
interval. Four methods (Cash, Buy-and-Hold, Dual MA20/60, RSI14 with30/70
thresholds), each at1×/2×/3× declared costs =12. Four adjacent-parameter cells at
1× cost: Dual MA18/54 and22/66; RSI window13 and15 with unchanged30/70 levels.
No trials are dropped and no winning cell is selected. The standalone installed
Runner must support both baselines with explicit policy, not an extra formula
engine. Cash holds cash; Buy-and-Hold requests100% at the first scored open,
reserves fees, never adds/re-enters, and uses no protective exits. Those baseline
differences are declared, not silently inherited from active-strategy stops.

State slices for the four base1× runs use only the previous24 completed bars:
HIGH_VOL when the sample standard deviation of hourly close returns is at
least1%; otherwise UP for24h close return≥2%, DOWN for≤−2%, and RANGE for the
rest. Report count, mean observed per-bar return, arithmetic PnL contribution,
and exposure by state; do not pretend disjoint bars form a separately tradable
strategy or infer independent sample size. Empty/small slices stay insufficient.
These are descriptive breakdowns of16 planned runs, not additional parameter
search or confirmation evaluations.

Additional detailed acceptance: explicit StrategySpec declarations; linked
snapshot revisions and metadata-required CSV imports; legacy five-reference
checks pinned to the old immutable source (separate from corrected core tests);
Windows whitespace/Chinese install path; no termination of unrelated processes
on an occupied desktop port. Linux CI is configured but must remain NOT_RUN
until an actual remote Linux run provides evidence. Required-check configuration
and any GitHub writes remain maintainer decisions.
