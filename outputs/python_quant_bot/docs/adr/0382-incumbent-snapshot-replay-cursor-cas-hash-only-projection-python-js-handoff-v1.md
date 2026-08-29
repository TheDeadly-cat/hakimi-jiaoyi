# ADR0382: Replay Cursor CAS Projection Python-to-JavaScript Handoff v1

## Status

Accepted as an unmounted, exact in-memory interface bridge.

## Context

ADR0381 produces a strict hash-only projection, but a JavaScript presenter must
not accept that projection merely because a caller supplied a plausible hash.
The existing ADR0375 -> ADR0376 -> ADR0377 consumer sequence establishes the
required boundary: Python first reruns the complete projection verifier, then
hands JavaScript an isolated verification envelope.

ADR0382 preserves that activation order. The visual presenter is deferred to
ADR0383 rather than consuming a bare ADR0381 document.

## Decision

Add a four-field handoff envelope:

- exact handoff schema version;
- exact verification status;
- independently expected ADR0381 projection hash;
- a JSON-safe deep clone of the verified projection.

The builder calls the complete ADR0381 verifier with the base and observed
cursors, attestation, ADR0379 result, ADR0380 intent, all expected hashes, stream
binding, and projection preregistration binding. Verification failure returns
no envelope.

JSON cloning rejects NaN, floating-point values, unsupported types, non-string
object keys, and integers outside JavaScript's safe-integer range. This prevents
Python-to-Node numeric precision drift in sequence evidence. The exact envelope
verifier rebuilds the complete envelope and requires equality.

## Cross-language evidence

Node receives the envelope only through stdin. A recursive sorted-key
canonicalizer proves byte-exact JSON agreement with Python for the accepted
synthetic envelope. No temporary file, presenter mount, DOM, browser, service,
route, or runtime loader is used.

## Adversarial matrix

- synthetic advance crosses as UNKNOWN;
- CAS conflict crosses as UNKNOWN;
- duplicate consumption crosses as BLOCK;
- wrong projection hash produces no envelope;
- resealed permission or atomicity promotion produces no envelope;
- resealed JavaScript-unsafe sequence produces no envelope;
- envelope or nested projection mutation fails exact verification;
- raw stream, nonce, and prior consumed hashes remain absent;
- ADR0379 blocked evidence cannot cross the bridge;
- production bridge exposes no I/O, Node, runtime, mount, or publish operation.

## Non-claims

This bridge proves schema and canonical JSON interoperability only. It does not
prove rendered UI, browser behavior, storage CAS, durability, linearizability,
provider identity, current activation, real holdings, wall-clock freshness,
strategy performance, profitability, paper authority, or live authority.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. pointer-v2 remains unchanged
and is not reissued.
