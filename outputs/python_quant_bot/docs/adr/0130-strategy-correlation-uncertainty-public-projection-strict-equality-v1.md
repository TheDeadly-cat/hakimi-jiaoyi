# ADR 0130: Strategy correlation uncertainty public projection strict equality v1

## Status

Accepted as verifier-only research hardening. This decision does not activate a
writer, register a route, admit a current artifact, or authorize paper/live use.

Static fingerprint:
20260822-strategy-correlation-uncertainty-public-projection-strict-equality-1

## Context

A synthetic matrix covered six multiplicity and uncertainty rebuild verifiers
and 461 boolean leaves. Ordinary Python equality accepted 199 resealed or
unsealed bool/int aliases. A second strict-rebuild prediction separated actual
comparison weakness from source pass-through behavior:

- uncertainty public summary: 9 accepted and all 9 differ under strict JSON
- uncertainty audit: 183 accepted but all 183 remain strictly equal after rebuild
- multiplicity audit: 5 accepted but all 5 remain strictly equal after rebuild
- multiplicity family registration: 2 accepted but both remain strictly equal
- uncertainty policy and multiplicity binding: no accepted aliases

Replacing equality in the three pass-through cases would not block the observed
attacks and would create false confidence. Those cases remain governed by their
upstream verifier contracts.

## Decision

Use strict_json_contract_equal for fixed public-value comparisons and for the
final whole-document comparison when a source audit is supplied. Preserve the
existing source-free local verification path while making its fixed boolean
fields type-strict.

Keep the schema, builder, public fields, gap calculation, blocker names, source
verification, maturity, permission fields, and status vocabulary unchanged.

## Adversarial contract

The persistent contract covers both projection states:

- OBSERVED summary: 9 boolean leaves
- UNKNOWN summary: 9 boolean leaves
- total: 18 bool/int alias attacks
- required result: every attack BLOCK

## Compatibility and authority

This hardening does not change the natural-forward evidence chain, legacy
pack-v5 UNKNOWN behavior, pointer-v2 fields or hash contract, current admission,
route registration, profitability claims, paper authorization, or live
authorization. Verifier PASS remains document-integrity evidence only.
