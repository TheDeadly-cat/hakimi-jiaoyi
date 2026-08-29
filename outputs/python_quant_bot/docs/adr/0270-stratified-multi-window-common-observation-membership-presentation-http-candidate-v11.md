# ADR 0270: Stratified multi-window common-observation membership presentation HTTP candidate-v11

## Status

Accepted as an unregistered, research-only candidate. It is not a route, not a
current artifact consumer, and not paper/live authority. The current static
contract is candidate-v11 `unmounted-lock-4`.

## Context

Presentation-v10 and HTTP candidate-v10 stop before the exact
common-observation membership identity introduced by membership gate-v2,
adapter-v10, and presentation-v11. A pure synthetic gap proof showed that a
v11 request is rejected by candidate-v10 before its presentation verifier is
called. Counts alone therefore cannot be treated as proof that correlated
edges used the same observations.

The next consumer must preserve the exact presentation-v11 verification
receipt and expose only bounded aggregate facts. It must not reveal raw
observation identifiers, samples, pair commitments, source documents, or
verification contexts.

## Decision

Add an unregistered HTTP candidate-v11 with these exact inputs:

- request schema, expected presentation-v11 hash, and presentation-v11 document
- presentation-v10 document and verification context
- adapter-v10 document and verification context

The source boundary is pinned to `presentation_v11_hash`,
`static_fingerprint`, the `source` lineage object, and the ordered SOURCE, GAP,
MATURITY, PERMISSION stage list. The verifier boundary accepts only the exact
`verification-v1` PASS receipt, including `presentation_v11_exactly_verified`,
whose current-admission, presentation-consumer activation, runtime-gate,
paper/live, and writer fields remain false. Malformed
requests, contexts, documents, receipts, verifier failures, or authority
promotion produce `UNKNOWN` with a null payload.

A verified document produces `KNOWN_BLOCKED`, never READY. The payload contains
only bounded aggregate risk, multi-window, edge-uncertainty,
common-observation, and membership summaries. Floating-point values are
rendered as canonical decimal strings. Raw identifiers, samples, symbols,
prices, pair commitments, source documents, contexts, and receipts are
excluded.

The candidate remains fail-closed with the fixed blockers:

- `HTTP_CANDIDATE_V11_UNREGISTERED`
- `PRESENTATION_V11_CONSUMER_NOT_REGISTERED`
- `CURRENT_ADMISSION_LOCKED`
- `UI_NOT_MOUNTED`

Membership, adapter, and local presentation blocks remain visible as additive
blockers. Exact response verification uses deterministic rebuild and rejects
compatibility fields or resealed mutations.

Lock-2 also preserves the source presentation's four fixed governance blockers
as visible GAP evidence. The exact ordered set is validated before invoking the
presentation verifier; substituted, missing, reordered, or additional tokens
return `UNKNOWN` with a null payload. A general string-list projection was
rejected because it could leak symbols or observation identifiers through a
mocked verifier boundary. Candidate-v11 remains unregistered, so this hardening
replaces lock-1 rather than introducing a duplicate candidate-v12 boundary.

Lock-3 scopes GAP evidence explicitly. `source_snapshot` preserves the frozen
presentation-v11 assertion that candidate-v11 had not yet been defined;
`candidate_current` reports the now-existing candidate as unregistered and
includes any local, adapter, or membership blocker added by this consumer. The
payload and GAP stage state that the source snapshot is not current candidate
state. This removes the apparent `NOT_DEFINED` versus `UNREGISTERED`
contradiction without rewriting presentation-v11 or adding a compatibility
path. Candidate-v11 remains unregistered and authority remains unchanged.

Lock-4 removes the candidate's private JSON serialization and SHA-256 sealing
implementation. All payload and response sealing and exact comparison now use
the project `strict_canonical_json_hash` service directly. The private and
shared implementations happened to agree for the current ASCII payload but
produced different hashes for a Unicode synthetic document. No fallback or
compatibility hash is retained. This closes a duplicate canonicalization
boundary before any route consumer can depend on the candidate.

## Consumer-first activation order

1. Keep candidate-v11 unregistered and exercise it only through direct,
   synthetic calls.
2. Verify presentation-v11 and adapter-v10 independently before accepting the
   candidate receipt boundary.
3. Add any future route contract as a separate versioned consumer with explicit
   registration evidence.
4. Add a UI projection only after the route contract exists, preserving the
   neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` order.
5. Require a separate current-admission decision. No candidate, route, or UI
   contract can authorize current, paper, or live operation.

## Adversarial matrix

- exact clear aggregates remain outer blocked
- membership mismatch remains visible
- unknown source suppresses the complete payload
- extra request or context fields fail before verifier invocation
- expected-hash substitution fails before verifier invocation
- malformed or compatibility verification receipts fail closed
- verifier exceptions fail closed
- response permission mutations fail exact rebuild
- raw membership data and pair commitments are absent
- floats are canonical strings
- resealed authority promotion is rejected before verifier invocation
- request and context objects remain immutable

## Consequences

The HTTP boundary can now distinguish exact membership evidence from equal
counts without registering a route or changing authority. The natural-forward
evidence chain and pointer contracts are untouched. This ADR supplies no
profitability evidence and grants no paper/live permission.
