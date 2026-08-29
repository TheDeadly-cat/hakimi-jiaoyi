# ADR 0097: Calendar-session presentation envelope and timetable card v1

## Status

Accepted as an unmounted consumer-first presentation candidate. It is not referenced by the active page, does not fetch data, and cannot mount itself.

## Context

Calendar registration and session verification now provide aggregate local evidence, while provider identity, external registration time, replay, admission, profitability, paper, and live authority remain unresolved. Closing those gaps with synthetic local artifacts would be misleading. The next useful product step is therefore a truthful detached consumer that preserves the evidence hierarchy without activating it.

## Decision

Add a sealed Python presentation envelope and a strict-canonical JavaScript card. Both preserve `SOURCE -> GAP -> MATURITY -> PERMISSION`. Positive evidence maps only to `LOCAL_SESSION_BOUND`; a valid negative source maps to `EVIDENCE_BLOCK`; missing, unsupported, or tampered input maps to `UNKNOWN`. GAP always retains provider identity, external timing, and replay. MATURITY exposes only aggregate label/calendar/check counts, and PERMISSION remains locked.

The visual direction is a cool mineral exchange timetable. Four ordered stops represent canonical calendar assignment, common session labels, provider-time close, and admission lock. The card uses scoped CSS, local typography fallbacks, one route-scan animation, responsive 900/540 breakpoints, and reduced-motion support. It renders only through `textContent`, exposes no rows, returns, observation IDs, session labels, close times, buttons, requests, DOM queries, or page activation hooks.

## Consequences

The presentation can be independently tested before any mount decision. Its existence does not change current evidence, the natural-forward chain, pack/pointer contracts, observation admission, or trading authority. Browser and real-device rendering remain outside this static slice.
