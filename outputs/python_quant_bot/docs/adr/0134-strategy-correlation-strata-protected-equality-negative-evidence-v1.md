# ADR 0134: Strategy correlation strata protected equality negative evidence v1

## Status

Accepted as a regression and negative-evidence receipt. The four production
strata verifier files are unchanged. This decision does not activate a writer,
register a route, admit a current artifact, or authorize paper/live use.

Static fingerprint:
20260822-strategy-correlation-strata-protected-equality-negative-evidence-1

## Context

Six strata documents still use ordinary whole-document equality after hash,
authority, and source-verifier checks:

- preregistration and strata gate
- protocol registration
- registry asset and registry binding
- global independence gate

The combined documents contain 154 boolean leaves. No-reseal attacks accepted
none of 154. Correctly resealed attacks also accepted none of 154. Strict
equality replacement therefore has no demonstrated security effect in this
slice.

## Decision

Persist both attack modes as a 308-attack regression contract. Do not
mechanically replace equality in the four pinned production files without a new
demonstrated gap.

This negative result is distinct from ADR 0129, which fixed two unsealed public
projections, and ADR 0132/0133, which fixed demonstrated no-reseal gaps.

## Compatibility and authority

This receipt changes no schema, builder, verifier, hash algorithm,
natural-forward evidence, legacy pack-v5 UNKNOWN behavior, pointer-v2 contract,
current admission, route registration, profitability claim, paper
authorization, or live authorization.
