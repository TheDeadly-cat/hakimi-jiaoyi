# ADR 0232: Downside-tail presentation consumer registration-v7

## Status

Accepted as a blocked, static registration candidate.

## Context

ADR0231 adds Python execution evidence-v4 for the unmounted downside-tail
consumer. That evidence binds a pre-registration receipt-v4 whose formal
registration fields are intentionally null. Mutating or automatically
reissuing that receipt after evidence exists would break the receipt and
evidence hashes and would erase the distinction between preregistered local
execution and later registration.

Presentation registration-v6 remains the latest predecessor registration, but
it pins the earlier receipt-v3/evidence-v3 consumer chain. Copying its eleven
artifact pins into a new manifest would create a duplicate manifest boundary.

## Decision

Add presentation consumer registration candidate-v7 with two layers:

1. exactly rebuild and verify registration-v6 as the predecessor;
2. require an exact 26-item delta manifest for ADR0225-ADR0231 and bind one
   public-verifier-approved execution evidence-v4 hash.

The delta contains one predecessor implementation, nine production or
presentation assets, nine verification assets, and seven decision records. It
does not copy the predecessor's internal manifest.

Evidence-v4 may preserve `CLEAR`, `TAIL_BLOCK`, or `EXACT_UNKNOWN`. All three
are valid evidence semantics, but none changes registration-v7 status from
`BLOCKED`. Registration verification PASS means only that the blocked candidate
was rebuilt exactly.

Registration-v7 does not backfill registration fields into receipt-v4. It
records that receipt-v4 is a pre-registration receipt and requires a future,
separately versioned post-registration execution receipt. This ADR does not
authorize or issue that receipt.

## Remaining blockers

- no post-registration execution receipt exists;
- external witness policy registry and organization identity are unbound;
- independent process witnessing and shared anti-replay are unverified;
- browser visual review is unperformed;
- production route, mount, activation, and current admission remain
  unauthorized.

## Consumer-first order

1. registration-v6 predecessor chain;
2. downside-tail adapter, neutral envelope, HTTP candidate, and projection;
3. unmounted card and consumer-v6;
4. local execution preregistration-v1;
5. pre-registration receipt-v4;
6. Python execution evidence-v4;
7. blocked registration-v7 candidate;
8. future post-registration receipt;
9. external identity, independent witness, browser review, and a separate
   production activation decision.

## Consequences

- The new implementation chain is versioned without modifying registration-v6
  or duplicating its manifest.
- Pre-registration evidence remains immutable and replayable.
- No source document, descriptor, markup, runtime asset, database, cache, log,
  service, browser, scheduler, market task, or trading path is accessed.
- Current admission, pointer-v2, presentation mounting, runtime activation,
  paper/live authority, migration, and writer authority remain false.
- This registration candidate is not profitability evidence and does not alter
  the natural-forward current evidence chain.
