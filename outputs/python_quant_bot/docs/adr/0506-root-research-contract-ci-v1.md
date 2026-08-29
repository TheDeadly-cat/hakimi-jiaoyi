# ADR0506: Root Research Contract CI v1

## Status

Accepted as a repository-level source contract. The first remote run,
`33257858701`, failed before source materialization because Windows Git could not
create two tracked long-path files. That run is failure evidence, not contract
test evidence. This revision adds the bounded checkout prerequisite; its remote
status remains separate until a later run completes. Run `33258057373` then
reached the deterministic verifier and exposed a platform-dependent config
digest; ADR0505 now fixes the fixture byte contract at LF.

## Context

The repository had no workflow under the root `.github/workflows` directory, so
the prior source releases correctly reported zero Actions runs. ADR0505 provides
an exact dependency lock and a deterministic input-identity verifier, but neither
was consumed by repository CI.

## Decision

Add `.github/workflows/research-contracts.yml` with the following fixed scope:

1. In the ephemeral Windows runner, enable Git long-path handling from the empty
   workspace before checkout.
2. Activate only for relevant pushes, pull requests, or explicit manual dispatch.
   The root `.gitattributes` is an explicit relevant path.
3. Grant only `contents: read` and disable persisted checkout credentials.
4. Use Python 3.14 and the exact `requirements.research.lock` closure.
5. Run `pip check`, the deterministic identity verifier, and eleven explicit
   research contract modules.
6. Use a 15-minute timeout and cancel superseded runs for the same ref.

The action major versions are `actions/checkout@v7` and
`actions/setup-python@v7`. They are source workflow dependencies, not application
runtime dependencies, and remain independently reviewable in this file.

## Fail-closed boundaries

- No schedule, secret reference, cache, service, browser, dashboard, package
  publication, or deployment step exists.
- Long-path enablement does not omit, rename, sparse-checkout, or otherwise avoid
  any tracked source file; it only permits checkout to materialize the committed
  tree on the ephemeral Windows runner.
- CI activation includes the exact fixture byte-normalization contract, so a
  `.gitattributes` change cannot silently bypass the verifier.
- The workflow does not invoke `run_bot.py`, any paper/live path, or an order path.
- Unit tests use synthetic/in-memory fixtures and contract-only consumers. They
  are not a formal backtest, frozen-OOS result, cost-stress result, or profit proof.
- A locally valid workflow is not CI-green evidence. Only an actual remote run
  can establish its remote status.
- The single-look evidence chain, legacy pack-v5 UNKNOWN reads, pointer-v2 no-
  reissue rule, and all execution-authority locks remain unchanged.

## Consumer-first order

1. Pin the active dependency closure (ADR0505).
2. Add the deterministic identity verifier (ADR0505).
3. Enable Windows Git long paths before checkout without broadening credentials.
4. Add a root workflow that consumes both without invoking product entrypoints.
5. Add a static adversarial contract that prevents future authority expansion.
6. Obtain a separate remote run before making any CI status claim.

## Local acceptance target

- Python syntax for the new contract test: PASS.
- Targeted contract suite including CI, migration, and frozen-evaluation contracts:
  90/90 PASS.
- Deterministic input verifier: 8/8 PASS.
- Workflow static authority and checkout matrix: 4/4 PASS.
- `git diff --check`: PASS.
- Remote run `33257858701` is FAIL at checkout. Run `33258057373` is FAIL at the
  old deterministic verifier and ran no unittest contract suite. The corrected
  revision remains UNKNOWN until a separate run completes.
