# ADR 0432: Registry organization identity application port migration v1

- Status: accepted research-only architecture migration; activation remains forbidden
- Date: 2026-08-24
- Predecessor: ADR 0431

## Context

ADR 0431 found no module cycle, no domain outward dependency, and no application-to-infrastructure dependency. It also found that `exchange_terminal.interfaces` mixes inward ports with outward delivery adapters. The application package imported the legacy organization-identity interface from four use-case modules, while other consumers still depended on the legacy path.

A direct deletion or duplicate reimplementation would create compatibility or Python type-identity drift. A reverse shim from application to interfaces would preserve the forbidden application dependency. The migration therefore needs a canonical application-owned port plus an outward compatibility shim.

## Decision

1. Preserve the exact pre-migration port bytes as `exchange_terminal.application.ports.registry_organization_identity_v1`.
2. Replace `exchange_terminal.interfaces.registry_organization_identity` with a narrow compatibility shim that re-exports the exact canonical objects and pins the canonical implementation hash.
3. Migrate the four application consumers to the canonical application-owned path before any legacy-path removal.
4. Keep existing non-application consumers on the compatibility path until separately inventoried and migrated.
5. Do not select a runtime adapter, external registry, signer, trust anchor, storage provider, or execution authority through this migration.

## Consumer-first result

- Canonical port SHA256: `df294b21bae439b96b86220a2be55ed5bf3305c9f32aaefb98c18e5d3b00b59f`.
- Legacy compatibility shim SHA256: `362ece930576c683c42ac02747825254ba2a83f8614ec9240fab56f28cff4d60`.
- Ports package initializer SHA256: `19453f38ba0134c0cd1e81d9f8abf9932d63ccae136ed8ad7d3792213da5e13f`.
- Evaluation consumer SHA256: `fec30c1e6433db5ea67c7e2a222e3c74cfd7fac8757461f579ccc7ee6d6fa055`.
- Verification consumer SHA256: `e0bbd82b139f41fd6394343f9a074698e6477f27af3b22b8a3fd984848532b96`.
- Intake consumer SHA256: `e41299bd52c64e2eb47b691cfe4a8bf2fcaff401d018cd1647293842f16ea014`.
- Signer-trust consumer SHA256: `970b7ac92dca0ea5f76e9c899d4506c2a61d3da83eb600431aafe9ddb23687f9`.
- Nested-module architecture audit-v2 implementation SHA256: `321b4ad0ef6fc7c7d0137129866938645ac3c458ef68a2ff35fec91ae94bb523`.
- Nested-module architecture audit-v2 test SHA256: `6216847fab53774d55268329dde26a3590feb967122cbf6e640bdedffeb8de1a`.
- Migration contract SHA256: `007e30d8580e3c0fa46a0312c059040044c2c43a3ff4cc6d6f383ee359a4d29f`.
- Application module inventory changes from 82 to 84 because the explicit ports package and canonical module are added.
- Full recursive interfaces inventory is 33; the prior count of 15 remains the audit-v1 top-level historical scope.
- Direct application-to-interfaces import statements reduce from 12 to 8.
- ADR0433 audit-v2 consumes recursive current-tree evidence including nested Python modules; both audit versions remain pure in-memory evaluators with no filesystem access.
- Overall architecture remains `BLOCKED_PARTIAL_LAYERING`; this slice is progress, not completion.

## Compatibility contract

The legacy module defines no duplicate class, enum, protocol, helper function, or validation rule. Public objects from the old and new import paths must be identical with `is`, not merely structurally equal. References constructed through the old path must satisfy exact `isinstance` checks against the canonical application port.

The compatibility shim is temporary. Removal requires explicit inventory of remaining consumers, consumer migration, targeted compatibility evidence, and a separate ADR. Import success alone is not removal authority.

## Safety and evidence boundary

This is a static source-boundary migration. It performs no filesystem access at module import, network access, market-data access, runtime mutation, service startup, scheduler action, backtest, paper order, live order, publication, or evidence-chain activation.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is not reissued.

Passing architecture and compatibility contracts is not strategy performance, profitability, market validity, release permission, paper authority, or live trading authority.