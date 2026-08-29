# ADR 0193: Presentation-consumer registration candidate v1

## Status

Accepted as a static, immutable, `BLOCKED` registration candidate. It does not
activate or execute the consumer, mount UI, register HTTP, switch `current`, or
grant runtime, paper, live, writer, registry, or migration authority.

## Context

ADR0192 proves that projection-v3 and card-v3 compose through a DOM-free fixture.
That fixture is still an implementation artifact, not a versioned consumer
registration. A registration candidate is needed before the fixture can be
pinned by a successor shadow preregistration, but it must not accept synthetic
rendering as DOM, browser, HTTP, or activation evidence.

## Decision

Add
`strategy-correlation-cluster-portfolio-risk-presentation-consumer-registration-candidate-v1`.
Its only input is an exact four-entry implementation manifest:

1. projection-v3 Python service
2. freshness-gate card-v3 JavaScript
3. freshness-gate card-v3 stylesheet
4. DOM-free presentation-consumer fixture-v3 JavaScript

The registration freezes projection/card/fixture schemas and fingerprints,
global names, `SOURCE -> GAP -> MATURITY -> PERMISSION`, exact composition,
unmounted execution, and always-unauthorized permission policy.

Matching all four hashes sets `registration_candidate_built=true` while
`registration_activated=false`. Status remains `BLOCKED`. The API accepts no
projection document, fixture descriptor, markup, DOM instance, browser result,
HTTP receipt, runtime handle, or trading evidence.

## Activation order

1. Bind exact projection-v3 evidence.
2. Execute fixture-v3 against the synthetic projection matrix.
3. Independently review the render descriptor.
4. Separately authorize isolated DOM contract review.
5. Separately authorize browser visual review.
6. Version presentation HTTP before mounting.
7. Separately authorize registration activation.
8. Separately authorize presentation mounting.
9. Keep `current` authorization last.

## Adversarial matrix

The contract covers actual file hashes, each hash drift, missing/extra/type-alias
manifest entries, exact schema/fingerprint/stage pins, candidate-versus-active
separation, evidence and authority denial, activation ordering, API narrowing,
output redaction, deterministic non-mutation, exact rebuild, import boundaries,
neutral wording, and permanent mount denial.

## Compatibility and evidence boundaries

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 fields and hash contract
are unchanged and no pointer is reissued. No runtime assets, market tasks,
backtests, services, browsers, schedulers, or trading paths are used.
