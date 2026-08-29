# ADR 0098: Factor calibration calendar-bound observation admission gate v1

## Status

Accepted as an inactive, research-only consumer contract. It is not current
admission authority and does not activate long-horizon evaluation.

## Context

The calendar-session verifier v1 proves, on a strict synthetic call chain, that
every private observation date belongs to the intersection of the registered
identity and factor calendars and that every corresponding session closed no
later than the signed provider timestamp. Its highest state is deliberately
`CALENDAR_SESSIONS_VERIFIED_BATCH_NOT_ADMITTED`.

That source still carries five unresolved boundaries: external provider
identity, externally attested calendar-registration time, append-only replay
checking, long-horizon evaluation activation, and a distinct observation
admission receipt. Treating the calendar check as admission would collapse
source validation into permission and would allow correlated research evidence
to advance without the promised external controls.

## Decision

Introduce
`strategy-correlation-cross-lag-factor-calibration-long-horizon-calendar-bound-observation-admission-gate-candidate-v1`.

The gate:

1. Requires the exact calendar-session verifier v1 schema and expected hash.
2. Replays the complete calendar-session verification context instead of
   trusting a copied positive label.
3. Binds the calendar evaluation, calendar assignment, observation batch,
   schedule, batch verification, calendar registration, and future evaluation
   identifiers into one `admission_policy_hash`.
4. Freezes an ordered five-item external evidence manifest.
5. Produces only
   `SESSION_VERIFIED_ADMISSION_PREREQUISITES_UNREGISTERED` or `UNKNOWN`.
6. Keeps admission, evaluation, paper, live, current-pointer, profitability,
   and candidate activation authority false.

The v1 gate has no positive admission branch. That is intentional. Later
provider-identity, external-time, replay, activation, and admission-receipt
adapters must be versioned and verified consumer-first before a successor gate
may expose a stronger state. Synthetic fixtures can prove binding and failure
semantics but cannot establish those external facts.

## Failure semantics

Malformed expected hashes, unsupported source schemas, missing or extra context
fields, source tampering, private-batch drift, cross-binding drift, and source
authority drift map to a sealed `UNKNOWN` document. No compatibility fallback,
implicit alias, boolean override, or caller-supplied permission is accepted.

The public document exposes aggregate counts and lineage hashes only. It omits
private rows, returns, session-close ledgers, signatures, keys, and attestation
receipts.

## Activation order

1. Land and adversarially validate this inactive consumer contract.
2. Define external provider-identity and calendar-registration-time adapters.
3. Define an append-only replay registry receipt and verifier.
4. Define distinct evaluation-activation and observation-admission receipts.
5. Build a successor gate that verifies all five artifacts.
6. Only after independent review may a separate migration proposal discuss any
   active consumer. No current pointer is changed automatically.

## Consequences

The admission gap becomes an explicit, hash-bound contract instead of an
informal blocker list. The project gains a safe insertion point for future
external adapters without overstating current evidence. It does not create a
result, profitability evidence, trading permission, or paper/live authority.
