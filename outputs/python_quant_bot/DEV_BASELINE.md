# Hakimi Trade v2 Saved-Project Baseline

This file supersedes the historical G43 isolated-development notice that came
from the read-only reference tree. The authoritative and only writable project
root is:

`C:\Users\Administrator\Documents\哈基米v2交易`

The current baseline, validation evidence, and remaining limitations are
maintained in `docs/project_status.md`. Historical development ports, process
IDs, `runtime_g43`/`runtime_g50`/`runtime_g51_dev` directories, screenshots,
registries, and databases are not part of this saved-project baseline.
Use `docs/README.md` as the document index; current source and scoped test
evidence take precedence over stale historical status text.

Strategy research now has two explicit current versions. Development remains
schema 13 with hypothesis-v2 and admission-v2. Formal preregistration and the
formal runner use schema 14 with hypothesis-v3,
`strategy-research-search-lineage-v1`, and admission-v3. Mechanism-specific
failure conditions remain executable allowlisted predicates; schema 14 adds a
global registered-search ledger rather than changing schema 3-13 hashes.

Before any formal selection data is loaded, the store must use the one
canonical registry under the active-runtime root, rebuild every REGISTERED
nested-research trial in a transaction, bind the claim/event tail, and verify
the lineage live. Validation ranking uses `cumulative_trial_count`, not the
current batch's variant count, so a new generation or family name cannot reset
the search penalty. The public admission-v3 builder is receipt-consistency
only and always blocks; only the store-owned live gate can admit. Path, claim,
event, lineage, or cumulative-count drift produces no frozen candidate, TEST,
confirmation load, holdout result, or forward candidate. Offline report
verification is explicitly limited to
`OFFLINE_REPORT_AND_PREREGISTRATION_RECEIPT_CONSISTENCY_ONLY` and does not claim
current database truth.

The current natural-forward public projection is
`portfolio-forward-dashboard-v7`. It preserves the operational view while
requiring the exact `portfolio-forward-statistical-maturity-v3` contract. Its
upstream persisted chain is `portfolio-forward-statistical-audit-v2` plus
`portfolio-forward-readiness-v3`; its frozen public-pack chain is
`portfolio-internal-backtest-pack-v6` plus
`portfolio-backtest-return-quality-snapshot-v4`. Dashboard v6/maturity-v2 and
audit-v1/readiness-v2 remain explicit historical compatibility paths and cannot
be routed as current evidence. The public maturity states remain `NOT_DUE`,
`REVIEW_REQUIRED`, `STOP_RESEARCH`, and `BLOCK`; none is trading authority.

The server still reads four candidate-bound fixed artifacts: observer and
performance status with 16 MiB limits, plus backup-v2 and watchdog-v3 receipts
with 256 KiB limits. The broader forward-source boundary now shares
`services/forward_artifact_io.py`: bounded, no-link/reparse, strict-object JSON,
Windows-safe basename validation, memory/recursion containment, and path-free
errors are reused by the active-candidate, active-research, performance-runner,
and watchdog paths. Control receipts/registries are capped at 256 KiB, compact
candidates at 1 MiB, invalidation/pack documents at 32 MiB, observer/performance
and statistical status at 16 MiB, and research/robustness documents at their
existing 256 MiB producer ceiling. The request path does not glob, select a
newest-looking artifact, open SQLite, or replay an archive.

The v2 audit locates the first settlement prefix at which both preregistered
outcome and executed-rebalance thresholds are jointly mature (currently 60/8).
Exactly that prefix is used once for the paired bootstrap and the prefix
drawdown-risk acceptance check. The prefix identity, stage, risk receipt, and
decision hashes are frozen. Later settlements remain full-chain-integrity
checked and descriptive, but never re-enter the statistical or risk decision;
therefore a first BLOCK cannot recover and a first PASS cannot be overturned by
optional stopping on a later tail. Before any resampling loop, the shared budget
guard requires an integer resample count from 100 through 50,000, an integer
block length from 1 through 1,024, and a block length no greater than the prefix
sample size. Invalid or excessive work fails closed before the stage starts.

Maturity-v3 rebuilds that first-joint-maturity decision from the embedded full
series and requires canonical equality with persisted readiness-v3. `NOT_DUE`
requires at least one remaining outcome/rebalance gate; `REVIEW_REQUIRED` and
`STOP_RESEARCH` require both remaining counts to be zero; `BLOCK` zeroes all
eight public progress counts. A valid negative result is `STOP_RESEARCH`, not
missing evidence.

The exact current public verification scope is
`PERSISTED_READINESS_V3_AND_FIRST_JOINT_MATURITY_DECISION_REBUILT_FROM_EMBEDDED_FULL_SERIES_NO_SETTLEMENT_REPLAY`.
This is deliberately `NO_SETTLEMENT_REPLAY`: the public join does not reopen or
replay the source settlement ledger. It demonstrates deterministic agreement
with persisted readiness and its embedded series, not external authenticity,
cryptographic provenance, profitability, parameter selection, paper
authorization, or live authority.

The current report-root writer is pack-v6 with forward-evidence-v2. It keeps the
fixed `portfolio-backtest-pack-pointer-v2` schema; after an explicit successful
writer run publishes a current v6 pointer, the read-only public loader projects
snapshot-v4. This change did not automatically reissue the persisted pointer. A
historically valid pack-v5 bundle can still be
verified under its frozen contract, but a pointer-v2 public load now returns
`UNKNOWN` with null quality/forward values instead of treating v5 as current.

A verifier-only `portfolio-forward-local-source-anchor-v1` is now derived only
after archive-v3 restore rehearsal independently rebuilds the archived shadow
and performance ledgers, binds the exact copied database bytes before and after
the read, and obtains equal non-empty observation/settlement date chains. The
archive manifest remains v3 and does not embed the derived anchor, avoiding a
hash cycle. Backup-status-v2 carries the anchor; watchdog-v3 independently
re-verifies the archive and binds the same anchor; maturity-v3 recomputes the
current full or prefix projections. A contradiction blocks maturity and zeroes
its eight progress fields, while `FULL` or `PREFIX` never promotes the underlying
maturity result.

This anchor's only scope is
`LOCAL_ARCHIVE_CROSS_ARTIFACT_BINDING_ONLY`. It does not authenticate an
external data provider, settlement source, broker fill, profitability, parameter
selection, paper authorization, or live authority. A coordinated local writer
can still reseal the databases, archive, and receipts; deleting both local
receipts can also degrade coverage to `NOT_AVAILABLE`. An actual external
anchor still requires an independent signing trust root and an external
append-only/WORM/timestamp receipt.

The existing forward-observation band keeps the neutral source-first order
`SOURCE -> GAP -> MATURITY -> PERMISSION -> historical returns`. The current
static fingerprint is `20260814-single-look-contract-1`. At `<=480px`, native
`details/summary` disclosure collapses market search, categories, and the market
button list by default while retaining the current symbol/type in the summary;
desktop and 720px keep the wide source contract. One rendered 480px check
observed the closed main content near y=180 with zero visible market buttons,
and the opened content near y=455 with 46 market buttons. The later browser
policy denied the 720px keyboard interaction step, so 720px/desktop are claimed
only from source/static contracts, not as a full browser/device QA pass.

