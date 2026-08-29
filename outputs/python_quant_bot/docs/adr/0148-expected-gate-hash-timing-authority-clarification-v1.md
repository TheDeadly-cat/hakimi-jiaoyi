# ADR 0148: Expected gate hash timing-authority clarification v1

## Status

Accepted as a fail-closed semantic clarification on 2026-08-22.

## Context

Report20 and report21 require caller-supplied expected gate hashes and exact
gate reconstruction. ADR0146 and ADR0147 initially used wording that could be
read as evidence that the expected hash existed before evaluation.

The actual contracts contain identity, replay inputs, and an expected gate hash.
They contain no declaration timestamp, evidence cutoff binding, external time
anchor, immutable receipt, or independently verified sequence. Protocol-v9,
protocol-v10, formal-persistence registry candidates, and the report21 candidate
binding do not add timing evidence for these expected gate hashes.

A pure synthetic proof evaluated the gates first, copied their hashes into the
expected-hash fields, and then built exact report20 and report21 PASS documents.
Adding a `declared_at` field was rejected because it is not part of either exact
input contract. Post-hoc equality therefore passes, while timing remains
unrepresented.

## Decision

- Describe these fields as caller-supplied expected-hash equality bindings.
- Treat them as substitution-resistance and exact-replay evidence only.
- Do not infer preregistration, precommitment, chronology, external timing,
  freshness, formal persistence, or current authority from a matching hash.
- Preserve all existing builder, consumer, protocol, hash, decision, and
  permission contracts. No compatibility alias or optional timing field is
  added to the frozen inputs.
- Keep timing authority `NOT_PROVEN` until a separate consumer-first versioned
  contract exists and is independently verified.

## Future timing contract requirements

A future candidate must bind the exact identity, base report hashes, expected
gate hash, declaration timestamp, evidence-not-before boundary, external anchor
identifier and anchor receipt hash. It must prove strict chronology, immutable
persistence, uniqueness, freshness, rollback resistance, and exact source
linkage before any public maturity or writer consideration.

The activation order remains consumer verifier, adversarial tests, redacted
projection, external delivery evidence, and only then any mounting review.
Adding a timestamp field directly to current inputs is prohibited because it
would create an unverifiable compatibility path rather than timing authority.

## Evidence and non-activation

- Post-hoc expected hash accepted: `true`.
- Exact report20/report21 reconstruction: `PASS`.
- `declared_at` supported by current exact input: `false`.
- Timing authority: `NOT_PROVEN`.

Machine-auditable adversarial result:

```text
POST_HOC_EXPECTED_HASH_ACCEPTED=True
DECLARED_AT_SUPPORTED=False
TIMING_AUTHORITY=NOT_PROVEN
```

Any future timing-authority contract must require immutable persistence and
source linkage in addition to the declaration, chronology, external-anchor,
uniqueness, freshness, and rollback-resistance requirements above.
- ResourceWarning: `0`.

No production code, consumer, builder, protocol, service, browser, persistence,
current, pointer, paper, or live path is changed by this clarification.
