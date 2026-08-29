# ADR 0036: Protocol-v9 isolated formal-registry read adapter

Date: 2026-08-21

## Status

Accepted for isolated, synthetic, read-only contract evidence only.

## Context

A protocol-v9 candidate can be frozen, bound, and publicly projected while the
formal registry remains missing. The existing chain has no formal source snapshot
fingerprint, immutable adapter snapshot, exact-ID cardinality decision, or formal
persistence proof. Treating `CANDIDATE_BOUND` as a formal lookup would collapse this
boundary and could incorrectly admit a future writer.

## Decision

Add an in-memory copy-on-read adapter and two sealed contracts:

- `strategy-correlation-cluster-stability-formal-registry-read-record-v1`
- `strategy-correlation-cluster-stability-formal-registry-read-assessment-v1`

The record binds the formal source identity/version/hash, registry snapshot hash,
candidate asset/binding/protocol/policy hashes, and dates before the evidence cutoff.
The adapter fingerprints its complete in-memory record set, deep-copies at
construction, and deep-copies every lookup result.

Lookup uses an exact registry ID and requires exactly one record. Outcomes are
`CANDIDATE_RECORD_VERIFIED`, `MISSING`, `DUPLICATE`, `DRIFT`, or `UNKNOWN`.
No outcome sets `formal_persistence_verified` or `formal_registry_bound` to true.

The implementation exposes no file, database, network, provider, service, write,
publication, report-20 writer, or current-pointer interface.

## Consequences

- Missing and duplicate records cannot be silently selected or conflated.
- Source, registry snapshot, adapter snapshot, candidate hash, date, and authority
  drift fail closed.
- Tests can establish the read contract with pure synthetic records without touching
  a formal runtime or persistence layer.
- A real formal persistence adapter remains a separate future activation boundary.
- The public projection remains candidate-only and continues to show formal registry
  as missing.