Current activation tests pass 161/161 across single-look, maturity,
projection/server, pack/pointer, and lean contracts. The shared artifact-reader
boundary passes 109 targeted tests with two host symlink skips; the corrected
256 KiB active-registry boundary passes 16/16; an independent final matrix
passes 139 tests with four host symlink skips. These suites overlap and are not
added into a full-regression total. The complete Node evidence contract and
three `node --check` syntax checks pass. No old K-line replay, G50/G51 rerun,
formal blind test, lean-fresh run, product service, scheduled runtime task,
paper action, live action, or automatic pointer reissue was performed. One
agent's overly broad read-only search matched source-code lines inside a runtime
backup copy; those lines were not used as evidence and no runtime or backup file
was changed.

Schemas 13 and 14 inherit schema 11 direct replay and schema 12's unchanged
standard development gates. Schemas 3-13 retain their historical hashes and
verifier contracts. The fixed pointer artifact, publication expectation, and
publication receipt all remain v1 with unchanged exact fields. Public evidence
uses an exact capability split: report schemas 3-10 retain v3, schemas 11-12
require v5, schema 13 requires v6, schema 14 requires
`strategy-lab-frozen-evidence-v7`, and schema 15+ fails closed. v7 requires
hypothesis-summary-v3, admission-v3, post-selection replay-v1,
failure-conditions-v4, and a deidentified search-lineage-v1 projection. Only a
live-at-selection binding can publish `BOUND`; receipt-only input yields
UNKNOWN. The public lineage exposes global prior/current/cumulative counts and
fixed verification scopes, never the family value, registration or candidate
IDs, paths, or protocol/claim/anchor/lineage hashes. Every layer fixes
profitability, parameter selection, automatic paper activation, paper
authorization, and live ordering to false.

Schema 11/12/13/14 public evidence also includes the pure
`strategy-post-selection-replay-summary-v1`. For the currently selected
strategy only, it summarizes frozen TEST and one historical holdout with
candidate/result/cell coverage, replay-preservation counts, formal aggregate
counts, minimum configured/excess/stressed return, worst drawdown, and total
trades. It never exports symbol, variant, parameters, candidate IDs, local
paths, or raw blockers. Replay-integrity failures null every numeric metric;
integrity-valid negative outcomes retain finite negative values. Its PASS is a
strict public replay-preservation diagnostic, not a replacement for the
formal cross-symbol aggregate, candidate gate, or report verifier. The
holdout remains historical confirmation, explicitly not natural-forward
performance, WFO, or profitability proof.
The standalone return-quality builder now uses the same canonical authority
scanner as the sealed portfolio evidence chain. Case, separator, and camel-case
aliases such as `Paper_Authorized`, `canTrade`, and
`parameter-selection-authority` fail closed even inside Mapping/tuple values;
this hardening does not change return calculations or pack schema versions.
The execution-rehearsal and statistical-audit CLIs now share one active
research-source loader instead of independently globbing for a report with a
matching batch hash. The shared path first delegates to the canonical active
candidate verifier, then reads only the completion-receipt basename in the
report root and rebinds its bytes/SHA, batch identity, and frozen candidate
identity. A missing or drifted bound report blocks before evidence expansion or
calculation; an explicit operator-supplied `--research-report` retains its
existing offline contract.
Scoped schema-14 validation passed CLI 16/16, lineage/admission/protocol 26/26,
runner 35/35, companion 68/68, public pointer/failure/replay 50/50, and an
independent expanded public audit 71/71. The root agent separately reran four
critical core cases and five public cases. The watchdog/authority/lean cross
set passed 22/22, and the complete frontend adversarial contract plus three
JavaScript syntax checks pass. These sets overlap and are not added into a
single regression total. They used temporary or in-memory fixtures and
controlled source only; they did not load production runtime data, run market
history, execute old G50/G51 evidence, run a formal blind test, or run lean
fresh.

The current backtest page keeps research-gate, time-slice, dataset-manifest,
and audit-artifact statuses neutral in the visible UI. Raw `PASS`/`READY`
values remain audit metadata only; no evidence status grants paper or live
authority. The static resources are now fingerprinted as
`20260814-single-look-contract-1` for styles, evidence presentation, and
app. The strategy lab's invalidation column is the widest desktop evidence
column and uses a semantic definition-list ledger with neutral rules and the
existing mono face. It adds no card treatment, state color, animation, request,
polling, or live region. At 720px the outer evidence bands stack while ledger
label/value rows remain scannable; at 480px each ledger row becomes a single
column. These layout claims have static-contract coverage only; browser and
real-device QA have not been performed for this slice.

The frozen return-quality band now follows the explicit source-gap-maturity-
permission-return sequence. An unverified response is classified only from locally
recomputable safety, source, version, stage, value-consistency, and
natural-forward contract facts. A verified `failure_conditions` object is
reduced to counts in four allowlisted categories; raw blockers, paths,
candidate identities, full hashes, and claimed return strings are never
rendered. Stage names, evidence/benchmark/statistical statuses, benchmark
bases, and summary evidence stages are allowlisted and mapped to fixed local
copy before they can enter text, dataset values, or titles. Localized authority
keys such as `可下单`, `已授权`, and `实盘授权` fail closed just like canonical
English aliases. A valid observed negative result says to stop promotion rather than
pretending that the evidence is merely missing. The local fallback carries the
same forward, schema, source-mode, and cue fields. This slice has Node/static
contract evidence only and no browser or device QA.
The attribution spine consumes the verified natural-forward dashboard under
`forward_validation.incremental_observation`, not its outer control-center
wrapper. The same neutral projection is visible in both the strategy/backtest
workspace and the platform control center, so users can distinguish the same
portfolio candidate, a mismatched candidate, and an unverified relationship
before combining frozen return evidence with forward observations. Full hashes
remain audit metadata; the visible relationship does not prove profitability
or grant paper/live authority.
The attribution spine also has a default-collapsed full-identity hash check.
It appears only after strict source mapping passes and adds no request, live
region, direction color, or authorization semantics. The platform control
center now reuses the shared `sanitize_authority_claims` canonical alias
contract (`Paper_Authorized`, `canTrade`, and `live-order-allowed`) while
preserving component-local fields such as `armed` where their existing
descriptive contract requires them.
The natural-forward control section now separates its next missing evidence
from the latest verified receipt. A strict six-state presentation map produces
the visible gap text and ignores upstream next-action or pause prose; the
receipt is a non-live disclosure at the end of the section. The section keeps
one live status only and never surfaces READY/order wording as authority.
The market-truth center follows the same evidence-first hierarchy. Its visible
gap is generated only from the verified READY/STALE/BLOCK/UNKNOWN status; raw
`next_action` text is ignored. Symbol, quote source, candle source, freshness,
and last-completed-candle facts remain separate ledger cells, with one live
status and a single-column mobile divider treatment.

