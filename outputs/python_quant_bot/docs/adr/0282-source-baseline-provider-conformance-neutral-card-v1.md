# ADR0282: Source-Baseline Provider-Conformance Neutral Card v1

## Status

Accepted as an unregistered, unmounted, asset-isolated implementation candidate.

## Context

ADR0281 preregisters a bounded consumer payload for the ADR0280 neutral
presentation envelope. A scoped source inventory found no JavaScript consumer
for that payload. Existing portfolio-risk and anti-replay cards consume
different schemas and cannot be reused as if they were source-baseline assets.

ADR0281 remains immutable preregistration evidence. Its
`consumer_implementation_present: false` field describes that preregistration
phase and is not automatically rewritten or promoted when this separate
candidate file is created.

## Decision

Add a pure JavaScript card module that:

- pins the ADR0281 payload schema, static fingerprint, implementation SHA-256,
  and deterministic preregistration document hash;
- pins the existing strict-canonical JavaScript helper;
- snapshots external input once before verification and projection;
- exact-verifies the sealed payload, bounded fields, four ordered axes, seven
  blockers, five counts, locked permission object, facts, and authority;
- rejects all added, omitted, reordered, promoted, or non-canonical input;
- produces a sealed neutral view model with separate source, required,
  executed, passed, and open-gap counts;
- renders an escaped HTML string with `SOURCE -> GAP -> MATURITY -> PERMISSION`,
  an open-gap register, provenance hash abbreviations, and explicit permission
  locks.

The module uses a UMD/CommonJS boundary and has no DOM, network, provider,
filesystem, route, storage, timer, or application import. It does not modify or
reuse the protected stylesheet and is not imported by `app.js`.

## Consumer-first activation order

1. Keep ADR0281 as the frozen producer-side preregistration.
2. Validate this candidate against exact synthetic Python output and adversarial
   JavaScript inputs.
3. Create a future registration version that pins this candidate's final hash.
4. Preregister any stylesheet reuse, route binding, and mount location without
   changing current evidence.
5. Perform browser rendering and visual review only after explicit authorization.

No later step is implied or automatically activated by this ADR.

## Adversarial matrix

- invalid seal or extra top-level field: reject;
- status, tone, execution count, pass count, or permission promotion: reject;
- stage reorder or blocker omission: reject;
- throwing getter or unsupported canonical value: fail closed;
- second-read provenance substitution: frozen at the first snapshot value;
- input mutation: forbidden;
- READY, profitability, return, alpha, or win-rate language: forbidden.

## Non-claims

This candidate is not registered, routed, styled, mounted, browser-executed, or
visually reviewed. It does not call a provider, mutate runtime state, activate
current evidence, authorize paper or live activity, prove market validity,
demonstrate strategy performance, or prove profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
