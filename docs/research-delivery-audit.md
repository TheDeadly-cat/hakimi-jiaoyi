# T0/T1/T3/T7 delivery audit — 2026-09-05

Scope: the supplied review, the subsequently supplied
`development_task_outline.md`, and its ZIP README. The ZIP explicitly describes
formula-level spot checks rather than a full repository or Windows runtime run;
this audit does not upgrade that earlier evidence. Current formal delivery is the
installed CLI. Desktop and legacy HTTP service publication are excluded.

## T0: baseline, classification, entry points and rollback

Current source worktree is `cf77`, based on
`f4bfa8adab07a21b66b341a0b8b2fe1804c537d7`. The current implementation is uncommitted.
The integration PR and its original/temporary dirty working directories were
preserved. See [the baseline plan](research-mvp-plan.md) for exact locations and
the accepted local-copy inventory.

Supported software evidence currently concerns the Windows local CLI and its
measured Python environment; desktop release and other platform claims are
separate. Public market access is not treated as redistribution permission.
Data redistribution/commercial-use licensing was not verified here; the study is
local research, not a published data product or public-release authorization.

Read-only `git diff --numstat f4bfa8adab07a21b66b341a0b8b2fe1804c537d7
4fb6d191b282ea9a0d7136f4b94a9e9d49642178` yields the original PR classification:

| Path class | Files | Added text lines | Deleted text lines |
| --- | ---: | ---: | ---: |
| Migration/archive subtrees | 62 | 26,620 | 0 |
| Reference/example subtrees, including their documents | 56 | 107,912 | 0 |
| Test paths and `.test.*` files | 139 | 22,261 | 1,717 |
| Remaining Markdown/docs | 8 | 6,722 | 77 |
| Remaining Python/JS/HTML/CSS/PowerShell/batch source | 164 | 44,636 | 4,378 |
| Configuration/other | 8 | 154 | 10 |
| Total | 437 | 208,305 | 6,182 |

Classification is path-based in the displayed precedence order. Neither the
208,305 total nor the source bucket is a count of new business logic.

| Entry or launcher family | Active dependencies / disposition |
| --- | --- |
| Installed `hakimi-research`, `python -m hakimi_research`, root `hakimi-research.ps1` | Canonical CLI → snapshot/spec → ExperimentRunner → accounting/report/provenance. Formal MVP. |
| `outputs/python_quant_bot/run_bot.py` | Compatibility aliases to the same formal CLI; no `load_stack` or provider-backtest route. Paper/optimize still refuse. |
| `tools/collect_btc_snapshot.py` | Explicit public history GET, raw page admission, snapshot publication. Never imported by formal research/replay. |
| `tools/verify_wheel.py`, root `tests/test_*.py` | Developer package/build/behavior acceptance, independent temporary directories. |
| `tools/run_legacy_reference_checks.py` | Pinned historical source/resources below, outside installed wheel and formal command catalog. |
| `outputs/Hakimi_Trade_V2_Electron_START.bat`, Electron package `start`/`dev` | Electron main → read-only legacy Python server. Preview only. |
| `outputs/QuantX_V2_START.bat`, `start_exchange_terminal.bat/.ps1` | Legacy HTTP/static terminal → legacy services and distinct backtest engine. Excluded from CLI first release. |
| `outputs/Hakimi_Trade_V2_START.bat` | Legacy `hakimi_trade_desktop.py` desktop launcher; not the accepted Electron/CLI path. |
| `start_dashboard.bat/.ps1` | Legacy Streamlit `dashboard_app.py`, outside first release. |
| `outputs/okx_quant_desk_app/START_OKX_QUANT_DESK.bat`, `OPEN_OKX_QUANT_DESK.bat` | Separate legacy `server.mjs`/browser desk, outside first release. |
| `install_dependencies.bat/.ps1`, `install_desktop_dependencies.bat/.ps1`, `find_python.ps1` | Legacy environment helpers; formal wheel does not require these. |
| `build_hakimi_trade_v2.bat/.ps1` | Legacy desktop packaging; not run and not an MVP release proof. |
| `check_environment.bat/.ps1`, `check_btc_daily_database.bat` | Legacy environment/data diagnostics, not run. |
| `build_btc_daily_database.bat/.ps1` | Legacy daily-data collection/build path, outside the fixed spot/1h import flow. |
| `install_portfolio_forward_task.ps1`, `install_portfolio_forward_performance_task.ps1`, `install_portfolio_forward_backup_task.ps1`, `install_portfolio_forward_watchdog_task.ps1` | Legacy scheduled-task installation, not run or authorized by this delivery. |
| `tools/set_futu_opend_credentials.ps1` | Legacy credential-management helper, outside first release and not invoked. |