The strategy lab keeps its immediate heuristic response separate from frozen
research evidence. Schema-3 through schema-10 reports use public v3;
schema-11 and schema-12 use public v5, and schema-13 uses public v6. V6 must
carry strict post-selection replay, hypothesis-summary-v2, admission-v2, and
failure-conditions-v3; cross-version or downgrade-shaped evidence fails
closed. Only a valid v6 `MATCHED` presentation emits frozen mechanism and
future-condition ledger rows. Each mechanism row separates the condition ID,
formatted predicate/threshold, observed value, outcome, and research boundary;
v3, v5, and `NOT_IN_REPORT` emit no rows. A matched strategy with no candidate
shows `NOT_APPLICABLE` and explicitly says no PASS conclusion was formed. The
two future rows remain raw `NOT_DUE` and visibly state "not evaluated, not
PASS." All supported public contracts retain the facts-only currentness
binding, while hypothesis-bound schema-7 through schema-13 reports require the
versioned hypothesis contract appropriate to that report. Schema-3 through
schema-6 reports remain readable only as
`LEGACY_NOT_BOUND`; historical results cannot be rewritten as preregistered
hypotheses. A successful strategy-research run may publish only one
fixed, hash-bound pointer after the public semantic verifier passes. The
read-only `/api/strategy/research-evidence` route reads exactly that pointer
and one bound report, never scans for a newest file and never runs a backtest.
Pointer publication now starts from a versioned expectation built from the
in-memory report and its deterministic UTF-8 bytes. The publisher binds the
report basename, canonical report hash, file SHA/length, report schema,
batch/dataset/run hashes, governance status, creation time, and fixed-false
authority. It atomically replaces the unchanged pointer-v1 artifact, then
re-reads both pointer and report and returns a receipt whose pointer hash is
uniquely recomputed from that expectation. Formal and development CLI paths
require a report-root publication target before hypothesis loading, registry
access, claim, or market-data loading; nested and external targets fail closed.
This remains a local two-file integrity protocol, not a cross-file atomic
transaction or an external cryptographic trust anchor.
Its whitelist is descriptive only: parameter-sequence adjacency is not
numeric distance, fixed-parameter chronological slices are not WFO, and no
field can select parameters or authorize paper/live trading. A missing current
pointer or a report that does not contain the selected strategy remains
explicitly unverified/unmatched rather than borrowing another strategy's
evidence. For a strategy present in the report, the route recomputes each
frozen signal-implementation fingerprint through the current strategy service.
Current schema-6/7/8/9/10/11/12 reports additionally hash-bind `implementation-manifest-v2`
before research data is loaded. The public route rebuilds the current closure
from the fixed research-runner entrypoint, then verifies that Python
source/import closure and runtime contract against the frozen report,
using a source path gate that blocks external paths, `runtime*` directories,
`.env*`, and `config.local.json` before any read. It reports full-closure match,
mismatch, or closed failure separately from signal identity. Schema-3/4/5
reports remain legacy-compatible and can show only signal identity; they never
gain a full-manifest claim retroactively. The route now also emits
`strategy-research-currentness-facts-v1`, which recomputes the report age and
UTC calendar-day distance from the verified report timestamp/data cutoff and a
caller-supplied observation time. This is a facts-only projection: freshness
and report-age thresholds remain undefined and explicitly unchecked, and UTC
calendar days are not trading sessions. Mismatched cutoff sources, future
times, malformed dates, forged ages, thresholds, or authorities fail closed.

New formal preregistration writes `strategy-matrix-protocol-v3`. Its protocol
hash binds an absolute `strategy-research-protocol-artifact-binding-v1` and
the `IMMUTABLE_NO_CLOBBER` publication mode. The CLI validates the output
against the report root, fixed report pointer, SQLite registry and its
`-wal/-shm/-journal` companions before publishing a UUID temporary file with
exclusive creation, fsync, and no-clobber linking. Read-only mode blocks before
any artifact or Store creation. Register, post-register, and claim boundaries
all revalidate the immutable sidecar. If database registration fails after
publication, the orphan sidecar is not claimable or deleted; a later retry may
reuse only the same unexpired protocol after generation, hypothesis, full
batch, implementation, registry, and artifact-binding checks. This is not a
cross-resource filesystem/SQLite transaction, and legacy protocol v1/v2
verification remains unchanged.

Formal strategy research and the formal strategy-matrix runner now share
`prepared-research-result-v1` between the fully verified final report and
registry completion. Each runner builds a deterministic completion receipt from
one clock attestation, verifies the full formal report, then publishes a hidden
no-clobber prepared artifact before the registry consumes the result. A later
invocation can restore a `RUNNING` or `COMPLETED` registration from that exact
artifact before any batch rebuild, claim, exposure rescan, or market-data load.
Final-report conflicts and publication failures are non-success outcomes.
Strategy research retains its existing fixed pointer; the matrix runner has no
pointer and this change does not invent one. Recovery still does not cover a
crash after claim but before prepared publication, and the filesystem/SQLite
boundary is not a cross-resource transaction.

Schema-7 reports introduced `strategy-hypothesis-preregistration-v1`, which
schemas 7-12 retain as a historical contract. Current schema-13 reports use
`strategy-hypothesis-preregistration-v2` before any market-data load. The
project-owned JSON draft freezes a new hypothesis ID, strategy IDs, research
generation, mechanism statements, and machine-readable mechanism-specific
failure predicates. The schema fixes, rather than lets the author weaken, frozen
sequence adjacency, positive stressed returns, fixed-parameter chronological
slices (not WFO), a fresh single-use holdout, at least 60 natural-forward
outcomes and 8 executed rebalances, and statistical recheck at maturity. The
full contract and hash are sealed into batch/report/protocol hashes and
semantically rebuilt by verifiers. G50/G51 IDs remain rejected. The editable
starting point is `docs/strategy_hypothesis_preregistration_template.json`;
the template itself is not a valid or authorized strategy claim.

The verified strategy projection includes versioned descriptive failure
conditions. Report schemas 3-10 retain
`strategy-research-failure-conditions-v1` with five dimensions: parameter
plateau, cost break-even, fixed-parameter time slices, signal identity, and
the full implementation closure. Schemas 11-12 use v2 and add frozen-TEST and
historical-holdout replay-preservation conditions. PASS/BLOCK/NOT_RUN map to
not-triggered/triggered/not-checked and are rebound to the exact stage state
and blockers. Dataset freshness, report-age policy, and natural-forward
performance remain evidence gaps; no day threshold or promotion rule is
invented. The UI keeps its source/robustness/invalidation audit spine and
places the neutral post-selection group after research coverage.

The interactive backtest now separately emits
`backtest-risk-control-surface-v1` over its existing 5 x 5 x 4 position,
take-profit, and stop-loss grid. The grid definition is shared by evaluation
and projection. The pure service recomputes exact coverage, native finite
metrics, the highest-score cell, one-grid-step neighbors, axis support, and the
connected near-score component. This is risk-control sensitivity on the same
development data, not strategy-signal parameter stability: selection bias is
uncorrected, no out-of-sample claim is allowed, and it cannot select parameters,
prove profitability, or authorize paper/live trading. The frontend independently
recomputes the summary from all 100 projected cells and fails closed on a forged
status, count, topology, metric, or authority field.

Current schema-5/6/7/8/9/10/11 research verification also requires native integer batch
limits (`limit`, `max_test_candidates`, and `max_confirmation_candidates`; the
row limit is at least 360 and both candidate caps are at least 1);
resealing a report with numeric-string limits remains blocked. The development strategy comparison and backtest candidate rows use
neutral presentation; copying a candidate only fills the research form and
does not run or authorize anything.

Internal backtest pack v2/v3 also fail closed when a published
`forward_progress` object is present but its six progress counts are not
native non-negative integers or its scheduler health is not a non-empty
string. This protects the frozen evidence from projection-only numeric casts;
missing progress in older hand-built v2 artifacts remains compatibility-only
and never grants authority.

