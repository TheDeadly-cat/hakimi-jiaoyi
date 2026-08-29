# ADR 0015: Isolated strict canonical hash for complete-link contracts

Status: Implemented for complete-link modules only

## Context

Four complete-link modules and the market-data envelope independently implemented the same strict JSON and SHA-256 routine. The older shared `canonical_hash` service is not byte-compatible with these contracts and accepts non-finite numbers, so replacing the new hashes with it would change sealed evidence and weaken fail-closed behavior.

## Decision

Add `strict_canonical_hash` using UTF-8, unescaped Unicode, sorted keys, compact separators, and `allow_nan=false`. Migrate the four complete-link modules and the market-data envelope whose existing bytes match this policy. Preserve the envelope-specific non-canonical-row error.

Do not modify or reinterpret the older canonical-hash contract. Existing complete-link schema versions and hashes remain stable.

## Consequences

- New strict-evidence serialization has one implementation.
- NaN, infinity, and non-JSON values fail closed.
- Legacy canonical hashes and historical artifacts do not drift.
- No strategy result, current pointer, profitability claim, or execution authority changes.
