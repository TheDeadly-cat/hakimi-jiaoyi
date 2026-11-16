# WIP: factor-stage4 code handoff (not for merge)

This directory preserves an incomplete, unverified code draft for the original project conversation to review. It does not install the feature or change any production source file. Do not merge, deploy, or treat this as a working application.

## Two different baselines

- This handoff branch starts from remote `main` at `e33c1ef324f142be3889bbef44b663b6b5f54a1a`.
- The enclosed patch was generated against the separate local candidate `62d5451cf74a27dd9b25fbf6565390d5895eacce`. GitHub reported that this commit was not present in this repository on 2026-11-16.
- These are not interchangeable baselines. The patch was NOT checked against remote main, PR #31, or the current original-project working tree. Do not apply it there blindly.
- Local repository ownership checks were not disabled. No original-project files, protected branches, existing PRs, or sealed candidates were changed by this handoff.

## Included and deliberately excluded

`code-only.patch` contains six code-file changes from the original seven-file draft:

1. `index.html`: three insertion points for a research entry, stylesheet, and script.
2. `factor-research-entry.js`: an in-terminal dialog draft that carries the selected symbol.
3. `factor-research.html`
4. `factor-research.css`
5. `factor-research.js`
6. `factor-research-model.js`

All paths in the patch are under `outputs/python_quant_bot/exchange_terminal/static/`. The patch is stored here as review material, not applied to those paths.

The seventh file, `factor-research-binding.v1.json`, is wholly excluded. It contains private file-service identifiers and research provenance whose public redistribution was not established. No synthetic replacement or success-looking sample has been invented. The code still requires that file and will report a load/validation failure without an appropriately reviewed binding. This is therefore NOT a complete seven-file implementation.

Also excluded: runtime executables and dependencies, browser/app profiles, raw logs and diagnostics, private source artifacts, credentials, local machine/user paths, source-copy inventories, and unrelated local changes. Only the code patch, this note, and a public hash/verification manifest are included.

## Known failure and verification limits

The earlier isolated launch failed because the backend could not import `_canonical_source`, then `exchange_terminal`. Both modules existed locally; the isolated launcher set PYTHONPATH to `source/src` without `source/outputs/python_quant_bot`. That search-path defect has NOT been fixed by this handoff.

The Electron observation only reached the boot page. It does not prove that the terminal or the research dialog worked. Computer-control approval timed out during investigation, and the original worker later reported the Windows environment unavailable. A subsequent read-only inspection could read the files again, but the failed test instance's current lifetime was not established and it was not terminated by this handoff.

Checks performed while preparing this artifact:

- All original seven candidate file hashes still matched the existing local manifest.
- The local baseline index hash was verified. The six-file patch passed `git apply --check` on a disposable fixture containing that baseline index.
- Applying it to that disposable fixture reconstructed all six included target file hashes exactly, with `core.autocrlf=false` and `core.eol=lf`. The patch SHA-256 is recorded in `manifest.json`.
- The three included JavaScript files passed syntax-only checks with Node.js v24.16.0.
- No backend restart, Electron/UI acceptance test, behavioral test, or full repository test suite was run for this handoff. Any CI result for this documentation branch cannot validate the enclosed, unapplied feature.

Not verified: symbol switching, repeated opening and closing, stale/unknown data, dialog focus and keyboard behavior, normal application startup, or compatibility with any remote baseline. The earlier worker reported existing desktop security-policy unit tests passing, but those were not rerun here and do not validate the new dialog.

## Required before implementation

1. Recover and verify the intended integration baseline, including its relationship to the local 62d5451 candidate and the remote branches. Preserve the original project's uncommitted work.
2. Privately review or regenerate an authorized binding dataset. Do not restore private identifiers into this public repository without appropriate approval.
3. Reconcile the code changes in a separate development checkout; review all existing draft assumptions and stale-data behavior.
4. Correct and verify the backend launch environment in that isolated checkout.
5. Run the relevant unit, integration, UI, Electron lifecycle, and repository-required checks against the final code. Record failures and not-run checks separately.
6. Prepare a separate reviewed implementation change. This draft handoff is not approval to merge, deploy, trade, or enable execution.