## Permanent boundaries

- Real-order execution is permanently hard locked in code.
- Paper execution is unauthorized unless a future, explicit, isolated workflow
  independently satisfies every risk and governance gate.
- Read-only acceptance must not mutate runtime databases or sidecar files.
- `.env*`, local configuration, credentials, databases, caches, logs, and
  screenshots are never migration inputs.
- G42 remains observation-only. It has no paper or live authority.
- G50 `trend_pullback` and G51 `squeeze_breakout` are falsified historical
  hypotheses. Their old strategy IDs may reproduce historical evidence but
  cannot start a new research generation.
- No formal blind test is authorized by this baseline.
- The USD 100-200 small-capital feature is a read-only planning artifact only.
  It has no credential provider, signer, deposit action, execution adapter, or
  order authority; even complete planning evidence cannot unlock paper or live
  trading.
- Public order-book microstructure is descriptive evidence only. The fixed
  5/10/25 bps midpoint bands report visible bid/ask notional and per-side
  boundary coverage; a partial band is only a visible lower bound. Neither
  these bands nor any snapshot ratio can create a signal, color a strategy
  direction, authorize paper trading, or relax the permanent live hard lock.
  The 20-level standard book remains incomplete and non-RPI.
- Stock display quote identity is source-aware: a fresh higher-quality quote
  cannot be overwritten by `offline-seed`/preview fallback, older same-source
  timestamps are rejected, and stock tape/盘口 rows are filtered to the active
  quote source. Quote source and candle source remain separate evidence; a
  preview chart is never promoted to realtime by this rule.
- The ResearchBrief bridge accepts versions 1.0 and 1.1. Version 1.1 exposes a
  contract hash and optional idempotency key: an identical retry replays the
  original immutable summary, while a same-key content conflict is rejected.
  Research summaries remain research-only and cannot carry account, order,
  credential, or execution authority.
- Public OKX GETs share a bounded in-memory provider coordinator (20 requests
  per 2 seconds, non-blocking admission, bounded failure backoff). Per-symbol
  instrument/order-book singleflight and last-good cache behavior remain the
  source of truth; a rate-limit or upstream failure returns a retry hint or a
  stale/unavailable result and cannot be promoted to READY. This coordinator
  does not retry automatically, persist state, read credentials, or create any
  order route.
- Strategy research keeps a fixed parameter grid and chronological
  train/validation/test/holdout separation. Schema-4/5/6/7/8/9/10/11/12/13 reports require
  `strategy-parameter-plateau-v2`: topology comes from the report's frozen
  variant sequence, and only an eligible best point with an eligible,
  directly adjacent near-best point forms a descriptive plateau. Sequence
  adjacency is not a numeric multi-parameter distance. Schema-3 reports remain
  compatible with an absent or legacy v1 summary. Neither version can select
  parameters, launch another generation, authorize paper, or authorize live
  trading.
- New reports use schema 13 and inherit schema-11 post-selection replay plus
  schema-12 standard admission gates.
  Schema-5/6/7 retain
  `strategy-research-selection-cell-evidence-v2`; schema-8 uses
  `strategy-research-selection-cell-evidence-v3`; schema-9 uses v4 and schema-10/11/12/13
  use `strategy-research-selection-cell-evidence-v5`. The selection-cell hash seals
  every stable cell field except diagnostic elapsed time, including complete
  fold/selection-replay/cost/lookahead evidence, frozen risk, the evidence schema, and
  research/paper/live authority. Schema-8/9 bind
  `strategy-cost-stress-evidence-v1`: exact stress/severe names and costs are
  recomputed from frozen variant risk, selection baseline is rebound to the
  validation metrics, and the frozen-test configured/severe returns, drawdowns,
  and trade counts are semantically checked. Schema-8 freezes fee/slippage at
  the backtest report's 8/4 decimal precision, preserves an explicit zero-cost
  input instead of applying legacy defaults, and rejects non-canonical risk or
  negative drawdown evidence. Schema-3/4 reports retain their
  historical selection-cell hash; schema-5/6/7 keep their v2 hashes and
  verification semantics, and schema-8 keeps its v3 hash and verifier.
  Schema-6/7/8/9/10/11/12/13 require the full implementation manifest.
  Schema-7/8/9/10/11/12 retain hypothesis-v1, while schema-13 requires the
  structured hypothesis-v2 mechanism-failure contract. Schema-8 is the
  cost-evidence version, schema-9 adds topology evidence, schema-10 adds causal
  fold and complete selection-result replay, schema-11 adds post-selection
  replay, schema-12 adds standard admission, and schema-13 adds mechanism
  admission.
- Schema-9 binds `strategy-fixed-chronological-slice-evidence-v1` to the exact
  selection-prefix dataset and each fold's number, count/index bounds, dates,
  dataset hash, and declared result fields. Verification rebuilds the
  prefix/fold identities from the frozen dataset snapshot and requires strict
  chronological order, no overlap, no gap, and full prefix coverage before
  recomputing the existing fold summary. It does not yet rerun the causal
  engine from frozen rows/strategy/risk to prove each declared fold result;
  schema-10 implements that stronger semantic replay while preserving this
  schema-9 verifier and hash contract unchanged.
  Parameters are not refit per fold
  (`parameters_refit_per_fold=false`), so this is not walk-forward
  optimization. Cost sensitivity now blocks when the worst stressed return is
  not positive, and missing/non-finite baseline or scenario returns/drawdowns
  block with null evidence rather than being coerced to zero.
- Schema-10 binds `strategy-fixed-chronological-slice-evidence-v2`. It ignores
  evidence-provided fold topology as an input, derives the fixed three-fold,
  minimum-120-row policy from frozen `rows[:validation_end_index]`, and calls the
  same direct causal-engine replay used by the runner. Each fold seals dataset,
  strategy, params/param hash, risk, execution model, signal-engine version,
  startup/evaluation policy, stable result metrics, and complete trade/equity
  digests. Coherent metric/hash reseals, digest-only tampering, and self-selected
  fold policies fail semantic verification. This remains fixed-parameter,
  descriptive research evidence, not WFO, profitability proof, or authority.
- Schema-10 also binds `strategy-selection-cell-replay-v1`. For formal reports,
  the verifier rebuilds the calendar split from the complete frozen selection
  snapshot before choosing the prefix. The same pure causal service used by the
  runner then replays train, configured validation, buy-and-hold benchmark,
  stress/severe costs, prefix invariance, and lookahead checks. Flat ranking
  metrics, cost evidence, and full trade/equity digests must equal that replay;
  coherent 999-return, benchmark, cost, digest, or lookahead reseals therefore
  block. For schema-10 development reports, the runner first physically omits
  the protected test suffix. It then builds
  `development-selection-prefix-split-v1 / TRAIN_VALIDATION_ONLY_INDEX_SPLIT_V1`
  from the frozen truncated rows and batch split policy, with
  `train_end_index = floor(row_count * train_ratio / (train_ratio + validation_ratio))`,
  `validation_end_index = row_count`, and `test = 0`; the verifier independently
  rebuilds and exactly compares that schedule. This is a deterministic
  within-prefix index split, not the formal calendar boundary reconstructed
  from a complete snapshot, and it cannot freeze candidates or supply fresh
  out-of-sample evidence. The replay uses one frozen parameter identity across
  historical selection checks, so it is neither WFO nor profitability proof
  and grants no paper/live authority.
