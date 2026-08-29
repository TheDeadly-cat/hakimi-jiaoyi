# ADR 0171: Native cutoff session-label manifest v1

## Status

Accepted as an additive native-cutoff research contract on 2026-08-22. It does
not define or evaluate freshness and does not activate shadow or runtime use.

## Context

ADR0168 binds two matrix payloads to provider-asserted UTC cutoffs because
neither matrix schema carries a cutoff. The upstream completed-price input does
carry a cutoff date and all frozen price rows. Existing contracts already prove:

1. Every preregistered symbol has a completed 61-row input.
2. Matrix replay embeds that exact completed-price input.
3. Common-support derivation binds the common price index hash.
4. Calendar/provider composition binds that index to a verified contiguous
   suffix of completed registered sessions.

The remaining gap is an explicit, redacted bridge from these native session
labels to the UTC cutoff field consumed by ADR0168.

## Decision

Add a native cutoff manifest that exact-verifies completed-price input, replay,
common-support derivation, and calendar/provider composition. It additionally
requires:

- Every symbol has the same ordered 61-session completed date grid.
- Dataset first/last dates match their frozen rows.
- Completed-price cutoff equals every dataset last session label.
- Calendar-session verification reports that same label as the final completed
  common session.
- Common-price index count and hash match the exact date grid.
- Expected UTC cutoff is exactly the session-label date encoded at midnight.

The midnight UTC value is only a canonical encoding of a session-label date.
It is not a claim about exchange close time, provider timestamp, ingestion time,
wall-clock currentness, or freshness.

The manifest outputs dataset hashes, date-grid hashes, first/last session labels,
and source receipt hashes. It excludes price rows, matrices, observation
batches, session checks, and runtime assets.

## Adversarial matrix

The targeted contract covers absent matrix cutoff, valid native cutoff, malformed
and non-midnight UTC values, wrong expected dates, completed-input cutoff
tampering, single-symbol date-grid drift, calendar last-session tampering,
common-index hash tampering, freshness non-claims, input immutability, source
redaction, resealed cutoff/authority/type changes, and research-only authority.

## Consequences

ADR0168 provider assertions can now be compared to a native completed-session
date manifest without guessing from matrix payloads. Freshness remains a
separate, unimplemented policy because session-label correctness does not imply
that a dataset is current at consumption time.

ADR0169 preregistration-v1 remains immutable BLOCKED. No shadow consumer,
risk-service version, server route, UI mount, current switch, backtest,
profitability evidence, paper authority, or live authority is added. The
natural-forward chain remains audit-v2/readiness-v3 ->
maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2.
