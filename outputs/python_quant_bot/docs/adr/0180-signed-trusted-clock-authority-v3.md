# ADR 0180: Signed trusted-clock authority v3

- Status: Accepted as detached research-only evidence; not activated
- Date: 2026-08-22
- Scope: Local contract and synthetic tests only

## Context

The existing trusted-clock v2 checks source shape, source count, round-trip time,
provider spread, and local skew.  A pure synthetic read-only call showed that two
fabricated, unregistered, unsigned source dictionaries can still produce a `PASS`
attestation and then pass the public verifier.  The v2 artifact contains no
signature, public-key hash, key id, authority registration, request nonce, or
caller-pinned receipt hash.

That is a real evidence gap, but it does not justify reusing provider-identity
contracts as if they authenticated dataset-content or time authorities.  Those
contracts bind different schemas and signature domains.

## Decision

Add a detached v3 contract with four stages:

1. Build a hash-sealed local registration for 2 through 16 Ed25519 public keys.
2. Build an exact unsigned receipt bound to registration hash, authority/key,
   request nonce hash, request context hash, observed time, and issued time.
3. Attach a detached 64-byte signature without exposing a signer-secret API.
4. Evaluate and publicly reverify all source inputs, signatures, expected hashes,
   quorum, issue delay, receipt age, provider spread, and local skew.

The reference time is the median-low signed observation.  At least two distinct
registered authorities are mandatory.  The public-key map must exactly match the
registration, and the expected receipt-hash map must exactly match the supplied
receipt authorities.

The full attestation verifier rebuilds from registration, receipts, public keys,
expected hashes, request bindings, and verification time.  It never accepts the
attestation's self-hash as sufficient evidence.

## Maximum supported claim

`SIGNED_MULTI_AUTHORITY_TIME_QUORUM_VERIFIED_EXTERNAL_AUTHORITY_TRUST_UNPROVEN`

This means only that local cryptographic and policy checks passed against
caller-supplied material.  It does not mean:

- the registered keys belong to independent or real-world time authorities;
- registration governance, revocation, or key custody is trustworthy;
- the caller-supplied verification time is externally trusted;
- the request nonce is globally unique or protected by a durable replay registry;
- current market time has been established;
- paper/live trading is authorized;
- profitability has been demonstrated.

## Fail-closed bindings

| Binding | v3 behavior |
| --- | --- |
| Registration | Exact schema, canonical rebuild, caller-pinned hash |
| Keys | Exact authority map, Ed25519 length, registered SHA-256 hash |
| Receipt | Registration, authority/key, nonce, context, observation, issue time |
| Signature | Detached Ed25519 over canonical receipt-content digest |
| Expected inputs | Exact registration hash and exact receipt hashes by authority |
| Quorum | At least two unique registered authorities |
| Time policy | Validity, issue delay, age, spread, local skew |
| Projection | Raw keys and signatures omitted; all permissions false |

## Adversarial matrix

The synthetic contract suite covers duplicate authority/key/public-key identity,
single-source quorum, booleans passed as integers, invalid validity, malformed
base64, out-of-window receipts, delayed issuance, malformed request hashes,
wrong-length signatures, wrong public keys, extra keys, invalid signatures,
registration/receipt hash drift, omitted expected hashes, nonce/context drift,
provider spread, stale receipts, excessive local skew, verification outside
registration, coherent receipt resealing without resigning, projection tampering,
redaction, input immutability, and authorization inflation.

## Consumer-first activation order

1. Keep v3 detached and validate only its public contract.
2. Design a separate readiness-envelope revision that can reference the v3 hash
   while keeping external authority trust unproven.
3. Review that consumer before changing any shadow preregistration.
4. Do not switch `current`, issue a pointer, or alter the natural-forward chain.

## Compatibility and authority

Trusted-clock v2 remains unchanged for compatibility.  V3 is not a compatibility
promotion path and is not wired into the portfolio-risk shadow consumer.  The
natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reading remains `UNKNOWN`, and pointer-v2 fields, hash
contract, and non-reissuance behavior are unchanged.

## Validation boundary

Validation is limited to synthetic contract tests, related trusted-clock tests,
the public API matrix, and in-memory compilation.  No runtime, network, database,
cache, service, browser, scheduler, historical-return backtest, formal blind test,
paper task, or live task is used.
