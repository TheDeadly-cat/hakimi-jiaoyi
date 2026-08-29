# ADR0280: Source-Baseline Provider Conformance Presentation Envelope v1

## Status

Accepted as an unmounted, neutral presentation candidate.

## Context

ADR0279 produces exact provider identity binding and conformance-plan documents.
Those documents are governance evidence, not a bounded frontend projection. The
plan contains fourteen case records and has no ordered presentation axes.

Existing application presentation envelopes use sealed, unmounted candidates
with axes, summaries, lineage hashes, facts, blockers, and authority locks. A
pure synthetic gap proof confirmed that ADR0279 has no first-party presentation
envelope, presentation status, or ordered stage projection.

## Decision

Add one import-only presentation envelope with the fixed stage order:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

For exact ADR0279 inputs the states are:

- `SOURCE`: `BOUND`;
- `GAP`: `OPEN`;
- `MATURITY`: `PREREGISTERED_NOT_RUN`;
- `PERMISSION`: `BLOCKED`.

The display tone is `NEUTRAL`, presentation status is `UNMOUNTED_CANDIDATE`, and
the display state is
`SOURCE_BOUND_CONFORMANCE_NOT_RUN_PERMISSION_BLOCKED`.

The projection includes only six lineage hashes, five bounded counts, seven gap
identifiers, fixed facts, and authority locks. It does not embed the fourteen
raw conformance cases, source documents, operator claims, registry ID, trust
domain, endpoint, credentials, public/private keys, or signatures.

Invalid or promoted inputs produce the same four axes in `UNKNOWN` state with
no lineage hashes or maturity counts. Exact-envelope verification uses a full
rebuild against the exact ADR0279 source chain.

## Adversarial matrix

- exact source chain: bounded neutral envelope;
- plan or binding tampering: ordered `UNKNOWN` projection;
- resealed provider-conformance promotion: `UNKNOWN`;
- resealed UI/current/permission promotion: exact verifier failure;
- raw cases or identity material: forbidden;
- READY, profitability, positive color, or trading-authority language: forbidden;
- HTTP registration or UI mount: false.

## Non-claims

This contract does not mount a frontend, alter CSS or JavaScript, register HTTP,
activate current evidence, call a provider, execute conformance cases, access
runtime state, authorize paper/live activity, prove market validity, demonstrate
strategy performance, or prove profitability. No browser or visual validation
claim is made.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
