# ADR0482: Idempotent replay-cursor synthetic fixture setup v1

## Status

Accepted as a test-only performance optimization. It changes no production contract, schema, gate, evidence, engine, server, CLI, UI, runtime, paper, live, execution, profitability, or trading behavior.

## Context

Targeted ADR0478 through ADR0481 processes each spent about 39 seconds before assertions. Direct timing separated import at 0.964 seconds, final exact evaluation at 0.012 seconds, and nested fixture construction at 38.571 seconds.

Layer timing in one process showed repeated setup costs of 38.868 seconds for ADR0478, 38.188 seconds for ADR0479, 38.603 seconds for ADR0480, and 40.472 seconds for ADR0481, totaling 156.132 seconds. A second split measured signed-registration setup at 0.006 seconds and the provider/CAS fixture at 40.073 seconds.

Profiling confirmed that the old historical-coverage/CAS synthetic fixture rebuilds a deep exact-verification chain. The new ADR0478-0481 production evaluators were not the latency source; final ADR0481 evaluation took about 0.012 seconds.

## Decision

Make five synthetic `setUpClass` methods idempotent within one Python process:

- replay-cursor provider fixture;
- ADR0478 signed-receipt fixture;
- ADR0479 conformance fixture;
- ADR0480 transcript-binding fixture;
- ADR0481 content-verification fixture.

Each class checks its own `__dict__` for `_fixture_setup_complete_v1`. The sentinel is written only after all fixture material is successfully built. Exceptions are never cached. Repeated setup reuses the same class-owned immutable or read-only fixture material.

The cache is process-local, has no filesystem or runtime persistence, and is not shared across Python processes. It does not cache production verifier outputs or bypass any assertion inside the first successful build.

## Safety invariants

- failed setup remains retryable;
- subclass inheritance cannot accidentally satisfy the guard because the check uses `cls.__dict__`;
- random synthetic keys remain fresh per process;
- mutation tests continue to use copies or per-test values;
- exact evaluators continue to rebuild their expected evidence;
- authority remains fail-closed.

## Validation plan

1. Compile all five changed fixtures and the cache contract test.
2. Run ADR0478-0481 plus the cache contract in one process.
3. Measure the same four sequential setup calls after the change.
4. Verify repeated setup preserves material identity and final exact ADR0481 evidence.
5. Confirm protected frontend hashes remain unchanged.

No historical market data, formal backtest, provider, service, browser, scheduler, runtime asset, paper path, or live path is used.