- Schema-11 adds `strategy-frozen-evaluation-replay-v1` after selection. For
  `FROZEN_TEST_ONCE`, the pure service independently replays configured cost,
  buy-and-hold, and severe-cost results from frozen selection rows and the
  rebuilt boundary, including complete trade/equity digests and every flat
  metric projection; the outer aggregates are then recomputed. For
  `HOLDOUT_CONFIRMATION`, the verifier first rebuilds
  completed-daily alignment from frozen CONFIRMATION rows and frozen data
  policy, exactly compares the reported alignment, explicitly applies the
  frozen split policy to rebuild the schedule, and then replays configured,
  benchmark, severe, temporal, full-confirmation fixed-slice, prefix, and
  lookahead evidence. Schema-11 forbids legacy `source_run_hash`, requires
  exact NOT_RUN alignment/schedule when no candidate exists, and recursively
  blocks canonical authority aliases including `parameterSelectionAuthority`.
  Development remains selection-only. Schema-3 through schema-10 hashes and
  verification semantics remain historically compatible. This proves internal
  consistency of the frozen local artifact, not cryptographic authenticity of
  an external provider or recovery of a pre-alignment source history.
- Schema-10 also carries a self-hashed
  `strategy-selection-alignment-input-v1` snapshot. It records only
  alignment-relevant date/completion projections and binds every dataset to
  `role=SELECTION`, symbol/market/timeframe/source, and its SELECTION-manifest
  hash. The verifier reruns `daily-batch-alignment-v2` from that snapshot and
  the frozen data policy; reported PASS/BLOCK cannot control required
  dataset/cell/ranking coverage. Deleted datasets, wrong roles, source drift,
  and a forged PASS-to-BLOCK plus emptied evidence fail closed. When alignment
  or selection admission is BLOCK, the current writer emits only a sanitized
  failure receipt: it does not generate a research report, complete the formal
  registration, or publish the report pointer. A future terminal FAILED state
  needs a separately anchored receipt schema rather than a weaker verifier.
- The fold summary applies the same fail-closed rule: every `ok=true` fold
  must carry finite return/drawdown values and a non-negative integer trade
  count. Missing, non-finite, pseudo-boolean, or failed fold evidence blocks;
  aggregate trades and worst drawdown become `null` instead of zero/defaults.
- Cross-symbol validation and frozen-test aggregation use the same strict
  metric contract: numeric strings, booleans, negative trade counts, and
  non-finite values are not usable cells. This prevents `int(... or 0)` from
  turning malformed trade evidence into valid sample counts.
- The top paper-status indicator is presentation-only: it stays neutral and
  reads "模拟未授权" even if a legacy/runtime snapshot contains
  `armed=true`. Raw armed state remains audit metadata; it cannot authorize
  paper or live trading. The control center keeps that visible boundary even
  when an upstream snapshot claims `paper_authorized=true`; forward-observation,
  small-capital planning, replay, and audit rows expose only neutral research
  labels while raw statuses remain metadata.
- The market-AI research header calls its waiting condition "研究观察"
  rather than "下一步"; this is descriptive copy only and cannot imply an
  execution action. Risk-engine and order-book strategy hints use the same
  neutral boundary; raw armed/condition flags remain metadata only. The static
`app.js` cache fingerprint is `20260814-single-look-contract-1`.
- The anomaly radar, anomaly detail, and trend cockpit read-only routes finish
  through `market-anomaly-research-projection-v1`. Direction, preference,
  tone, and visible READY-like source states are neutralized in the research
  surface; raw values remain `raw_*` audit metadata and nested execution fields
  are forced false. The projection does not fetch data, write history, rerun a
  backtest, or grant paper/live authority.
- `/api/market/scanner` finishes through
  `market-scanner-research-projection-v1`. Strategy identifiers, actions, risk
  labels, and the "highest opportunity" summary are neutralized for the public
  research surface; raw values remain audit metadata, numeric scores remain
  descriptive scan evidence, and a row click only changes the selected symbol.
  It never auto-applies a strategy or grants paper/live authority.
- The full configuration center routes finish through
  `configuration-research-projection-v1`. Visible configuration states are
  neutral research observations; raw `READY`/`PASS` values remain metadata,
  configuration detail paths and secret values are not projected, and paper,
  live, execution, and automatic activation authority are forced false. The
  apply route only records that configuration was written; it does not grant
  simulation or trading permission.
- The interactive backtest page exposes a neutral robustness/cost evidence
  ledger from the existing temporal-validation report: slice and fold counts,
  cost-stress outcome, look-ahead status, and the same-data risk-control surface
  are descriptive only. Missing values remain unknown rather than zero. The
  risk-control surface covers position/take-profit/stop-loss only; strategy
  signal-parameter stability stays `NOT_CONNECTED` until a frozen research
  report is verified, and this view cannot authorize paper or live trading.
- The frozen internal-pack return-quality band now has an expandable
  validation/test stage strip. It shows stage provenance, sample counts,
  benchmark-excess basis, and statistical-claim status without adding a
  request or recomputing evidence; malformed stage fields fail closed to
  `UNKNOWN`. This is covered by the static evidence contract and frontend lean
  only, not by HTTP/browser runtime acceptance.
- The control center presents market, natural-forward, small-capital-plan, and
  paper-account states as neutral evidence/authority text with a permanent
  permission summary. Its
  "核对当前证据" action refreshes existing snapshots only and must not trigger
  a backtest, strategy doctor, parameter search, or execution workflow.
- The control-center projection recursively forces embedded authority fields in
  component snapshots and recent audit rows to false, recording sanitized
  paths. Only its explicit envelope argument can define effective authority;
  nested component values cannot promote the public response.
- Pipeline summaries and all seven stages use neutral evidence sentences; raw
  PASS/READY values remain metadata only. Paper stays visibly unauthorized
  until effective authority is explicit, while live trading remains hard
  locked or forbidden when protection cannot be confirmed.
- `/api/strategy/war-room`, `/api/strategy/doctor` (including preview),
  `/api/strategy/lab`, and `/api/strategy/compare` finish through pure research
  projections. The lab's
  development heuristic position/target/invalidity values live only under
  `planning_candidate`; legacy operational keys are null, parameter selection
  is false, and the UI may copy values into a research form only as a
  planning observation. Compare scores/probabilities are uncalibrated
  development evidence, and its action/condition fields are descriptive-only.
  None of these endpoints grants paper or live authority.
- `/api/research/panel` also finishes through the pure
  `research-panel-research-projection-v1` boundary. Direction/preference,
  ready-like statuses, tones, and BUY/SELL-like actions are descriptive
  research observations or raw metadata; nested authority is forced false and
  the route does not move its existing market/news I/O.
- The lab also emits `strategy-lab-evidence-boundary-v1`. Parameter plateau,
  cost-stress, and fixed-parameter chronological-slice statuses are explicitly
  `NOT_CONNECTED` until a separately verified frozen research report is wired
  in; the interactive lab must not be described as parameter stability or true
  walk-forward evidence.