Delivery boundaries are CI/catalog, accounting semantics, packaging/provenance,
snapshot/Runner, consumer restrictions, and descriptive study artifacts. Their
dependency order is T0 → T1 → T2/T3/T4 → T5 → T6 → T8, with T7 parallel. No nine-PR
split is required. There are no new published PR commits to claim independently
merged. A future reviewer can separate those boundaries, each with its listed
behavior checks. Rollback must be file-specific and preserve unrelated dirty
work, old snapshots and reports; no reset/clean/force-push is part of this plan.
Older result semantics remain explicitly legacy. Restoring a workflow or facade
must never remove the permanent execution locks to obtain a pass.

## T1: exact coverage and gate

Python owns the canonical definitions in `capability_definition.py`.
`tools/generate_product_capabilities.py` generates the committed packaged JSON
projection; CI runs its byte-exact `--check`, and Git fixes its LF line endings.
Node reads the generated definition and Python tests compare both projections. Exact
hard-coded execution locks independently reject authority/status escalation; the
JSON cannot grant execution authority. Known dossier fixture drift in the old
integration test is corrected only in memory from that pinned Python catalog;
all original negative and authority assertions execute unchanged.

Seven independent required domains are configured. `research-required` uses
`if: always()` and an exact dependency set. It rejects failure, cancellation,
unexpected skip, missing/invalid result or extra job identity. There is no
`continue-on-error`; workflow-level path filters are removed. A canceled workflow
cannot produce a successful required gate, even if cancellation prevents its
final job from starting. Python 3.14 and Node 22 are explicitly selected.

Read-only official GitHub ref queries confirmed the configured action tags exist:
`actions/checkout@v7` → `3d3c42e5aac5ba805825da76410c181273ba90b1`,
`actions/setup-python@v7` → `5fda3b95a4ea91299a34e894583c3862153e4b97`,
`actions/setup-node@v7` → `820762786026740c76f36085b0efc47a31fe5020`.
Commands were `gh api repos/actions/<action>/git/ref/tags/v7 --jq '.object.sha'`.
These observations prove tag existence, not a run of the unpushed workflow.

| Current behavior/tests | Required domain | Scope of evidence |
| --- | --- | --- |
| Workflow/gate, capability source/projection, canonical CLI/config/data/core migration, architecture/authority contracts | `python-contracts`; 23 explicit modules in workflow | Explicit subset, not all repository tests |
| Existing `examples/deterministic_experiment/verify.py` and frozen-protocol unit tests | `deterministic-references` | Current available input identity and corrected dormant protocol |
| `tests/test_experiment_runner.py` | `mvp-contracts` discovery and installed-wheel discovery | Snapshot admission, scoring/causality, CLI workflow, report consistency, actual offline replay |
| `tests/test_dataset_versions_csv.py`, `tests/fixtures/dataset_snapshot_v1.json` | Same two discovery paths | Immutable revision/CSV metadata and older-format compatibility |
| `tests/test_research_accounting.py`, `tests/test_independent_ledger_reconciliation.py` | Same two discovery paths | Numerical ledger, fees, partial exits, independent reconciliation, risk/model semantics |
| `tests/test_packaging_provenance.py` | Same two discovery paths | Failed Git queries, measured installed versions, build/source bytes |
| `tests/test_report_persistence.py` | Same two discovery paths | Concurrent writes, no-overwrite/idempotence, process interruption and disk/publish failure |
| `outputs/python_quant_bot/tests/test_research_management_boundary.py` | `python-contracts` | Retired handlers stop before request-body/sensitive work; preserved status callbacks |
| Current `backend-runtime-contract.test.js`, `desktop-security-policy.test.js`, `tools/research-ci-gate.test.js` | `electron-capability-contract` | Exact read-only health, external navigation/debug/process ownership, executable aggregate gate |
| Current `chart_controller.test.js`, `evidence_presentation.test.js` | `market-data-renderer` | Current neutral display and chart contracts |
| Ordinary wheel + full root suite outside source | `package-install-smoke` Windows/Ubuntu matrix | Package behavior, not desktop cross-platform acceptance |

