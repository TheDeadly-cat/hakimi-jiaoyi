# ADR 0437: Anti-Replay Registry V2 Application Port Migration V1

- Status: Accepted
- Date: 2026-08-24
- Predecessors: ADR 0435 and ADR 0436

## Context

Anti-replay V1 already has an application-owned canonical port, but V2 remained in the mixed interfaces package. Two application producers imported that V2 module directly: the source-baseline nonce namespace preregistration and its provider-conformance plan.

V2 also imported V1 through the legacy interfaces shim. A correct migration must move V2 inward and retarget that dependency to canonical V1 rather than copying the old reverse dependency into the application port.

## Decision

1. Create `exchange_terminal.application.ports.anti_replay_registry_v2` from the V2 contract while replacing only its V1 import with canonical application port V1.
2. Replace the legacy V2 module with an explicit object-identity shim, including the inherited V1 outcome symbol.
3. Migrate both direct application consumers to canonical V2.
4. Propagate the V2 and namespace implementation fingerprints into provider-conformance plan V2.
5. Update ADR0435 H6, convert ADR0436's exact-five assertion to a non-regression ceiling, and let ADR0437 own the exact current value of three.
6. Preserve all V2 schemas, static fingerprint, request/key binding, deep-copy behavior, and authority locks.

## Fingerprints

- Canonical V1 SHA256: `5eed523c3665e687c6d2f202afcea5cc93bcdee3ef4ee942a7d4f76364f380a0`.
- Canonical V2 SHA256: `ff5d027d7b8352455be7792b495076070347de67534b736ff46cc1872f927f21`.
- Legacy V2 shim SHA256: `5b4656f4a06509491ae69f008fb57865d1a1acf7b93f20a4dd0f89f121f1cc38`.
- Namespace preregistration SHA256: `c716d91765aba195bb4f65be0d2fd6b9cc6e768ddcb544a2f0633eb894dc2e29`.
- Provider-conformance plan V2 SHA256: `cb48118f7791f7eb466d8fdc8da3235d568fe2a1a61def7c14df7709c8ad5792`.
- Updated ADR0435 migration contract SHA256: `f96d05ea8e9e7ed5093739531704c40f1675dacff685629ce376f1bba87aa58c`.
- Updated ADR0436 migration contract SHA256: `2133aa854cbf3bee96ce15c9ebd1ca1cb6c72f1889a90bb266a1a675cad32534`.
- Updated architecture-v2 contract SHA256: `3380d86f0f44d9de3ae30968aa865d64211eb29b962f3c71d2e5ec7dcdc0683f`.
- ADR0437 migration contract SHA256: `e68d630c585a7c6fcbf7d656e06be5d2066f7b1e5dbe7b6cea671b1a45a9a445`.

## Compatibility and activation order

Activation is producer-first and fail closed: canonical V2 with canonical V1 dependency, legacy identity shim, namespace consumer, plan consumer, predecessor ceilings, then the exact ADR0437 current-tree contract. The legacy path exports the exact canonical objects and does not wrap or duplicate V2 dataclasses, protocol, builders, or verifier.

The explicit hash-reference scan found no additional production consumer of the updated plan implementation hash. Existing namespace and plan verifiers rebuild synthetic documents from the current implementation pins; no evidence artifact or pointer is reissued.

## Current dependency result

- Explicit application-to-interfaces submodule imports reduce from 5 to 3.
- Recursive inventory becomes domain=2, application=88, infrastructure=1, interfaces=33.
- Audit-v2 cross-layer edges become application->domain=2, application->interfaces=9, interfaces->application=19.
- Module cycles remain absent.
- Architecture remains `BLOCKED_PARTIAL_LAYERING / LAYER_ROLE_SEPARATION_REQUIRED`.

## Safety and evidence boundary

This migration performs no registry call, compare-and-consume operation, nonce reservation, network access, runtime mutation, service startup, market-data access, backtest, scheduler action, paper order, live order, or publication. It preserves permanent paper/live locks.

The natural-forward single-look chain, legacy pack-v5 public reads, pointer-v2 fields and hash contract, and protected host assets remain unchanged. Static architecture and synthetic contracts are not strategy performance, profitability, release permission, paper authority, or live trading authority.