- `/api/bot/center`, `/api/bot/scheduler`, the scheduler mutation responses, and
  `/api/strategy/robot-profiles` finish through the pure
  `services/bot_research_projection.py` projection. OWNER/OBSERVER, can-execute,
  armed, recommended, allocation percentages, and PASS-like readiness remain
  raw audit metadata only; the public fields are research roles, descriptive
  states, development scores, or null. The UI calls this research-role
  observation and keeps paper unauthorized and live permanently hard locked.
  The underlying planning mutation is not an order path and is never translated
  into execution authority.
- `/api/strategy/analyze` finishes through the pure
  `services/strategy_analysis_projection.py` projection. Direction, TP/SL and
  nested risk configuration are presented as research planning only; numeric
  price fields are copied under `planning_*`, raw values remain audit metadata,
  probabilities are explicitly uncalibrated, and all paper/live/selection/order
  authority is false. Chart anchors, side insights, and risk preflight consume
  this planning contract instead of coloring or labeling the values as orders.
- `/api/ai/market/dual-analysis` finishes through the pure
  `services/market_ai_projection.py` projection. DeepSeek/GPT directional
  estimates, win rates, support/resistance, and TP/SL are uncalibrated research
  observations; price fields are copied under `planning_*`, raw model payloads
  remain metadata, and all paper/live/selection/order authority is false. The
  market-AI cards use neutral evidence presentation and never treat a model
  response as profitability proof or authorization.
- The legacy DeepSeek GETs `/api/ai/deepseek/analyze`,
  `/api/ai/deepseek/opportunities`, and `/api/ai/deepseek/platform-review`
  finish through `services/deepseek_projection.py`. Direction, confidence,
  opportunity levels, position hints, and actionability are descriptive
  research only; price-like values move under `planning_*`, raw model values
  remain audit metadata, and paper/live/selection/order authority is false.
- `/api/ai/trading-agents/discuss` finishes through the pure
  `services/trading_agents_projection.py` projection, including its streamed
  NDJSON events. Stances are mapped to `RESEARCH_*`, confidence/win-rate values
  are raw uncalibrated metadata, and action/signal/price/position values are
  research labels, raw metadata, or planning-only. Both the event root and
  nested data are projected before streaming. The room and UI remain
  descriptive research minutes; paper authorization, selection, order
  execution, and live authority are always false.
- Control-center response assembly and the market-health authority envelope now
  live in the pure `services/platform_control_center.py` projection module.
  The final natural-forward authority/dashboard projection similarly lives in
  `services/portfolio_forward_projection.py`. Research-context and summary
  response assembly now live in the third pure projection,
  `services/research_query_projection.py`; its root authority is fixed inside
  the function to read-only with live ordering forbidden. Service calls,
  candidate/hash validation, queries, caches, database/file fallbacks, locks,
  and routes remain in `server.py`; the extractions preserve the dual
  market-truth entry points and the latest-order field whitelist.
- The report-root internal-backtest writer emits the current
  `portfolio-internal-backtest-pack-v6` with
  `backtest-return-quality-v3` and frozen
  `portfolio-internal-forward-evidence-v2`. Its content-addressed flat bundle
  contains exactly one compact pack, one detached research document, and one
  detached statistical audit. A generic immutable manifest/publisher binds the
  exact basenames, roles, SHA-256 digests, byte counts, candidate/evidence/pack
  hashes, and bundle hash with no-clobber publication. The loader never globs or
  chooses a newest file: it reads those exact members and rebuilds source and
  numeric semantics from the detached bytes. A contract-valid source-blocked
  diagnostic bundle exposes null/unknown metrics only and never publishes the
  current pointer.
  The portfolio source family is `PORTFOLIO_RESEARCH_PROTOCOL_V1`; strategy
  schema-7 preregistration is explicitly `NOT_APPLICABLE`, so this chain cannot
  be presented as a bound strategy hypothesis. `AVAILABLE` still means only
  that descriptive fields are present, never a strategy pass, profitability
  proof, promotion decision, paper authority, or live authority. Pointer v1 and
  pack v2/v3/v4 retain their frozen historical verifier/hash semantics; v4 keeps
  its embedded-source quality-v2 verification while v5 retains its exact
  detached quality-v3 historical verifier. Pack v6 adds the current frozen
  single-look forward-evidence-v2 coupling. This proves local unkeyed
  self-consistency only:
  `external_anchor_verified=false` and
  `cryptographic_authenticity_proven=false`. An actor able to rewrite and
  reseal the complete identity chain can create a different self-consistent
  artifact; local unkeyed hashes do not authenticate the original external
  frozen file.
- A `portfolio-backtest-pack-pointer-v2` is atomically published at the same
  fixed filename, `current_internal_portfolio_backtest_pack.json`, only for a
  verified report-root v6 bundle. The pointer-v2 field and hash contract is
  unchanged; code activation alone does not reissue an existing pointer. It
  binds the content-addressed bundle
  directory, manifest, exact pack, and pack/evidence/candidate/bundle hashes.
  The read-only `/api/portfolio/backtest-return-quality` route reads exactly
  that pointer and bound bundle; it never globs, chooses a newest file, reads a
  database, or runs candles. The response is a whitelist projection, includes only the
  verified freeze timestamp and content hashes needed for provenance, and
  preserves the pack's own BLOCK/REVIEW status instead of translating verifier
  PASS into readiness. Its current outer schema is
  `portfolio-backtest-return-quality-snapshot-v4`. Only the exact current
  pack-v6/quality-v3/forward-evidence-v2 combination may expose the frozen
  single-look whitelist projection. Legacy pack v2-v5 artifacts retain their
  historical structural verifiers, but a pointer-v2 public load returns
  `UNKNOWN` with quality/forward values null; cross-version, future, or
  forward-missing combinations are also UNKNOWN.
  The projection returns no frozen spec, settlement rows, complete
  source evidence, paths, or complete pack, and explicitly states that the pack
  did not reload the database or independently replay the settlement chain.
  Pointer, manifest, pack, research, statistical, and aggregate bundle reads are
  capped at 64 KiB, 256 KiB, 32 MiB, 256 MiB, 16 MiB, and 304 MiB respectively.
  All use bounded immutable reads before strict JSON or semantic verification;
  duplicate keys, NaN/Infinity, excessive nesting, exact size/hash mismatch,
  symlink/reparse, and Windows case/NFKC/trailing-dot/space/ADS/reserved-name
  aliases fail closed. The generic publisher uses deterministic JSON, UUID
  temporary creation, fsync, and hardlink no-clobber semantics. Explicit
  external `--output` is an immutable legacy-v4 offline export only, never
  publishes a pointer, and any report-root descendant is rejected before build.
  Pointer/pack/bundle and adversarial contracts pass targeted validation. This
  is still not a cross-file transaction or an external authenticity proof.
  Current immutable manifests, v5 detached sources, pointer-v2 artifacts, and
  archive-v3 objects share the pure-stdlib `strict_json_artifact` parser. It
  requires UTF-8 bytes and an object root, rejects duplicate keys at every
  level, non-finite or exponent-overflow numbers, and nesting beyond root=1 / 128,
  while leaving canonical serialization to the owning artifact service.
  Pointer-v1 and ordinary legacy-archive reads deliberately retain their
  historical parser behavior; a v2 pointer cannot fall back through the legacy
  parser. Golden pack/evidence hashes and detached digests are unchanged. The
  scoped cross-check passed 150/150, with three real-symlink cases skipped only
  because the Windows host lacks symlink privilege.
  The public archive verifier also converts a `MemoryError` from any manifest
  or later semantic step into one fixed, path-free BLOCK response. This does not
  claim that a real process-wide OOM is recoverable; it prevents an injected or
  bounded-step memory failure from escaping the verifier contract.
