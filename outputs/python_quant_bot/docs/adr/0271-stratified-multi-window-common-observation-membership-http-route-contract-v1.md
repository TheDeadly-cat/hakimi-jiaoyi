# ADR 0271: Stratified multi-window common-observation membership HTTP route contract-v1

## Status

Accepted as a contract-only, unregistered research interface. No server route,
handler, external caller, UI consumer, current artifact, paper authority, or
live authority is activated.

## Context

Candidate-v11 lock-4 verifies and projects exact presentation-v11 membership
evidence, but intentionally contains no HTTP method, proposed route path, media
types, handler boundary, route-registration evidence, or UI consumer contract.
A pure synthetic audit confirmed all five route-contract field groups were
absent while the candidate correctly remained `KNOWN_BLOCKED` and
`UNREGISTERED_CANDIDATE`.

An older presentation-candidate-v3 consumes a
`registration_evidence_binding_document`, but that document belongs to the
strategy shadow-consumer preregistration chain. It is not HTTP server route
registration evidence and cannot be reused without collapsing domain and
transport boundaries.

## Decision

Add a separate route-contract-v1 consumer of candidate-v11 lock-4. Its exact
request contains the candidate response and expected candidate hash. Its exact
verification context contains the original candidate request and presentation
verification context. The candidate public verifier must return exact `True`.

The known contract proposes:

- method `POST`
- path `/api/research/strategy-correlation-clusters/common-observation-membership-presentation-v11`
- request and response media type `application/json`
- candidate-v11 request/response schemas pinned to lock-4

These values are descriptive only. `registered`, `externally_callable`,
`handler_bound`, `server_contract_bound`, and `ui_consumer_bound` remain false.
Registration evidence is explicitly `ABSENT`; a future activation consumer
must provide a separately versioned registration document and verification
receipt. Source-code search results are audit evidence, not self-authorizing
runtime input.

The route contract never embeds the candidate payload, candidate request, or
verification context. It carries only schema versions, exact hashes, fixed
transport metadata, calibrated facts, blockers, and the neutral
`SOURCE -> GAP -> MATURITY -> PERMISSION` stages.

Malformed request/context/candidate documents, candidate hash substitution,
candidate verifier false/exception, or authority promotion return `UNKNOWN`
with a null payload. A known candidate always produces
`KNOWN_UNREGISTERED/BLOCK`. Candidate local, adapter, and membership blocks are
projected as additive route-contract blockers without changing authority.

## Consumer-first order

1. Keep route-contract-v1 import-only and exercise it through direct synthetic calls.
2. Preserve candidate-v11 and presentation-v11 exact verification boundaries.
3. Define registration evidence as a separate versioned document before any server binding.
4. Bind a handler only after independent source audit and explicit authorization.
5. Define a UI consumer only after a registered route exists, preserving neutral axes.
6. Require a separate current-admission decision; no route contract grants execution authority.

## Adversarial matrix

- exact candidate remains known but route-unregistered
- membership block remains visible at the current route scope
- unknown candidate suppresses the complete route payload
- request and context compatibility fields fail before candidate verification
- candidate hash substitution fails before candidate verification
- candidate verifier false or exception fails closed
- resealed candidate authority promotion fails before candidate verification
- candidate payload, requests, and contexts are not embedded
- resealed route-registration promotion fails exact rebuild
- input objects remain immutable

## Consequences

The project gains a precise consumer-first transport contract without changing
server or UI behavior. This is not registration evidence, runtime validation,
profitability evidence, or paper/live permission.
