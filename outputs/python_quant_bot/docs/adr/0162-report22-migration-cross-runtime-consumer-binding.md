# ADR 0162: report22 migration cross-runtime consumer binding

- Status: Accepted
- Date: 2026-08-22
- Scope: Unmounted Python-to-Node evidence consumer

## Context

ADR 0160 defined the Python HTTP candidate and ADR 0161 preregistered a blocked
future mount. The standalone Node lockboard previously accepted a public summary
directly. That proves the payload shape but not that a complete Python candidate
response survives transport serialization, strict canonical hashing and frontend
boundary validation without semantic drift.

## Decision

Add a browser-compatible, side-effect-free HTTP binding in front of the lockboard.
The binding implements the same UTF-8, sorted-key, compact JSON SHA-256 contract
as Python `strict_canonical_json_hash.py`. It validates the full candidate response
before exposing the payload to the lockboard.

Validation covers exact response keys, schema and fingerprint, response hash,
candidate state, facts, lineage, null method/route transport, research-only
authority, ordered blocker set and payload state consistency. The lockboard must
also accept the payload as an exact public-summary-v1. A hash mismatch, extra key,
native type alias, transport drift, state mismatch or even correctly resealed
authority escalation yields the fixed unverified UNKNOWN model.

A Python unittest constructs real NOT_SUPPLIED, UNKNOWN, PLAN_LISTED and both
DRY_RUN report22 decisions through the production assessment, public projection
and HTTP candidate, serializes them to Node, and checks the binding result. This
is in-memory cross-runtime evidence only; it does not use an endpoint or browser.

## Consumer-first activation order

1. Build and seal the Python HTTP candidate response.
2. Verify the complete response in the Node HTTP binding.
3. Pass only a verified payload to the existing lockboard.
4. Keep the binding absent from app.js and index.html.
5. Create a separate sealed consumer-binding review before changing the blocked
   mount preregistration.

## Consequences

The Python and Node contracts now share executable evidence for canonical hash and
state semantics. The result does not complete mount review, register a route,
start a service or browser, execute migration, change current/single-look/pointer,
or grant paper/live and profitability authority.