- The current archive writer is `portfolio-evidence-archive-v3` and preserves
  v1/v2 verification compatibility. Its reports tree stores the same exact
  three-member bundle; the single research member is also the replay source and
  is not duplicated. The archive manifest binds pack/evidence/candidate hashes,
  member records, and bundle hash; restore and verification load exact manifest
  paths, rerun the core bundle verifier, and keep all authority false. Archive,
  replay, tamper, missing-member, and legacy cases pass targeted validation.
  No real runtime/SQLite/candle source was read for that evidence.
- V5 makes the persisted pack compact and now builds a borrowed normalized
  semantic view from the same detached parsed objects and exact bytes. It no
  longer creates transient v4 source-document, source-evidence, or
  result-evidence wrappers; the frozen v2-v4 schema, byte, and hash semantics
  remain unchanged. A targeted 8 MiB high-density synthetic JSON `tracemalloc`
  measurement fell from about 4.51x raw bytes to 2.50x. This measures Python
  allocations, not production RSS, and canonical JSON serialization remains a
  peak-memory residual. There is still no real-large-artifact, candle, HTTP, or
  rendered-browser acceptance evidence.
- A v3/v4 forward summary may be `RESEARCH_REVIEW_READY` while the overall pack is
  still `INTERNAL_BACKTEST_BLOCKED` by unrelated evidence. The frontend keeps
  those two layers separate in a compact neutral maturity audit rail; it never
  renders the child state as overall readiness, profitability proof, paper
  authorization, or live authority.
- Strategy backtest preview response assembly lives in the pure
  `services/strategy_backtest_projection.py` module. It deep-copies the upstream
  report, clears `pipeline_run`, and fixes historical/research-only,
  non-profitability, no-parameter-selection, paper-false, and live-false scope.
  Market retrieval and backtest computation remain in `server.py`.
- The interactive backtest page separately presents a neutral development
  evidence ledger. It puts benchmark/excess, cost inclusion, drawdown, sample
  and closed-trade evidence ahead of secondary annualized/win-rate/Sharpe
  metrics; missing evidence is shown as unverified, returns are not direction
  colored, and parameter comparison is explicitly selection-bias-uncorrected.
  A separate evidence strip now fetches the fixed-pointer return-quality GET
  exactly once and never merges it into these interactive metrics. Its pure
  mapper requires verified source/schema, recursively false authority, finite
  numeric-or-null fields, and a recomputable benchmark excess; any mismatch
  or missing freeze timestamp/hash falls back to unverified. This is statically
  contract-tested wiring, not yet an HTTP or rendered-browser acceptance claim.
- The same section now has a neutral attribution spine. It can call two hashes
  the same portfolio candidate only after both the frozen snapshot and current
  natural-forward contracts validate; mismatch and missing evidence are shown
  as separate fail-closed states. The selected strategy/preregistered
  hypothesis is always labelled as not whitelist-bound to the portfolio
  candidate. Visual adjacency is never treated as provenance.
- At viewport widths up to 480px, the static shell must switch to a single
  column: the market rail becomes a compact top navigation band, the market
  list may scroll in two columns, and research-view desktop minimum columns
  must not survive into the narrow layout. This is a responsive information
  architecture contract, not proof of device/browser rendering until a
  browser pass is run.
- Strategy preflight, doctor lifecycle, and research-release stages use
  descriptive evidence labels rather than raw PASS/READY/PAPER_READY text or
  direction colors. Raw values remain metadata for debugging; the preflight is
  never described as paper automation readiness, and live status remains a
  permanent hard lock or protection-unconfirmed block.
- The strategy research desk follows the same neutral contract: signal rows,
  war-room anchors, condition explanations, matrices, timelines, candidate
  strategies, and parallel comparison render action text as a research
  hypothesis rather than an order; score and model-estimate cells stay flat
  and uncalibrated. The command strip names research state, read-only paper
  parameters, and risk evidence instead of execution state or order model.
  Visible labels use observation/research vocabulary instead of entry,
  execution, or trading authority. Raw enums remain only in `data-raw-*` and
  titles; this is a static presentation boundary, not runtime acceptance.
- The `/api/strategy/war-room` route now passes through the pure
  `services/strategy_war_room_projection.py` boundary. Market/strategy/risk
  computation and scheduler access remain in `server.py`; the final payload
  is descriptive-only, recursively false for paper/live/execution authority,
  and rewrites simulation/owner/entry language into research review and
  planning-only terms while retaining raw enums as metadata. The frontend
  mapper recognizes the projected `RESEARCH_*` states and `raw_action` so
  neutral evidence labels remain informative instead of falling back to
  unknown status.
- The `/api/strategy/doctor` and preview routes use the companion pure
  `services/strategy_doctor_projection.py` boundary. Doctor computation,
  pipeline recording, and existing I/O remain in `server.py`; only the final
  response is projected to descriptive `RESEARCH_*` states, with raw paper
  readiness retained as metadata and every paper/live/execution authority
  forced false.
- The small-capital area is evidence-gap first and remains plan-only: displayed
  capital is a nominal envelope, quantity/depth details are opt-in, and the 5%
  amount is only a nominal buffer reference, not an account balance freeze,
  fee, expected spend, paper authorization, or execution instruction. Visible
  gap copy is derived only from a whitelist of already-validated check IDs;
  raw backend `next_action`, unknown IDs, READY-like text, and buy/order wording
  are never echoed. The section keeps one live status region, while the gap and
  permission boundary remain ordinary descriptive text.

## Lean validation policy

Routine development must use the smallest profile that matches the changed
area instead of repeating the full 750-test suite:

```powershell
python run_lean_validation.py --profile safety
python run_lean_validation.py --profile market
python run_lean_validation.py --profile research
python run_lean_validation.py --profile frontend
python run_lean_validation.py --profile core
```

The `core` profile deliberately contains only critical safety, market-data,
research-governance, syntax, and stock-quote checks. It never runs unittest
discovery or a formal/blind research workflow. The full regression is reserved
for a new frozen baseline, broad cross-cutting changes, or a safety-critical
release. A targeted PASS must not be described as a full-regression PASS.
Lean profiles force read-only mode, use a temporary runtime, skip local AI
environment loading, and start child checks from a strict minimal environment
instead of inheriting arbitrary host variables. Protected local configuration,
runtime data, databases, caches, logs, and screenshots are excluded before the
validation manifest reads file content.

Exact deterministic PASS results are stored as a local content-addressed cache.
The default output distinguishes `EXECUTED` from `REUSED`; `--fresh` ignores a
matching cache entry and really executes the selected checks, while `--dry-run`
only reports `WOULD_RUN` or `WOULD_REUSE` and writes nothing. A result such as
`0 executed, 3 reused` must never be described as three checks run in the
current invocation.

These receipts are unsigned local consistency records, not authenticated
attestations. Formal readiness accepts only freshly `EXECUTED` deterministic
engineering evidence. Browser interaction, HTTP 423, service process identity,
network/market observations, and SQLite before/after evidence are always tied
to the current instance and are never reusable. None of these receipts grants
paper or live authority.