This table names every new root safety/provenance/report test file. It does not
claim that all 139 original integration test files or all 437 PR files were run.

### The five original reference checks

The historical job checks out immutable
`4fb6d191b282ea9a0d7136f4b94a9e9d49642178` with all original `src`, `examples`,
`archive` and legacy builder dependencies. It runs from that source's `src`
directory, with no current-core import or reference rewrite. This preserves
meaningful old-version replay alongside separate current-core numerical proof.

| Historical command | Required source/resource family | Result |
| --- | --- | --- |
| `python -B -m hakimi_research frozen-benchmark` | `deterministic_frozen_benchmark.py`, frozen v2 fixture, retained prior versions/builders | PASS |
| `python -B -m hakimi_research strategy-family-benchmark` | `deterministic_strategy_family_benchmark.py`, family v1 fixtures and frozen dependency | PASS |
| `python -B -m hakimi_research strategy-robustness-benchmark` | `deterministic_strategy_robustness_benchmark.py`, robustness v1 fixtures/builders | PASS |
| `python -B -m hakimi_research strategy-statistical-correction-benchmark` | Default statistical-correction verifier and its preserved versioned fixtures/builders | PASS |
| `python -B -m hakimi_research strategy-research-dossier` | `deterministic_strategy_research_dossier_v1.py`, dossier receipts/Markdown/fixtures | PASS |

The same pinned job runs the original backend-runtime test with only its fixture
projected from Python, `research-capability-lock.test.js`, and
`market_data_research_projection.test.js`. All three passed. The renderer reported
`NETWORK_CALLS=0` and `RUNTIME_MUTATIONS=false`. The replay helper checks a clean
pinned checkout before and after. Its output says `current_core_equivalence=false`;
these results cannot prove the corrected core matches old formulas or promote
historical benchmark commands into the installed MVP.

Local historical source:
`%TEMP%/hakimi-legacy-reference-cuyhu3us`.
Receipt and five raw JSON receipts:
`%TEMP%/hakimi-legacy-reference-evidence-cuyhu3us/legacy-reference-replay.json`.

Exact harness command from the current checkout:

```text
python -B tools/run_legacy_reference_checks.py --legacy-root <pinned-checkout> --output-dir <separate-evidence-directory>
```

### Local and remote observations

The final current 23-module Python CI command ran **213 tests successfully**
(15.630 seconds), after preserving the historical strategy hashes while testing
the deliberately evolved behavior, adding the generated projection LF rule, and
rejecting Frozen ranking in the active developer manifest. Resealing a Frozen
manifest cannot grant ranking; Validation still requires verified protocol
evidence and never grants parameter-selection authority.
The current
input verifier passed and frozen protocol ran 15 tests successfully. The first
full root run after admission/report corrections passed 49 tests; subsequent
expanded-root validation passed **69 tests** both in the root acceptance and the
final independently installed wheel. Current Electron/gate/renderer commands
and `npm.cmd run check` passed. Five HTTP method tests plus eight nearest
HTTP/SQLite read-only tests passed. Those are overlapping scopes, not additive
coverage claims.

Local editable-domain Python:
`%TEMP%/hakimi-ci-domain-check-cyw_1ep5/Scripts/python.exe`, with the five exact
runtime dependencies checked and `pip check` successful. It reused installed
system packages and is not a fresh-wheel isolation proof. Exact module arguments
were read from the current workflow's `Run complete research-only Python contracts`
step; no module list was silently shortened after a failure.
Actual local runtimes were Python **3.14.6** and Node **24.16.0**. Local Node checks
must not be relabelled Node 22 execution merely because CI requests Node 22.

