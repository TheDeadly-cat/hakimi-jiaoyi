# ADR 0436: Genesis Replay Reservation Application Port Migration V1

- Status: Accepted
- Date: 2026-08-24
- Predecessors: ADR 0433, ADR 0434, and ADR 0435

## Context

The genesis replay-reservation contract remained in the mixed interfaces package while its only direct application consumer was an application preregistration producer. The consumer implementation hash is a provenance input for signed registration, challenge, handoff, clock binding, bootstrap topology, threshold admission, and semantic quarantine producers.

Moving only the import would leave seven downstream implementation pins stale. The migration therefore uses an explicit producer-first closure and preserves the legacy import path as an object-identity shim.

## Decision

1. Preserve the exact legacy contract bytes as `exchange_terminal.application.ports.challenge_consumption_provider_genesis_replay_reservation_provider_v1`.
2. Replace the legacy interfaces module with an explicit object-identity compatibility shim.
3. Migrate the sole direct application consumer to the canonical application port.
4. Propagate implementation SHA256 values through the complete eight-node application producer closure.
5. Change ADR0435's exact-six current-tree assertion into a non-regression ceiling of at most six; ADR0436 owns the exact current value of five.
6. Preserve schema versions, namespace, static fingerprint, structural reserve-once semantics, and all authority locks.

## Fingerprints

- Canonical port SHA256: `1d8ddf5cbe28481e9b5f911cdd776891d1692c6a2e8183f9bf17e01473924512`.
- Legacy shim SHA256: `5e5fc36bee30958af90bcff36ba73098d90eea9b599ded7ea9d1ded0ed180694`.
- Preregistration consumer SHA256: `f47f7ab7f6f6ede94dc0009bf478a28e8bad31030f55251560ae5e31a26d6c99`.
- Signed registration SHA256: `d82746844cd9835668fbb51a7fe3844a2a22692e8365afc67a148eff8c6a0ae1`.
- Registration challenge source SHA256: `97a1c605c68bb52904288d24da5989ee3211361f555fc8bb3c64cea8b79cc2fb`.
- Registration handoff SHA256: `9fe6eed5ad92a44f1b31af0c6d3c68c3277ceccec79d28c512170d96bf48682e`.
- Clock binding SHA256: `fe1e720af4fac5d45aa2a774597b9e8b364341bef139ee7107e24bd99ab6ce2c`.
- Bootstrap topology SHA256: `8e64081ab6d26e5678f4b86b80a28be1e2bbc7ba0d035840f4f1e4fec12e3b8b`.
- Threshold genesis admission SHA256: `741d4b44ac374fcf05e4daddfb142e5e4efb510ffec8eefdbb60e62487307313`.
- Semantic profile quarantine SHA256: `dfc9055ef1dcd8c9b567f94f1e3c0d01c8e201930bdfed95f89dc15330c9aefb`.
- Updated ADR0435 migration contract SHA256: `6ff10f153ace5c197bbcbfa9fec3e46b8500a1ce791591a89c59ea3ad42492e0`.
- Updated architecture-v2 contract SHA256: `2d71668dfda14be26529314f72b297a0af9a87759cd5530f198408ed15b989b9`.
- ADR0436 migration contract SHA256: `69218d69cd8e07f9536c55f9fbb3a1cf5eb46c83a724cbe3aab376365a0e23b5`.

## Activation order and compatibility

Activation is consumer-first and fail closed: canonical byte copy, legacy identity shim, direct consumer import, downstream implementation pins in topological order, predecessor ceiling, then exact ADR0436 current-tree contract. The legacy module exports the exact canonical objects rather than wrappers or duplicate definitions.

The explicit source scan found no frozen downstream document-hash literal in this closure. Existing producer verifiers rebuild their synthetic documents from current implementation pins; no public artifact, pointer, runtime record, or evidence pack is reissued.

## Current dependency result

- Direct application-to-interfaces submodule imports reduce from 6 to 5.
- Recursive inventory becomes domain=2, application=87, infrastructure=1, interfaces=33.
- Audit-v2 cross-layer edges become application->domain=2, application->interfaces=11, interfaces->application=18.
- Module cycles remain absent.
- Architecture remains `BLOCKED_PARTIAL_LAYERING / LAYER_ROLE_SEPARATION_REQUIRED`.

## Safety and evidence boundary

This migration performs no provider call, replay reservation, registry mutation, key operation, network access, runtime mutation, service startup, market-data access, backtest, scheduler action, paper order, live order, or publication. It preserves the permanent paper/live locks.

The natural-forward single-look chain, legacy pack-v5 public reads, pointer-v2 fields and hash contract, and protected host assets remain unchanged. Static architecture and synthetic contract evidence are not strategy performance, profitability, release permission, paper authority, or live trading authority.
