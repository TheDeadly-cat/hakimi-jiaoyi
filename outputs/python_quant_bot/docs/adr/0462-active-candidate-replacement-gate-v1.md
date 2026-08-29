# ADR 0462: Active candidate replacement gate v1

- Status: Accepted
- Date: 2026-08-25
- Scope: Explicit local active-candidate activation lifecycle

## Context

`activate_portfolio_candidate` wrote the active registry without checking an
existing active candidate. In an isolated synthetic sequence, a second valid
candidate returned `ACTIVATED`, replaced the first registry, and became the
candidate returned by the loader without any retirement receipt.

## Decision

Introduce `active-candidate-replacement-gate-v1` as a compatible v3
sub-contract:

1. New active registries declare the replacement-gate version.
2. A different candidate cannot replace a valid active candidate. Explicit
   retirement is required first.
3. An exact retry with the same candidate file, file hash, robustness document,
   and experiment-completion receipt returns `ALREADY_ACTIVE` without rewriting
   the registry.
4. Invalid or unreadable existing registries are never overwritten.
5. Immediately before a permitted write, the function confirms that the target
   registry is still absent or byte-identical to the previously verified retired
   registry.

The outer `active-portfolio-candidate-v3` version remains unchanged. The check
prevents sequential replacement and narrows write races, but it is not presented
as a cross-host distributed lock.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| First isolated activation | ACTIVATED with gate v1 |
| Different candidate before retirement | BLOCK, original remains active |
| Exact retry | ALREADY_ACTIVE, registry bytes unchanged |
| Invalid existing registry | BLOCK, bytes unchanged |
| Registry changes after validation | BLOCK before write |

## Boundaries

- Tests use only synthetic candidates and isolated temporary directories.
- No user registry, formal candidate, or retirement artifact is read or changed.
- No market task, backtest, service, browser, scheduler, runtime database, paper
  order, or live order is started.
- Active research remains research-only; paper/live remain unauthorized.
