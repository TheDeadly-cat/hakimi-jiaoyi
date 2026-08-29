# ADR0287: Source-Baseline Provider-Conformance In-Memory Delivery Adapter v1

## Status

Accepted as a cross-runtime, endpoint-free, in-memory delivery candidate.

## Context

ADR0286 preregisters host asset order and a future card slot, but explicitly
leaves payload delivery adapter and endpoint null. The ADR0281 payload candidate
is already bounded, identity-redacted, sealed, and consumable by the ADR0282
card. What is missing is an exact Python-to-JavaScript handoff contract that
does not silently create HTTP, persistence, DOM, browser, or mount authority.

## Decision

Add a Python service that exact-verifies the complete ADR0286 descriptor binding
and matching ADR0281 payload before building a sealed delivery envelope. The
envelope embeds the bounded payload candidate and hash provenance, but no raw
source documents or identity material.

Transport is fixed to `IN_MEMORY_JSON_DOCUMENT` with `NO_STORE`, UTF-8 JSON,
null endpoint, null route, no wire bytes, no network transport, and no persistent
storage. Building the document is not a delivery attempt.

Add a UMD/CommonJS JavaScript adapter that:

- snapshots and exact-verifies the delivery envelope;
- reuses the ADR0282 card verifier for the nested payload;
- extracts a detached payload copy in memory;
- creates a sealed receipt candidate stating that extraction occurred but card
  render, DOM access, browser execution, and mount did not occur;
- rejects endpoint, route, network, storage, render, permission, or payload
  promotion.

Neither side pins the other's implementation hash in this version, avoiding a
bidirectional hash cycle. A later registration must pin both final assets and
their tests before any host integration is considered.

## Consumer-first activation order

1. Keep ADR0281 through ADR0286 frozen.
2. Validate exact Python envelope to JavaScript extraction in memory.
3. Register Python and JavaScript adapter assets in a new version.
4. Preregister a payload source provider without exposing an endpoint.
5. Apply host changes only after explicit authorization.
6. Execute browser rendering and visual review only after independent host and
   payload-source evidence.

No step automatically promotes the next one.

## Non-claims

An in-memory document is not network delivery, endpoint availability, browser
execution, card rendering, DOM access, UI mount, or visual evidence. This version
does not write host files, register routes, access persistent storage, call a
provider, mutate runtime state, activate current evidence, authorize paper or
live activity, prove market validity, demonstrate strategy performance, or
prove profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
