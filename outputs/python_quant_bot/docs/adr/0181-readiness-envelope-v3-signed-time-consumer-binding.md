# ADR 0181: Readiness envelope v3 signed-time consumer binding

- Status: Accepted as detached research-only application evidence; not activated
- Date: 2026-08-22
- Scope: Synthetic consumer contract only

## Context

ADR0179 verifies a complete set of 13 local portfolio-risk shadow inputs.  Its
public builder and verifier accept no trusted-clock evidence argument.  A pure
synthetic call proved that changing unrelated clock material leaves the ADR0179
document byte-identical; its output contains no `trusted_clock` binding.  This is
correct for v2 compatibility, but it means ADR0180 cannot be attached without a
new consumer schema.

ADR0180 verifies a detached Ed25519 multi-source time quorum while explicitly
leaving real-world authority, registration governance, caller time, nonce
uniqueness, replay durability, current time, and trading permission unproven.

## Decision

Add an application-layer readiness envelope v3 that:

1. Fully reverifies the ADR0179 document from all original v1 and portfolio inputs.
2. Derives a trusted-clock request-context hash from the ADR0179 envelope hash,
   source attestation hash, future-evaluation id hash, v3 schema, and a fixed domain.
3. Requires ADR0180 receipts and attestation to bind that exact context hash.
4. Fully reverifies ADR0180 from registration, receipts, public keys, caller-pinned
   hashes, nonce, context, and supplied verification time.
5. Adds exactly one fourteenth locally verified input and emits only hash lineage.

The application module does not import or invoke the shadow consumer, risk service,
runtime, network, database, cache, scheduler, or trading code.

## Maximum supported claim

`LOCAL_INPUT_SET_AND_SIGNED_TIME_QUORUM_VERIFIED_EXTERNAL_TRUST_UNPROVEN`

The four neutral axes remain:

| Axis | V3 value |
| --- | --- |
| SOURCE | `LOCAL_INPUT_SET_AND_SIGNED_TIME_QUORUM_VERIFIED` |
| GAP | `EXTERNAL_TRUST_AND_RUNTIME_CONSUMER_UNPROVEN` |
| MATURITY | `LOCAL_INPUT_SET_AND_SIGNED_TIME_QUORUM_VERIFIED_EXTERNAL_TRUST_UNPROVEN` |
| PERMISSION | `DENIED` |

The overall status remains `UNKNOWN`.  Signed receipts do not authenticate the
real-world operators that control the registered keys and do not establish a
trusted current time.

## Fail-closed properties

| Property | Behavior |
| --- | --- |
| ADR0179 source | Full public re-verification, exact 13 verified inputs |
| ADR0180 source | Full public re-verification from every signed input |
| Consumer binding | Derived context hash must match receipts, attestation, and context |
| Inventory | Exactly 14 verified local inputs |
| Projection | Raw public keys, signatures, receipts, and verification contexts omitted |
| Authority | Descriptive only; current, shadow, runtime, paper, and live remain false |

## Adversarial matrix

The synthetic tests cover the original v2 gap, context derivation drift, v2 source
tampering, wrong v2 contexts, permission inflation, clock attestation tampering,
current-time inflation, valid clock evidence for another consumer, registration and
receipt hash drift, wrong signer, sub-quorum receipts, exact context schemas,
projection tampering, raw evidence redaction, hash-only lineage, immutability, and
execution/profit claim inflation.

## Consumer-first activation order

1. Keep ADR0181 detached and validate the public application contract.
2. Review a future shadow preregistration revision that may pin the ADR0181 schema
   and fingerprint without executing the consumer.
3. Require separate evidence for external time-authority ownership, governed key
   registration, caller time trust, nonce uniqueness, and durable replay handling.
4. Do not switch `current`, publish a new pointer, or invoke risk/trading services.

## Compatibility and authority

ADR0179 and trusted-clock v2 remain unchanged.  ADR0181 is not a compatibility
promotion path.  The natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reading remains `UNKNOWN`.  Pointer-v2 fields, hash contract,
and non-reissuance behavior remain unchanged.  No profitability or paper/live
authority follows from this evidence.

## Validation boundary

Validation is limited to synthetic contracts, related ADR0179/0180 families, a
public adversarial API matrix, and in-memory compilation.  No runtime, external
market data, historical-return backtest, formal blind test, service, browser,
scheduler, paper task, or live task is used.
