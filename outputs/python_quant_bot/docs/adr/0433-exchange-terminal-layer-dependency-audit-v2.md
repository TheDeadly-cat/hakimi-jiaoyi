# ADR 0433: Exchange-terminal layer dependency audit v2

- Status: accepted research-only static audit contract; architecture remains blocked
- Date: 2026-08-24
- Predecessors: ADR 0431 and ADR 0432

## Context

Audit-v1 accepts only three-segment module names and reports a top-level layer inventory. The first application-owned port migration added `exchange_terminal.application.ports`, exposing that v1 cannot represent nested package paths. Flattening nested names would permit basename collisions and weaken import and cycle evidence.

The recursive current tree contains domain=2, application=84, infrastructure=1, and interfaces=33 modules. The interfaces total includes 18 modules below `interfaces.http` that were outside the v1 top-level inventory.

## Decision

1. Preserve the audit-v1 implementation and its 82/15 top-level semantics.
2. Introduce `exchange-terminal-layer-dependency-audit-v2` as an independent pure in-memory evaluator with independently named evaluate and verify APIs.
3. Accept between 3 and 16 canonical lowercase module segments under one of the four exact layer names.
4. Reject empty segments, layer-name spoofing, invalid identifiers, excessive depth, and excessive length as UNKNOWN input.
5. Preserve complete dotted module identities so same-basename modules in separate packages cannot collide.
6. Resolve absolute and relative imports through the complete known-module set.

## Current recursive result

- Status: `BLOCKED_PARTIAL_LAYERING`.
- Decision: `LAYER_ROLE_SEPARATION_REQUIRED`.
- Module counts: domain=2, application=84, infrastructure=1, interfaces=33.
- Cross-layer edges: application->domain=2, application->interfaces=14, interfaces->application=15.
- Module cycles: none.
- Violations: application/interfaces package bidirectionality, mixed interfaces roles, and incomplete port/delivery namespace separation.
- Architecture migration complete: false.

## Fingerprints

- Audit-v1 implementation SHA256: `94f6d6b2fe1a678e638c1b7971cae5a7eee733249480c2e519a156c7b8cff45d`.
- Historical audit-v1 contract SHA256 before the ADR0432 migration attempt: `1834b68d08d20abe8a937b30396aab3fa30a5ebbbe5ba7f36f7147cbf9fc289c`.
- Current logically restored audit-v1 contract SHA256: `b526c1a7bd06f7943e37db78d51d7a3b48c5104572a9ada384c7b650d69d0a6c`; no byte-identity claim is made for the historical test file.
- Audit-v2 implementation SHA256: `321b4ad0ef6fc7c7d0137129866938645ac3c458ef68a2ff35fec91ae94bb523`.
- Audit-v2 contract SHA256: `6216847fab53774d55268329dde26a3590feb967122cbf6e640bdedffeb8de1a`.
- Updated ADR0432 SHA256: `130837b9bb1c6e6bf79573238885a9c3a3248628cde4b6ccd037b1693db88259`.

## Evidence and safety boundary

Both evaluators consume explicit native `dict[str, str]` mappings. Neither evaluator enumerates files, executes audited imports, accesses runtime state, starts services, accesses market data, or mutates trading artifacts. Recursive filesystem collection exists only in the current-tree contract harness.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. This architecture audit version is unrelated to the natural-forward audit-v2 artifact type. Legacy pack-v5 public reads and pointer-v2 remain untouched.

Static architecture evidence is not strategy performance, profitability, market validity, release permission, paper authority, or live trading authority.