# ADR 0129: Strategy correlation strata public projection strict equality v1

## Status

Accepted as verifier-only research hardening. This decision does not register a
route, activate a writer, admit a current artifact, or authorize paper/live use.

Static fingerprint:
20260822-strategy-correlation-strata-public-projection-strict-equality-1

## Context

Python container equality treats booleans and integers as equal. A synthetic
attack against the real preregistered-strata call chain exercised eight
whole-document rebuild verifiers and 179 boolean leaves. Six hash or
authority-protected documents rejected all 154 attacks. The two unsealed public
projections accepted all 25 attacks: 12 in the strata public summary and 13 in
the protocol migration public summary.

The accepted paths covered permission and redaction fields, including
profitability, current admission, writer activation, formal registry
activation, paper, live, identity exposure, artifact exposure, classification
source exposure, and selection cutoff exposure.

## Decision

Use strict_json_contract_equal for the exact rebuild comparison in:

- strategy_correlation_strata_projection.py
- strategy_correlation_strata_protocol_projection.py

Do not mechanically replace the six protected verifier comparisons. Their
current authority and hash checks independently rejected the observed aliases,
and changing them without a separate demonstrated gap would enlarge the slice
without improving the proven boundary.

Keep schema versions, builders, static fingerprints, blocker names, redaction
shape, and permission shape unchanged.

## Adversarial contract

The persistent contract covers both OBSERVED and UNKNOWN projections:

- strata public summary: 12 boolean leaves in each state
- protocol migration public summary: 13 boolean leaves in each state
- total: 50 bool/int alias attacks
- required result: every attack BLOCK with the existing exact rebuild blocker

## Compatibility and authority

This hardening does not change the natural-forward evidence chain, public
pack-v5 UNKNOWN behavior, pointer-v2 fields or hash contract, current admission,
route registration, formal persistence, paper authorization, or live
authorization. Verifier PASS remains document-integrity evidence only and is
not profitability evidence.
