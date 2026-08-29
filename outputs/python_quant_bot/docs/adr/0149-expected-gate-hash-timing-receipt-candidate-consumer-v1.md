# ADR 0149: Expected-gate-hash timing receipt candidate consumer v1

- Status: Accepted, inactive research-only contract
- Date: 2026-08-22

## Context

ADR0148 proved that the report20 and report21 caller-supplied expected gate
hashes provide equality and substitution resistance but no declaration-time
authority. A post-hoc caller can evaluate a gate, copy its hash, and satisfy the
current exact binding. Adding a self-asserted timestamp would not close that
gap.

The existing protocol registrations provide preregistration chronology, while
the report consumers verify replay inputs and gate hashes. No current artifact
binds those elements to an independently verified external anchor, immutable
persistence, uniqueness, freshness, or rollback resistance.

## Decision

Add one consumer-only candidate receipt contract. It accepts either the
report20 cluster-stability binding shape or the report21 temporal-stability
binding shape and independently normalizes:

- the exact strategy, variant, and lane identity set;
- hashes of the uncertainty audit, correlation matrix, and selection cells;
- the caller-supplied expected gate hashes for the selected stage;
- the base artifact and protocol-registration hashes;
- declaration, anchor, and evidence-not-before timestamps;
- external anchor provider, namespace, event identifier, and receipt hash.

The consumer recomputes identity-set, source-linkage, gate-commitment, and
anchor-payload hashes. It requires declaration at or before anchoring and both
events strictly before the evidence-not-before boundary. It rejects duplicate
identities, extra binding fields, native boolean aliases, hash substitution,
timestamp drift, authority escalation, and compatibility aliases.

A structurally valid candidate returns verification `PASS` but decision
`BLOCK`. External-anchor authenticity, immutable persistence, uniqueness,
freshness, rollback resistance, timing authority, preregistration authority,
writer activation, current admission, paper, and live remain native `False`.
There is deliberately no receipt builder, provider adapter, persistence path,
or activation export.

## Consumer-first activation order

1. Keep this v1 candidate consumer inactive and verifier-only.
2. Separately authorize and implement a provider-specific read adapter with an
   independently controlled trust root.
3. Prove immutable write and independent reopen, exact uniqueness, freshness,
   rollback resistance, and source linkage with adversarial fixtures.
4. Introduce a new versioned authority assessment; do not widen v1 aliases.
5. Treat report writers, current admission, paper, and live as separate later
   decisions.

## Adversarial matrix

The targeted synthetic contract covers both gate stages, valid post-hoc
candidate containment, invalid chronology, evidence-boundary equality,
noncanonical timestamps, identity/source/gate hash drift, external receipt
substitution, duplicate identities, extra binding fields, authority escalation,
native false aliases, extra receipt fields, expected receipt hash drift, and
absence of builder or activation exports.

## Boundary

This contract is not an external timestamp service and does not establish that
any synthetic anchor existed at the asserted time. Candidate verification is
not timing authority, preregistration proof, formal persistence, market
evidence, profitability evidence, or trading permission. It does not alter the
single-look evidence chain, legacy pack-v5 handling, pointer-v2, current,
writer, scheduler, UI, paper, or live paths.
