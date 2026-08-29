# ADR 0028: Shared strict JSON contract helpers

- Status: Accepted
- Date: 2026-08-21
- Scope: global-independence governance modules

## Context

Five new governance modules independently implemented the same recursive JSON
comparison, and two also duplicated non-mutating canonical sealing. Repeating
that logic risks inconsistent bool/int handling, nested comparison drift, or
different stale-hash behavior at adjacent contract boundaries.

## Decision

Extend `strict_canonical_json_hash.py` with two shared functions:

- `strict_json_contract_equal` requires exact native types, exact dictionary
  key sets, recursive values, and ordered lists;
- `seal_strict_canonical_document` deep-copies a dictionary, removes a stale
  hash field, and seals the remaining payload with strict canonical JSON.

The report19 consumer, protocol-v8 registration, registry candidate, and both
public projections now call the shared helper. Schema fields, status logic,
blockers, fingerprints, and authority outcomes are unchanged.

## Consequences

Strict type and sealing behavior has one implementation and a dedicated test
contract. This refactor creates no runtime, persistence, registry, writer,
pointer, paper, or live behavior.