Historical G50/G51 reports are reviewed with their existing semantic verifiers;
their falsified strategies are not rerun on the same exposed data. New evidence
should come from newly completed forward bars whenever possible.

Forward observation is incremental by default. Persisted forward status,
readiness, scheduler, ledger-audit, and data-revision identities must form a
complete content-addressed chain before the dashboard may report UP_TO_DATE.
Missing evidence is UNKNOWN or BLOCK, never a zero count. Scheduler `--dry-run`
must return before creating directories, locks, SQLite databases, or status
files; it is a read-only plan preview, not a hidden observer run.

G42 maturity uses the explicit `portfolio-forward-readiness-v2` and
`portfolio-forward-statistical-audit-v1` contracts. Before both the frozen
forward-return and executed-rebalance thresholds are met, the statistical
stage is `NOT_DUE` and no bootstrap PASS is emitted. Once due, the audit must
recompute the paired strategy/benchmark series from the fully verified ordered
settlement chain. It copies the verified historical audit's method, resampling,
block length, confidence, probability thresholds, Bonferroni adjustment, and
selection trial count; only the candidate's preregistered forward observation
floor may differ, and that difference is explicit. The historical audit's
valid BLOCK claim is context, not a substitute for the new forward result.
Legacy readiness keeps its original schema and semantics. The new audit is
portfolio-level natural-forward research evidence only: it always states that
profitability is not proven and grants neither paper nor live authority.

Internal-backtest pack v2 retains its historical promotion semantics. The
current v3 writer and independently dispatched verifier bind the full candidate
spec, verified historical statistical contract, readiness-v2, forward audit,
and hash-bound forward rows/series/stages. Before maturity it is COLLECTING;
a statistically valid negative remains RESEARCH_REVIEW_BLOCKED; a mature PASS
can reach only RESEARCH_REVIEW_READY with manual REVIEW_REQUIRED. Source damage
or binding drift makes the pack itself BLOCK. V3 explicitly says it did not
reload the settlement database or independently replay the chain. Every state
keeps profitability unproven and paper/live authority false.

The latest natural forward result is projected as a sealed, read-only
`latest-forward-observation-receipt-v1`. Current-run records remain separate:
an empty incremental run keeps `processed_count=0` and never replays an old bar,
while the last ledger-audited observation receipt remains visible. Legacy
status artifacts without a receipt are shown as unverified and hidden; a
non-empty receipt with mismatched candidate, date, audit, authority, or content
hash blocks. The control center labels its symbols as observation targets, not
orders, and the receipt can never grant paper or live authority.

The adjacent pair of ledger-audited observations is separately projected as
`forward-observation-change-v1`. The ledger audit seals an ordered observation
chain, and only its latest consecutive pair may produce a verified change.
Insufficient history is explicit and never reported as "unchanged". The UI
shows only whether the observation set changed and how the risk review status
transitioned; it does not expose the comparison as an order, direction signal,
performance claim, paper authorization, or live authority. Legacy artifacts
without this optional evidence remain unverified rather than blocked, while a
non-empty tampered change blocks.

Actual observer subprocess runs are separately recorded as a maximum two-entry
`portfolio-forward-observer-job-receipt-v1` chain. Scheduler heartbeats do not
create synthetic jobs; they carry the last verified chain unchanged. The five
neutral outcomes distinguish newly processed bars, no newly completed bar,
already-accounted work, a verified pre-mutation block, and failure requiring
reconciliation. A block accompanied by ledger movement, a non-PASS audit,
candidate drift, artifact mismatch, or timeout is always a failure rather than
a benign block. A reconciliation-required head blocks the next observer start
instead of silently retrying. Candidate activation changes start a new chain.
The current sealed observer artifact binds both the latest receipt fields and
the preceding receipt head. The parent also seals all receipt-relevant process,
schedule, activation, ledger, and result claims as
`portfolio-forward-scheduler-attempt-evidence-v1` in the same forward artifact,
including timeout, launch-failure, and invalid-child attempts. New scheduler
status artifacts use `portfolio-forward-scheduler-status-v2`; when current
attempt evidence exists, a matching non-empty latest receipt is mandatory, so
an empty chain, v1 downgrade, or truncated failure blocks. Only explicit legacy
v1 artifacts with no current attempt evidence may remain unknown. Receipts and
the dashboard never retain child stdout/stderr, commands, environments, or
paths, and none of these descriptive job results can grant paper or live
authority.

Stock snapshot refresh is coordinated by canonical `symbol + bar + session`
identity. Automatic and manual callers join one in-flight refresh; manual input
may bypass cooldown but never the in-flight or live-trading boundaries. Stale
responses are discarded by current-context checks, refresh failures preserve
last-good data with an explicit degraded status, and routine refresh requests
use `emit=false`. Backend `force/emit` GET requests require a loopback client
and a trusted local browser context; read-only mode still suppresses runtime
mutation. This mechanism has no paper-order or live-order authority.

Small-capital planning is built by a pure, I/O-free planner and displayed by
the existing control-center GET response. A separate public-only OKX SPOT rule
service now binds current symbol, `tickSz`, `lotSz`, `minSz`, capture time, and
content hashes into that plan through a short-lived in-memory cache. `minSz`
means minimum base-asset amount and is never presented as a minimum USD cost.
An additional quantity preview uses only the same trusted in-memory ticker's raw
best ask and one-level ask size; it never falls back to the last trade or client
`price` query. It estimates fixed 10/20 USDT tiers with exact integer-ratio lot
steps and floors base quantity to the public `lotSz`. A documented 5% OKX market-
order risk-check buffer is shown only as a temporary planning amount to reserve
(10.5/21 USDT), never as verified balance, a fee, slippage estimate, expense, or execution proof.
A separate public-order-book service now observes the first 20 standard non-RPI
levels through the existing OKX books route. It preserves decimal text and binds
symbol, exchange timestamp, sequence identifier, receive time, ordering,
non-crossing structure, and a content hash. Concurrent same-symbol requests join
one refresh, while exchange-timestamp regression is rejected. Exact fractional
scanning reports visible quantity, visible-level average price, distance from the
best ask, levels consumed, and coverage for the same 10/20 USDT tiers. The same
snapshot also derives exact 5/10/25 bps midpoint bands independently for each side;
failure to reach a band edge marks that side's total as a visible lower bound, never
as a signal or an extrapolated capacity. REST continuity, a full
book, RPI access, hidden liquidity, account balance, fees, minimum quote cost,
arrival latency, and actual fills remain NOT_CHECKED. The UI clears prior
quantities on symbol changes, stale/regressed evidence, and control-center
failure. The USD capital envelope and USDT tiers remain distinct.
Its absolute dollar guardrails remain illustrative safety envelopes, not venue
rules, expected returns, investment advice, or authorization. Account-specific
fees, minimum quote-currency cost, subaccount/key isolation, circuit breakers,
manual reset, and reconciliation remain `NOT_CHECKED` until current evidence is
explicitly bound. The public rule lookup uses no credentials and cannot grant
paper or live authority.

## Historical defect closure retained from G43

The G43 development work reproduced four fail-closed defects: caller leverage
override, caller direction override, reusable risk approval, and malformed
context exceptions. Their G51 fixes and regression tests are retained in this
saved project; current pass counts and acceptance evidence are recorded only in
`docs/project_status.md`.
