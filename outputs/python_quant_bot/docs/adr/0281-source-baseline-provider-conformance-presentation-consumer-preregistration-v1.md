# ADR0281: Source-Baseline Presentation Consumer Preregistration v1

## Status

Accepted as an unregistered, asset-free, read-only consumer contract.

## Context

ADR0280 provides a neutral unmounted presentation envelope. The repository also
contains portfolio-risk presentation consumer registrations through V9, plus
post-registration execution and anti-replay evidence. Read-only audit showed
that V9 pins a different source schema and six JavaScript/stylesheet assets. Its
manifest does not contain the ADR0280 implementation hash and cannot be reused
without semantic drift.

A pure gap proof confirmed source-schema mismatch, missing ADR0280 implementation
pin, absent source consumer preregistration, zero UI bindings, and zero runtime
mutations.

An additional pure synthetic adversarial proof found a verification/use gap in
the first draft: a stateful external `Mapping` could return the exact
preregistration hash during verification and a forged hash during payload
projection. The candidate remained `BLOCKED`, but its projected provenance was
not the value that had been verified.

## Decision

Add a source-baseline-specific preregistration that pins:

- ADR0280 schema version;
- ADR0280 static fingerprint;
- ADR0280 implementation SHA-256;
- `presentation_envelope_hash` as the source document hash field;
- the exact top-level source fields;
- the four ordered stages and axis fields;
- the five allowed summary fields;
- the seven bounded payload fields.

The preregistration records V9 as semantically incompatible and does not reuse
its asset manifest. JavaScript, card, stylesheet, and consumer implementation
hashes remain null. The protected stylesheet hash is informational only and
stylesheet reuse is not authorized.

Add a pure payload candidate builder. It exact-verifies the preregistration and
the full ADR0280 source chain, then copies only display tone/state, ordered axes,
summary, blockers, and a locked permission object. It exposes the source envelope
hash but omits source lineage details, source documents, identity material, and
executable assets.

Before verification, every external document is recursively normalized once
into a plain, JSON-compatible snapshot. Exact verification and all later field
projection use those same snapshots. Cycles, non-JSON values, invalid keys, or
snapshot exceptions fail closed to `UNKNOWN` without a payload. Public exact
verifiers apply the same snapshot fence before canonical comparison.

Successful payload construction remains `BLOCKED` with
`PAYLOAD_BUILT_CONSUMER_UNREGISTERED`. Invalid or promoted inputs return
`UNKNOWN` with no payload.

## Adversarial matrix

- V9 manifest substitution: incompatible;
- source schema/fingerprint/implementation drift: exact preregistration failure;
- source envelope tampering or resealed mount promotion: payload `UNKNOWN`;
- preregistration asset or consumer promotion: payload `UNKNOWN`;
- payload UI/current promotion: exact verifier failure;
- second-read preregistration hash or source display substitution: frozen at the
  value exact-verified from the one-time snapshot;
- cyclic, non-JSON, or exception-raising mappings: payload `UNKNOWN`;
- source lineage, raw documents, raw identity, READY, or profitability language:
  forbidden;
- browser, route, asset write, UI mount, and current activation: false.

## Non-claims

This contract does not create JavaScript, CSS, HTML, a route, a browser consumer,
or a mounted card. It does not execute or visually validate a frontend, modify
protected assets, activate current evidence, call a provider, authorize paper or
live activity, prove market validity, demonstrate strategy performance, or prove
profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
