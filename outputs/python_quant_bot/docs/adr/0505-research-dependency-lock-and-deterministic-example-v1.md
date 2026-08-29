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

## Decision

1. Add `requirements.research.lock` for the recursively resolved dependency
   closure of the supported historical-backtest CLI: NumPy, pandas,
   python-dateutil, six, and tzdata.
2. Make the experiment manifest prefer that scoped lock over the optional
   dependency inventory.
3. Add `examples/deterministic_experiment` with synthetic CSV data, a local-only
   config, an identity-only expected result, and a standard-library verifier.
4. Keep the example result free of return, PnL, Sharpe, drawdown, or other
   performance fields. All authority fields remain false.

## Consumer-first activation

1. The existing manifest consumer recognizes the new lock name.
2. The verifier consumes the checked-in example and fails on identity drift.
3. The contract test accepts the lock closure, preference order, input hashes,
   local-only config, and permanent authority locks.
4. Documentation advertises only identity reproducibility, not strategy quality.

## Fail-closed behavior

- A missing, changed, or non-exact lock remains a reproducibility blocker.
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

- Python syntax: 15/15 PASS.
- Targeted architecture, safety, backtest, manifest, and lock contracts: 64/64 PASS.
- Deterministic example identity verifier: PASS (8/8 checks).
- JSON parsing: 3/3 PASS.
- `git diff --check`: PASS; line-ending notices are non-error working-tree warnings.

The dataset SHA-256 is
`0a76f74772bd9830428684d90bd72578ce828ef47b04102dedead3135a80e23a` and the
config SHA-256 is
`efc3db26d8bdc0fd2da27cf16ff136fd97ea09b1a6cdc958184a5f6c61a0aa30`.
