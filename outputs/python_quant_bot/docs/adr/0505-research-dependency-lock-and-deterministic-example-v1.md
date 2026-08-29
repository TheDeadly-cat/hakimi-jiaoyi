# ADR0505: Research Dependency Lock and Deterministic Example v1

## Status

Accepted for the active local historical-backtest research surface.

## Context

`reproducible-experiment-manifest-v1` correctly blocks an experiment when the
dependency description is not fully pinned. The existing `requirements.txt` is
an intentionally broad optional dependency inventory and contains range pins,
so renaming or treating it as a lock would create false reproducibility evidence.

The repository also lacked a source-controlled example whose identity could be
checked without network access, cache state, services, or a performance run.

Remote run `33258057373` later proved that the initial config digest described a
local CRLF worktree rather than the canonical Git blob. The dataset digest was
already canonical. Platform-dependent checkout bytes are not reproducible input
identity and must fail closed rather than be treated as equivalent.

## Decision

1. Add `requirements.research.lock` for the recursively resolved dependency
   closure of the supported historical-backtest CLI: NumPy, pandas,
   python-dateutil, six, and tzdata.
2. Make the experiment manifest prefer that scoped lock over the optional
   dependency inventory.
3. Add `examples/deterministic_experiment` with synthetic CSV data, a local-only
   config, an identity-only expected result, and a standard-library verifier.
4. Bind all three identity-bearing example files to `text eol=lf` in the root
   `.gitattributes`, and make that file a CI activation path.
5. Keep the example result free of return, PnL, Sharpe, drawdown, or other
   performance fields. All authority fields remain false.

## Consumer-first activation

1. The existing manifest consumer recognizes the new lock name.
2. The verifier consumes the checked-in example and fails on identity drift.
3. The contract test accepts the exact LF attributes before accepting the input
   hashes, local-only config, and permanent authority locks.
4. The root CI workflow reacts to changes in either the fixtures or their byte
   normalization contract.
5. Documentation advertises only identity reproducibility, not strategy quality.

## Fail-closed behavior

- A missing, changed, or non-exact lock remains a reproducibility blocker.
- A CRLF or otherwise non-canonical identity-bearing fixture remains an input
  identity blocker even when its parsed JSON or CSV values are equivalent.
- A dirty or unidentified Git worktree remains a reproducibility blocker.
- The example does not become ranking input and cannot grant parameter-selection,
  paper, live, order, or profitability-proof authority.
- Optional desktop, exchange, broker, and packaging dependencies are outside this
  scoped lock and cannot silently inherit its claim.

## Non-goals

This ADR does not run or publish a strategy backtest, establish frozen-OOS
evidence, perform cost stress, prove profitability, enable paper/live trading, or
change any single-look evidence-chain contract.

## Acceptance evidence

- Affected Python syntax: 2/2 PASS.
- Targeted architecture, safety, backtest, manifest, CI, and lock contracts:
  90/90 PASS.
- Deterministic example identity verifier: PASS (8/8 checks).
- JSON parsing: 3/3 PASS.
- Canonical fixture byte matrix: 3/3 LF-only PASS.
- `git diff --check`: PASS.

Remote run `33258057373` is FAIL at the old byte-identity verifier and ran no
unittest contract suite. The corrected revision remains UNKNOWN until a separate
run completes.

The dataset SHA-256 is
`0a76f74772bd9830428684d90bd72578ce828ef47b04102dedead3135a80e23a` and the
config SHA-256 is
`5ded5c5f350bcfbd42eb5a782e9064024f9c5a34bc9d20b113ab121de9fda82f`.
