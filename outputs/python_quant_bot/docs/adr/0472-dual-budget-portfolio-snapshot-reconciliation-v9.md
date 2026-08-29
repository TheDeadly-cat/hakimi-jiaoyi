# ADR0472: Dual-budget portfolio-snapshot reconciliation v9

Date: 2026-08-25

## Status

Accepted as a versioned research-only portfolio-scope bridge. It establishes no
runtime admission, provider source truth, paper/live permission, or `current`
activation.

## Context

ADR0471 reconciles proposal symbol, direction, notional, unit scale, and cluster
cap between dynamic budget v7 and legacy budget v11. It deliberately left
positions and equity unbound because those fields were not exposed by the v11
output.

A deeper exact-context audit found that v11 already consumes a signed portfolio
snapshot chain containing:

- a snapshot claim with equity, positions, gross, sequence, and observed time;
- an Ed25519 signed-snapshot document;
- snapshot signature evidence;
- a continuity/freshness transition document;
- the same bounded snapshot summary in the v11 output.

The source remains synthetic and explicitly leaves provider identity,
implementation, source truth, and freshness unverified.

A pure synthetic gap proof showed v8 proposal reconciliation `PASS` while v7
used pre-proposal A/2000 and the exact v11 snapshot used A/2500. Equity matched
at 10000, but portfolio scope did not.

## Decision

Add a v9 portfolio-snapshot preregistration and reconciliation consumer that:

- exact-verifies ADR0471 and requires its proposal scope to be locally `PASS`;
- binds the exact v8 preregistration hash, v11 snapshot-claim hash, v7
  positions-before hash, expected equity, sequence, observed time, and one
  positive integer legacy-unit scale;
- treats both v7 positions and the v11 snapshot as pre-proposal positions;
- extracts the v11 snapshot claim, evidence, transition, and evaluation build
  inputs from the exact predecessor context;
- normalizes legacy equity and position notionals into v7 minor units with
  lossless decimal-to-integer arithmetic;
- requires exact symbol, direction, notional, positions hash, equity, gross,
  position count, snapshot sequence, observed time, and lineage equality;
- embeds only hashes and bounded summaries, never raw positions, keys, or
  signatures;
- returns `UNKNOWN` for unverifiable predecessors, `BLOCK` for exact portfolio
  mismatches, and `PASS` only for local proposal-plus-portfolio scope equality.

A v9 `PASS` sets:

- `combined_budget_scope_status=PASS`;
- `combined_budget_status=LOCAL_RESEARCH_SCOPE_RECONCILED`;
- `combined_admission_status=BLOCKED`.

It does not authenticate the external snapshot provider or prove snapshot source
truth/freshness.

## Consumer-first activation order

1. Produce exact v7, v11, and v8 research documents without runtime authority.
2. Create the v9 preregistration for one specific signed snapshot and v7
   positions/equity scope.
3. Evaluate v9 only in synthetic or isolated read-only consumers.
4. Preserve provider-identity, source-truth, freshness, and admission blockers.
5. Require separate external provider conformance and runtime ADRs before any
   `current`, scheduler, paper, live, or public evidence integration.

## Adversarial matrix

- v8 PASS with A/2000 versus signed-snapshot A/2500;
- fully aligned A/2500, equity 10000, B/2500, and 50-percent cap;
- integer unit scale 100 across proposal, positions, and equity;
- equity and position-symbol drift;
- snapshot sequence preregistration drift;
- snapshot evidence/context tamper;
- exact blocked v8 predecessor;
- boolean scale/equity and malformed lineage hashes;
- resealed preregistration, snapshot summary, and authority promotion;
- deterministic output, input immutability, and raw-context redaction.

## Consequences

The two budget lines can now prove that they evaluated the same local proposal
and the same pre-proposal portfolio snapshot. This remains only local structural
and cryptographic consistency. External snapshot source truth, market-data
truth, profitability, execution, combined admission, runtime activation, and
paper/live permission remain unproven and unauthorized.
