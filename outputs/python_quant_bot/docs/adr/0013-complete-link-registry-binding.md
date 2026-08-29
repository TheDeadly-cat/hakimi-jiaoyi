# ADR 0013: Complete-link protocol registry binding assessment

Status: Binding consumer implemented; no formal registry write or writer activation

## Context

Protocol registration v4 requires a formal protocol-v6 registry before any schema17 writer can exist. The existing registry anchor contract binds a protocol hash, registration event, audit tail, runtime root, canonical path, and search lineage, but its builder does not read the external registry asset.

## Decision

Add a registry-binding assessment that verifies registration v4, search-lineage v2, and registry-anchor v1 against expected registration identity and paths. It also requires a registry asset SHA-256 independently supplied by the caller.

The assessment never reads a registry file or database and explicitly records that fact. It binds the supplied fingerprint but does not activate a writer, current report, paper trading, or live authority.

## Consequences

- A fabricated or drifted protocol hash, path, lineage, or authority alias fails closed.
- Tests can use isolated synthetic anchors without claiming a production registry observation.
- A future authorized migration must independently compute the formal registry asset hash.
- No formal registry mutation, schema17 report, profitability claim, or execution authority is introduced.
