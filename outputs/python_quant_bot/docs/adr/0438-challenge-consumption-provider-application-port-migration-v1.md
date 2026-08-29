# ADR 0438: Challenge Consumption Provider Application Port Migration V1

- Status: Accepted
- Date: 2026-08-24
- Predecessors: ADR 0436 and ADR 0437

## Context

The replay-cursor registration challenge-consumption port remained in the mixed interfaces package. Two application consumers depended on it: command binding through the package import and provider preregistration through the explicit submodule import.

The port itself is standalone, but its command-binding implementation hash feeds a sixteen-node application producer chain that reaches challenge provider bootstrap, genesis replay reservation, clock trust, threshold admission, and semantic quarantine. Moving only the import would leave that provenance chain stale.

## Decision

1. Preserve the exact port bytes as `exchange_terminal.application.ports.strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_v1`.
2. Replace the legacy interfaces module with an explicit object-identity shim.
3. Migrate both application consumers to the canonical port.
4. Propagate implementation SHA256 values through the complete sixteen-node producer closure in topological order.
5. Refresh ADR0436's genesis closure manifest, convert ADR0437's exact-three assertion to a non-regression ceiling, and let ADR0438 own the exact current value of two.
6. Preserve namespace, schemas, immutable command/result structures, conflict semantics, receipt derivation, and all authority locks.

## Fingerprints

- Canonical port SHA256: `01c3e4aa2684352764bfbd30cf9ab9c377d300fd652a5f96928eecaaa608fa48`.
- Legacy shim SHA256: `39df203f82f27cd16082efe19e9f15c48626b35d235ee941e9ed1a990a6b8160`.
- Command binding SHA256: `1fe76424b379591b53ece3cdf744605e8c5859444f19bba96f43eb4a099ff82f`.
- Provider preregistration SHA256: `2f47f2e8f44335fc6e9f51d07bd0a40bb329806b1331d0c5867f1210ad201e00`.
- Signed registration / challenge source SHA256: `4bafe95c80522b99517391d9dd08fe1ba0439965fafd5c85bb337dde284fd358` / `9b4cb591c8b69fbcd9d711b11f9ef6b7dd249ddc17033011068ccd9d6dae30cd`.
- Registration handoff / clock binding SHA256: `27ef6bcc3e9e2c37eef8c221afe7871b25ee4dbbba5d865c1b360afaa07833e5` / `840b9626291a469e24ad8acfccc58de614485ed2a96b1f3084e482a598bb3b5e`.
- Bootstrap topology / threshold admission SHA256: `71d6892de2c9ad97c01473e83ed7bb965bab5d888563df647155714314805c53` / `ef5c3ce72f60cd55aac08278993ecde99253c8812b3fb8868a0f3b930bf8a6a9`.
- Genesis preregistration / signed registration / challenge source SHA256: `78f7265b26ecdd4d8517195f60477ae2d96c913baa87ceb675fc1e2bdc2e28dc` / `c17c2d601332a0d373744f7840245bce9b9a3aae0b8ba3a06974c60f00b4e89b` / `d8ca1f7ffa1d7b6b0bfd4248ae65ba946528ea6fbf3509ca8a01ddbf0991ec40`.
- Genesis handoff / clock / topology / threshold SHA256: `1498c0ff70ae1c0221916f83120edf2604253db1a6a1f07f6a296ebd828155f9` / `b75d68e6ee4203b403ea503955fcd09c7c686a3ddb5d45d39e28d8fce55eb778` / `512a4e7da01075bb186662d7e30ac2e93cfef2148d46dea36c29aa4c6b4dc1bf` / `db94e0f3d606c1bda585c72762544d3a300e1f66872f4563ddec72133d99e23e`.
- Semantic quarantine SHA256: `0b8cfea3c864a51c00486fcb8a18294e5c79df919a2ff954e849b2ce47c6ab1d`.
- Updated ADR0436 migration contract SHA256: `666841d839ffc75da0336c7e89620573d8b020d46e67d7b85ab79558af131166`.
- Updated ADR0437 migration contract SHA256: `653187b758237d305c217449d4f1560711fdbcd2ecd8e2cb384067a372d21974`.
- Updated architecture-v2 contract SHA256: `657b0bbe06be55d14a0ce7c68b9771f23897e4fec0e08c58044ff6fe650059d1`.
- Updated preregistration compatibility contract SHA256: `014463fd92f2251021f349424ea5b963bc1da40ea0bade55b61c120172989943`.
- ADR0438 migration contract SHA256: `c7eca93bfc5fed38cf813b5e3381ce1d301ccec0cfdcf47933227d4347f7d138`.

## Activation order and compatibility

Activation is producer-first and fail closed: canonical byte copy, legacy identity shim, command binding, provider preregistration, signed registration and challenge, handoff and clock, bootstrap and threshold, genesis chain, predecessor manifests, then the exact ADR0438 current-tree contract. The legacy path exports exact canonical objects rather than wrappers or duplicate definitions.

The read-only hash graph contains no module cycle. Existing exact verifiers rebuild synthetic documents from current implementation pins; this migration does not reissue an evidence artifact, pointer, registry record, or runtime reservation.

## Current dependency result

- Explicit application-to-interfaces submodule imports reduce from 3 to 2.
- Recursive inventory becomes domain=2, application=89, infrastructure=1, interfaces=33.
- Audit-v2 cross-layer edges become application->domain=2, application->interfaces=7, interfaces->application=20.
- Module cycles remain absent.
- Architecture remains `BLOCKED_PARTIAL_LAYERING / LAYER_ROLE_SEPARATION_REQUIRED`.

## Safety and evidence boundary

This migration performs no challenge consumption, registry mutation, replay reservation, key operation, network access, runtime mutation, service startup, market-data access, backtest, scheduler action, paper order, live order, or publication. Permanent paper/live locks remain unchanged.

The natural-forward single-look chain, legacy pack-v5 public reads, pointer-v2 fields and hash contract, HTTP projection candidate, and protected host assets remain unchanged. Static architecture and synthetic contracts are not strategy performance, profitability, release permission, paper authority, or live trading authority.
