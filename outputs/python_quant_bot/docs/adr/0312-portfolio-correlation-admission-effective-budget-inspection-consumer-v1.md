# ADR 0312: Portfolio Correlation Inspection Consumer v1

Date: 2026-08-24

Status: Accepted as an isolated, unmounted JavaScript consumer

## Context

ADR0311 adds an isolated Python consumer that verifies ADR0309 and ADR0310
before returning a sealed hash-only delivery result. ADR0306 already provides a
JavaScript envelope verifier and extractor, while ADR0307 provides an unmounted
neutral structural bridge.

Those JavaScript modules accept the embedded ADR0306 envelope directly. They do
not verify the outer ADR0311 consumer result. A future host could therefore
discard the Python consumer gate and pass only the inner envelope to the
JavaScript path.

## Synthetic cross-runtime gap proof

A pure synthetic Python stdout to Node stdin pipeline demonstrated the gap:

1. Build an exact ADR0311 KNOWN result in Python.
2. Promote paper authority in the outer result and recompute its
   consumer_result_hash.
3. Confirm the outer object is structurally resealed.
4. Pass only its unchanged inner envelope to the existing JavaScript adapter.
5. Confirm the envelope verifies, the payload extracts, the bridge model builds,
   and neutral markup renders.

This proves that inner-envelope verification alone does not enforce the Python
consumer gate. The proof used no file artifact, network, service, browser,
market data, database, cache, or runtime state.

## Decision

Add an isolated JavaScript inspection consumer with schema
portfolio-correlation-admission-effective-budget-inspection-consumer-result-v1.

The consumer first verifies the full ADR0311 result:

1. Exact outer seal, schema, static fingerprint, and Python consumer identity.
2. Exact ADR0309, ADR0310, and Python consumer contract hashes.
3. Exact gate, source-hash, transport, facts, blockers, and false-authority
   structures.
4. Exact embedded ADR0306 envelope seal and semantics.
5. Exact equality between outer source hashes and inner envelope provenance.

Only after that chain passes may the JavaScript adapter build and verify an
extraction receipt. The existing ADR0307 bridge may then build a view model and
neutral markup string.

An invalid outer result returns BLOCKED without invoking extraction or bridge
construction. A valid Python BLOCKED result also remains BLOCKED with no
JavaScript adapter invocation. KNOWN and UNKNOWN map one-to-one across runtimes.

## Preregistered consumer pins

- ADR0310 consumer preregistration hash:
  4cc6352fb4083d8589d656481ecfd8fe3a33d6bba44bac6383ce2ca1f6d72987
- ADR0310 JavaScript consumer contract hash:
  1966892253b987f98ae8e8814692ec6f94387d2f9191ca7416447802382bbb8f
- ADR0311 Python consumer implementation hash:
  ec7de6b7dfdd30d4c29d9156551fd62525516a48e52cfc2cd945acc7b959eeca
- ADR0311 Python consumer test hash:
  3ff87343beccd2f22d95be20e989886fbde6539a29d81a4730d56ab552addc92
- ADR0311 ADR hash:
  06f2385cd3a302c5311f6685afb917e81f184ccaec79fca228a19dad86a23558
- Strict canonical JavaScript hash:
  6bd330faa256140e54a5c067c7292d55bba4cc29f83cd583cb7bf463b6e3ab39
- ADR0306 JavaScript adapter hash:
  867f7a7016472101a3606f2af22ae7b63509cc2afb3d2dbfe8f7058da8e08be0
- ADR0307 bridge JavaScript hash:
  67f16fa7946aee1c552b85bbb9758c84149a5cf657b7af5f78dad5ed0f7149d7

## Synthetic fixture

One source-controlled JSON fixture contains exact KNOWN, UNKNOWN, and BLOCKED
ADR0311 results. It is generated only from existing synthetic test inputs.

Fixture SHA-256:
b25be196152f370101bc43cf61e065308761d3070c4edb4656ffd00ad287dbe7

The fixture is test evidence only. It is not runtime, cache, market, account, or
profitability evidence.

## Output boundary

The sealed JavaScript result contains:

- Exact required contract and implementation hashes.
- An ADR0311 source receipt containing hashes only.
- A verified ADR0306 extraction receipt.
- An ADR0307 bridge view model and neutral markup string.
- An explicit presentation hash.
- In-memory transport facts, blockers, and false authority.

The result does not embed positions, proposed symbols, prices, returns, bars,
account identity, credentials, runtime state, or a host binding.

## Fail-closed behavior

The exact verifier rebuilds the JavaScript result from the supplied ADR0311
result. It rejects outer-result drift, doubly resealed envelope permission
promotion, source-hash drift, required-contract drift, markup drift, authority
promotion, extra fields, cycles, and non-native values.

The production module has no DOM, network, storage, filesystem, subprocess, or
runtime-loader API. It returns strings and frozen in-memory objects only.

## Consequences

The Python and JavaScript consumers now have an isolated semantic handoff, but
neither is imported by the host. The next step is a versioned cross-runtime
consumer parity registration and acceptance receipt. Host script tags, routes,
providers, browser execution, and DOM mounts remain later, separately
authorized decisions.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 remains unchanged
and is not automatically reissued. Synthetic contract evidence is not
profitability evidence and grants no trading permission.
