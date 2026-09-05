# Integration and GitHub publication

> Historical integration snapshot for the first MVP publication. Current build,
> CI, branch protection and research evidence are indexed in
> [CURRENT_STATUS.md](../CURRENT_STATUS.md).

This change integrates the completed Windows CLI MVP from commit
`c6399410824a40d07c20e7e66b8d8de7584253c8` with the existing
`codex/research-platform-hardening` branch. The original development history and
Draft PR are preserved; this is an ordinary update, not a rewrite of `main`.
The source MVP delivery documents describe the earlier local acceptance snapshot,
including local-only artifacts; those documents do not themselves assert a newer
remote CI result.

## Preserved boundaries and compatibility

- The development branch's archived paper facade, disabled execution routes and
  stock-candle calendar/completed/source producer chain are retained.
- Default read-only operation and retired management routes are added to the
  canonical HTTP policy and its compatibility shim.
- Formal accounting/scoring/data/CLI semantics come from the tested MVP. Old
  v1/v2 report consumers retain versioned protocol functions and unchanged
  protocol hashes; both old and new persistence use atomic no-replace writes.
- The wheel has an explicit `runtime-files.json` closure. Repository-only
  terminal/configuration/reference modules remain in source control, but are
  not accidentally shipped as broken installed commands. Installed identities
  reject unexpected/missing runtime files; source-checkout identities explicitly
  cover that same declared runtime closure.
- The repository-only signature handoff test is preserved under
  `tests/repository_only`, with its old import/function names updated to the
  existing shortened implementation names. Its 13 assertions/tests execute
  separately in CI with the explicit developer-only cryptography dependency.
- Ten archived source files were recovered from the original c35d worktree with
  exact hashes matching their existing assertions. Some original mixed/CRLF
  bytes had been normalized in Git; other copies changed during checkout.
  Every restored file differs from its previous checkout copy only in line
  endings. No expected hash was replaced. Per-file `-text` attributes retain
  the original bytes through staging and subsequent checkouts.

The new package boundary changes the aggregate source identity. Earlier local
wheel and real-study receipts remain valid evidence for their recorded source
snapshot; they must not be relabelled as receipts for this integrated build.
No new public-data collection, market study, account connection or service
startup was performed during publication.

## Verification scope

The integrated ordinary wheel passed 79 tests in an isolated environment outside
checkout. Integration-specific HTTP, archived-paper and daily-candle contracts
passed 61 tests, and the repository-only handoff suite passed 13 tests. These
scopes overlap other current contracts and are not a whole-repository coverage
count. The CI workflow retains seven mandatory independent domains, adds the
integration tests to its Python domain, and runs package acceptance on Windows
and Ubuntu.

Read the live [PR checks](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/1/checks)
for the published commit's remote result. A successful local build or Git push
alone is not CI-green. PR readiness, merge, GUI/service release and execution
permission remain separate decisions. Paper/live/order permissions remain false.

Local wheel/data/report files under ignored `artifacts/` are not uploaded by
this source update. Use the documented build and explicit fixed-snapshot import
workflow to reproduce software acceptance. Public distribution of stored market
data or binary releases is not implied by this repository update.
