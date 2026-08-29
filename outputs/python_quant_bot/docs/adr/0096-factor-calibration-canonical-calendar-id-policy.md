# ADR 0096: Canonical calendar ID policy

## Status

Accepted as a pre-activation correction to the unmounted calendar registration and session verifier candidates.

## Context

`exchange-calendars==4.13.2` lists aliases by default. `NYSE` and `XNYS` both resolve to the same `XNYS` calendar object, yet revision 1 allowed both IDs in one registration. A valid 80-session synthetic exchange batch could therefore report two distinct calendars and 160 checks while evaluating the same calendar twice.

## Decision

Calendar IDs must appear in `get_calendar_names(include_aliases=False)`. Names that exist only when aliases are included fail closed as `IDENTITY_CALENDAR_NONCANONICAL` or `FACTOR_CALENDAR_NONCANONICAL`; unknown names retain the existing unsupported blockers.

The schema names and function signatures remain unchanged because both candidates are unmounted, but their static fingerprints advance to calendar registration revision 2 and calendar-session verifier revision 2. Existing revision-1 hashes remain historical evidence and are not accepted as the current implementation fingerprint.

## Consequences

Canonical `XNYS`, `XNAS`, `XSHG`, `XHKG`, `CMES`, `24/5`, and `24/7` assignments remain available. Alias-equivalent labels cannot create duplicate semantic calendars, inflate aggregate check counts, or produce ambiguous assignment hashes. This correction does not activate a consumer or change observation admission and trading authority.
