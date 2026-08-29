# ADR 0039: Shared strict governance primitives

Date: 2026-08-21

## Status

Accepted for non-schema-changing internal refactoring.

## Context

The registry projection, persistence protocol, and persistence projection repeated
native boolean, SHA-256, date/timestamp, and authority-lock helpers. Repetition makes
type-alias and cutoff semantics easier to drift. The formal-registry adapter contains
similar helpers, but its exact source SHA-256 is already externally bound by the
persistence preregistration and cannot be changed silently.

## Decision

Add `strict_governance_primitives.py` with exact native-boolean, non-empty string,
lowercase SHA-256, canonical ISO date, UTC-second timestamp, strict before-cutoff,
and explicit locked-field checks.

Migrate only the three modules whose source is not frozen by the current protocol:

- registry candidate public projection
- formal persistence protocol
- formal persistence public projection

Keep the formal-registry adapter byte-for-byte unchanged. A future adapter helper
migration requires a versioned protocol-v2 source-hash transition.

## Consequences

- Strict semantics have one tested implementation for future governance modules.
- Existing schemas, static fingerprints, statuses, decisions, and output documents
  remain unchanged.
- Tests reject local duplicate helper reintroduction in migrated modules.
- Tests also fingerprint the excluded adapter to preserve preregistration validity.
