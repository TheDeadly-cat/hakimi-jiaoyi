# ADR 0194: Shadow-consumer preregistration v7 presentation registration pins

## Status

Accepted as an immutable, `BLOCKED`, research-only preregistration. It does not
bind fixture or registration evidence, activate a consumer, review DOM/browser,
register HTTP, mount UI, switch `current`, or grant trading/runtime authority.

## Context

ADR0191 preregistration-v6 exactly verifies a thirty-three-pin predecessor and
pins the projection/card layer. ADR0192 adds a DOM-free consumer fixture, and
ADR0193 adds a static registration candidate. V6 cannot pin artifacts that did
not yet exist. Copying all thirty-three predecessor hashes into v7 would create
a duplicate manifest boundary.

## Decision

Add immutable preregistration-v7 with layered manifests:

1. The public v6 verifier owns and rechecks the thirty-three predecessor pins.
2. V7 accepts an exact three-entry successor manifest for v6 itself, fixture-v3,
   and registration-candidate-v1.
3. The resulting chain reports thirty-six total implementation pins without
   duplicating the predecessor map.

V7 also pins the registration candidate's schema, fingerprint, verifier schema,
implementation hash, status, and deterministic expected document hash. It does
not accept or rebuild a registration document and therefore records
`presentation_registration_v1_evidence_bound=false` and
`presentation_registration_v1_exactly_verified=false`.

The predecessor's fourteen shadow inputs, three closed local blockers, existing
blockers, contract pins, and authority locks are preserved. Only two new gaps
are appended: fixture execution evidence and registration-candidate evidence.
Existing DOM/browser/HTTP blockers are not duplicated.

## Consumer-first activation order

1. Execute the ADR0192 fixture against the synthetic projection matrix.
2. Independently review the frozen render descriptor.
3. Bind and exactly verify ADR0193 registration-candidate evidence.
4. Continue the existing isolated DOM/browser and HTTP prerequisites.
5. Separately authorize registration activation.
6. Separately authorize presentation mounting.
7. Keep `current` authorization last.

## Adversarial matrix

Contracts cover immutable v6 verification, 33+3 layered counting, all three
actual file hashes, each successor drift, missing/extra/type-alias manifests,
v6 tamper, context shape, fourteen-input and three-closure preservation, exact
two-blocker extension, expected registration hash, activation ordering, evidence
and authority denial, API narrowing, output redaction, deterministic
non-mutation, exact rebuild, import boundaries, and neutral wording.

## Compatibility and evidence boundaries

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 fields and hash contract
are unchanged and no pointer is reissued. No runtime assets, market tasks,
backtests, services, browsers, schedulers, or trading paths are used.
