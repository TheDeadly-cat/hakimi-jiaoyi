# ADR0506: Root Research Contract CI v1

## Status

Accepted as a repository-level source contract. Remote execution evidence is
separate and remains unavailable until a commit containing this workflow is
pushed and GitHub Actions creates a run.

## Context

The repository had no workflow under the root `.github/workflows` directory, so
the prior source releases correctly reported zero Actions runs. ADR0505 provides
an exact dependency lock and a deterministic input-identity verifier, but neither
was consumed by repository CI.

## Decision

Add `.github/workflows/research-contracts.yml` with the following fixed scope:

1. Activate only for relevant pushes, pull requests, or explicit manual dispatch.
2. Grant only `contents: read` and disable persisted checkout credentials.
3. Use Python 3.14 and the exact `requirements.research.lock` closure.
4. Run `pip check`, the deterministic identity verifier, and eleven explicit
   research contract modules.
5. Use a 15-minute timeout and cancel superseded runs for the same ref.

The action major versions are `actions/checkout@v7` and
`actions/setup-python@v7`. They are source workflow dependencies, not application
runtime dependencies, and remain independently reviewable in this file.

## Fail-closed boundaries

- No schedule, secret reference, cache, service, browser, dashboard, package
  publication, or deployment step exists.
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
3. Add a root workflow that consumes both without invoking product entrypoints.
4. Add a static adversarial contract that prevents future authority expansion.
5. Obtain a separate remote run before making any CI status claim.

## Local acceptance target

- Python syntax for the new contract test: PASS.
- Targeted contract suite including CI, migration, and frozen-evaluation contracts:
  89/89 PASS.
- Deterministic input verifier: 8/8 PASS.
- Workflow static authority matrix: 3/3 PASS.
- `git diff --check`: PASS.
- GitHub service-side YAML ingestion and execution remain NOT_RUN/UNKNOWN until
  this workflow is separately authorized for commit/push and GitHub creates a run.