Read-only `gh pr view 1 --json url,headRefOid,isDraft,state,statusCheckRollup`
observed [PR #1](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/1) OPEN/Draft at
`4fb6d191b282ea9a0d7136f4b94a9e9d49642178`.
[Run 33816097849](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/33816097849)
remains FAILURE, completed `2026-09-03T23:08:26Z`. No commit, push, PR edit, merge,
workflow dispatch or required-check configuration was performed. Current local
passes are not remote CI green. Required branch checks require the maintainer's
separate authorization and the exact published-SHA run.

## T3: installation and platform evidence

The console entry point, packaged resources, independent output directory and
atomic no-replace persistence are implemented. `tools/verify_wheel.py` builds a
fresh staged wheel, installs into a venv with no system site packages, clears
`PYTHONPATH`/`PYTHONHOME`, checks build and dependency identities, then runs the
entire root suite outside checkout. The final receipt is the authoritative proof;
editable tests do not substitute for it. Historical developer references are
outside the wheel and outside the formal command menu.

The final Windows acceptance after the Frozen-ranking correction **passed 69/69 installed tests**
(13.221 seconds) under an actual
Chinese-and-space path. The retained final receipt is
`C:/Users/Administrator/AppData/Local/Temp/Hakimi 最终 安装 验证 20260905 0740435a80f64cf8b389ba95b54654e4/wheel-acceptance.json`.
It records version `0.2.0`, non-editable installation, no system site packages and
no `PYTHONPATH`. The source content SHA-256 is
`753c2cab0b0b6fd6c41eae3a109342bb5523fd3286bd5e0138265c1163b843e0`;
wheel SHA-256 is
`30dd4e02225cd72242f157f49f36e65504922c75f1fb94ece5f54f8af0168bc7`.
The installed `hakimi-research.exe list-strategies` also passed from its
`outside-checkout` directory, returned all eight strategies, and kept
`parameter_selection=false`. Earlier wheels remain preserved and are superseded
by this source identity at that validation step. Any subsequent package-source
correction requires another accepted wheel and updated study provenance; the
receipt is evidence only for its recorded source hash, never for later edits.

Linux package CI is configured with
`ubuntu-latest`, `fail-fast:false`, alongside Windows. Local WSL is unavailable;
actual Linux validation is **NOT_RUN** pending a runner execution. No desktop
cross-platform claim follows from this matrix.

## T7: consumer and service scope

The accepted consumer is CLI `report-show`: the same versioned report validator
as the Runner/replay, explicit local file input, bounded JSON read, no server
import/start or account/Provider action. It does not modify the report. Output
prefix/artifact IDs reject path traversal; the output root is explicitly chosen
by the local user. A CLI user's chosen input file is not a remotely accessible
report-serving root.

The optional old service is **not published in the MVP**. Existing loopback Host,
Origin checks and request-size controls are documented in
[consumer boundaries](research-consumer-boundary.md). It does not currently have
a newly accepted session-authentication/report-root HTTP contract. Those service
release requirements therefore remain **NOT_APPLICABLE to the CLI-only release /
NOT_ACCEPTED for a service release**, not silently passed. No first-release GUI
report viewer is being claimed; UI/CLI visual interpretation equivalence is
**NOT_RUN** and GUI remains excluded.

Existing Electron isolation settings remain enabled; protocol/target validation
and packaged-debug disablement have pure callback tests. A conflicting existing
listener is never automatically terminated. Only a still-live direct child
handle owned by the shell can be stopped; exited/signaled/reused-PID candidates
are rejected. The legacy port-based stop-script generator now fails closed.
Stopping a PowerShell wrapper does not claim cleanup of all of its descendants;
manual service resolution remains necessary when a listener remains.

Eight code-worker/runtime-key/Futu management paths are unregistered and rejected
before sensitive work, including direct dispatcher calls. This is enforced in
server code, not merely hidden controls. No HTTP listener, GUI, real management
request, Provider or trading account was used to validate those restrictions.
Packaged Electron runtime/debug-listener observation itself is **NOT_RUN**, so
the code-level fix is not a desktop-release acceptance claim.
