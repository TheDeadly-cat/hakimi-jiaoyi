# ADR 0094: Long-horizon calendar registration v1

## Status

Accepted as an unmounted, research-only local calendar assignment. It contains no observation sessions and does not admit a batch.

## Context

The pure-synthetic 80-row batch currently uses consecutive calendar dates and includes 23 weekend dates while still satisfying structural verification. The verified source context contains no market, exchange calendar, timezone, completed-session, or close-time binding. A global weekend ban would also be incorrect for 24/7 assets.

## Decision

Add schema `strategy-correlation-cross-lag-factor-calibration-long-horizon-calendar-registration-candidate-v1`. The current unmounted implementation revision fingerprint is `20260922-cross-lag-factor-calibration-long-horizon-calendar-registration-2`; revision 1 was superseded before activation after the canonical-name audit.

The registration pins `exchange-calendars==4.13.2`, one canonical calendar ID for each identity-order position, a canonical factor calendar ID, the source schedule and identity-order hashes, the common-date rule `INTERSECTION_OF_COMPLETED_REGISTERED_SESSIONS_V1`, session-label semantics, and completion relative to the provider UTC timestamp. Both installed distribution metadata and the loaded module version must equal the pin. Calendar registry lookup failures degrade to `UNKNOWN` rather than escaping the fail-closed boundary. IDs must appear in `get_calendar_names(include_aliases=False)`; aliases such as `NYSE` that resolve to canonical `XNYS` are rejected so one underlying calendar cannot be represented or counted twice. Mixed exchange and 24/7 assignments remain allowed.

The positive state is only `CALENDAR_ASSIGNMENT_DECLARED_NOT_EXTERNALLY_TIME_ATTESTED`. It exposes position-indexed calendar IDs but not identity labels, sessions, observations, results, or authority. The local declaration time must follow the schedule declaration and precede evaluation, but it is not external timing proof.

## Consequences

A later calendar-session verifier can distinguish valid exchange sessions from 24/7 dates and intersect them across identities and factor before accepting the fixed 80-position prefix. The existing synthetic weekend batch is not promoted or rewritten. The current natural-forward chain remains unchanged.
