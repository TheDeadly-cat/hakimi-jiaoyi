# ADR 0434: Registry signer source-trust application port migration v1

- Status: accepted research-only architecture migration; activation remains forbidden
- Date: 2026-08-24
- Predecessors: ADR 0432 and ADR 0433

## Context

After the organization identity port migration, `anti_replay_registry_signer_source_trust_preregistration_v1` still imported signer source-trust schemas from the mixed `interfaces` package. The signer source-trust contract itself depended on the legacy organization identity interface path, despite that dependency already having an application-owned canonical port.

This is the smallest remaining one-consumer inward port and forms a coherent dependency chain with the first migrated port.

## Decision

1. Create `exchange_terminal.application.ports.registry_signer_source_trust_v1` as the canonical signer source-trust port.
2. Change its organization identity dependency to the existing application-owned canonical port.
3. Replace the old interfaces module with an object-identity compatibility shim pinned to the canonical implementation hash.
4. Migrate the sole application consumer to the canonical signer source-trust path.
5. Preserve record schema, protocol version, validation behavior, runtime-checkable Protocol identity, and all authority locks.
6. Keep shim removal and all external source selection separately unauthorized.

## Fingerprints

- Legacy signer source-trust preimage SHA256: `676546a5b1bba46d63a362cdc313a83a591a3976de67f170962645cbb3cdb7ce`.
- Canonical signer source-trust implementation SHA256: `04e288bc11db85e21a775602d54a453d514474b9bf82133716ec4e63f72775ff`.
- Legacy compatibility shim SHA256: `12a21ae296c8ee8fc22d5ef233af7471377c91b337bf0af799e9e1f2ece9f6c2`.
- Migrated application consumer SHA256: `b8fbd76f4f4ea4b1990f7a17974d2d31c5e5b2e13f573c32117647a7945f53bc`.
- Validation correction: the consumer intake implementation pin now references canonical SHA256 `e41299bd52c64e2eb47b691cfe4a8bf2fcaff401d018cd1647293842f16ea014`, and its organization identity pin is verified against the application-owned canonical port rather than the legacy shim.
- Updated ADR0432 monotonic migration contract SHA256: `4e1088b7f36faa650630752db0668158654c50edf1807e4c4b9aee0f24b86ec7`.
- Updated audit-v2 current-tree contract SHA256: `eedb0412889ad32627b6b69c4f925101830d884b2c1e74578d80f66ac00190ca`.
- ADR0434 migration contract SHA256: `4db55be81a9a908a3fe0f5874f3f7ea8f66c9ca7e89931fb83d270acc2b7ec4a`.

## Current dependency result

- Direct application-to-interfaces import statements reduce from 8 to 7.
- Recursive inventory becomes domain=2, application=85, infrastructure=1, interfaces=33.
- Audit-v2 cross-layer edges become application->domain=2, application->interfaces=13, interfaces->application=16.
- Module cycles remain absent.
- Architecture remains `BLOCKED_PARTIAL_LAYERING / LAYER_ROLE_SEPARATION_REQUIRED`.

ADR0432 keeps its historical 8-edge snapshot. Its current contract now enforces a non-regression ceiling of at most 8, while ADR0434 pins the exact current count of 7. ADR0433 remains an immutable historical snapshot; this ADR records the updated audit-v2 current-tree contract hash.

## Safety and evidence boundary

This migration performs no source selection, network access, external registry access, runtime state mutation, service startup, market-data access, backtest, scheduler action, paper order, live order, or publication. The compatibility shim grants no authority and cannot be removed without a separate consumer inventory and ADR.

The natural-forward evidence chain, legacy pack-v5 public reads, and pointer-v2 remain unchanged. Static architecture and synthetic contracts are not strategy performance, profitability, release permission, paper authority, or live trading authority.