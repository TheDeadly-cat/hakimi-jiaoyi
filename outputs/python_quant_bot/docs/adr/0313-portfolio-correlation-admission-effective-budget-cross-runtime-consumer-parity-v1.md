# ADR 0313: Cross-Runtime Consumer Parity Registration and Acceptance v1

Date: 2026-08-24

Status: Accepted as isolated, synthetic, and host-unbound

## Context

ADR0311 implements the Python hash-envelope source consumer. ADR0312 implements
the JavaScript verification, extraction, and unmounted bridge consumer.

Passing tests in each runtime do not by themselves prove that both consumers
agree on the same three states, source-hash policy, envelope hashes, extraction
receipts, presentation hashes, markup semantics, or permission locks. A
versioned parity registration and independently sealed acceptance receipt are
required before any future host binding can be reviewed.

## Decision

Add a Python parity registration with schema
portfolio-correlation-admission-effective-budget-cross-runtime-consumer-parity-registration-v1.

The registration pins:

1. The exact ADR0310 preregistration and both consumer contract hashes.
2. ADR0311 Python implementation, test, and ADR source hashes.
3. Corrected ADR0312 JavaScript implementation, test, fixture, and ADR hashes.
4. Exact KNOWN, UNKNOWN, and BLOCKED Python and JavaScript result hashes.
5. Envelope, extraction-receipt, presentation, markup, bridge-label, and
   source-hash policies for each state.
6. The rule that KNOWN and UNKNOWN markup must differ.
7. A consumer-first activation order that leaves host binding and current last.

Add a JavaScript acceptance module with receipt schema
portfolio-correlation-admission-effective-budget-cross-runtime-consumer-parity-acceptance-receipt-v1.

The acceptance module verifies the Python-generated registration, verifies the
exact synthetic three-state fixture, rebuilds all three ADR0312 results, and
compares hash-only state receipts against the registered matrix.

## Three-state parity

KNOWN maps to KNOWN:

- Source hashes are exact 64-character lowercase hashes.
- Bridge status is LOCAL ALIGNMENT.
- Markup is the corrected KNOWN markup and differs from UNKNOWN.

UNKNOWN maps to UNKNOWN:

- Source hashes remain all null.
- The extraction receipt is BLOCK/ENVELOPE_UNKNOWN with no payload.
- Bridge status is SOURCE UNKNOWN.

BLOCKED maps to BLOCKED:

- No envelope, extraction receipt, presentation, markup, or bridge label exists.
- JavaScript presentation work is not invoked.

The status mapping hash is
f0332296b3370e75810d172cbc261b13327e25f8b77f0d7f9c83d80df7bd3014.

## Acceptance boundary

An EXACT acceptance receipt contains only:

- Registration, parity-matrix, and status-mapping hashes.
- Three hash-only state receipts.
- Parity facts, blockers, transport locks, and false authority.

It does not embed Python results, envelopes, payloads, markup, positions,
symbols, correlations, prices, bars, account identity, runtime state, or
credentials.

Invalid registration or fixture input produces a sealed BLOCKED receipt with an
empty state-receipt list.

## Fail-closed behavior

Both verifiers reject unsealed and fully resealed source drift, parity-matrix
drift, state reordering, fixture drift, Python authority promotion, acceptance
state drift, authority promotion, extra fields, cycles, and non-native values.

Production modules have no network, storage, database, cache, environment,
filesystem, subprocess, DOM, browser, route, provider, or host-loader API.

## Consequences

Cross-runtime parity can now be evaluated as an exact synthetic contract rather
than inferred from separate test suites. The acceptance receipt remains
unbound evidence. It does not authorize host imports, script tags, stylesheets,
routes, providers, browser execution, DOM mounting, current activation, paper,
live, or writing.

The next step is an explicit host-binding preregistration that consumes this
acceptance receipt. It must remain a separate version and must not mount or
activate the interface automatically.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 remains unchanged
and is not automatically reissued. Synthetic contract evidence is not
profitability evidence and grants no trading permission.
