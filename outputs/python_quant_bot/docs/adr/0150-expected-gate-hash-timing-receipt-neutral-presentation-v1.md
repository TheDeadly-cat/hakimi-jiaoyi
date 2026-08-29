# ADR 0150: Expected-gate timing receipt neutral presentation v1

- Status: Accepted, unmounted research-only candidate
- Date: 2026-08-22

## Context

ADR0149 introduced a verifier-only candidate timing receipt. Its structural
verification can pass while external authenticity, timing authority,
preregistration authority, maturity and all trading permissions remain false.
Presenting that result without a strict semantic boundary could turn a source
contract PASS into a misleading readiness signal.

## Decision

Add two inactive projection layers:

- an application envelope with fixed SOURCE, GAP, MATURITY and PERMISSION axes;
- an exact HTTP candidate response whose transport is permanently unregistered.

The application layer independently invokes the ADR0149 consumer and accepts
only its exact candidate-only PASS shape. It does not embed the receipt, replay
bindings or verification context. The SOURCE axis may state that the candidate
contract was verified. GAP must state that external anchor authenticity,
immutable persistence, uniqueness, freshness and rollback resistance are
unproven. MATURITY remains `NOT_PROVEN`; PERMISSION remains `RESEARCH ONLY` and
locked.

The HTTP candidate re-verifies the envelope, emits only the redacted envelope,
and fixes route, method, external callability, runtime reads/mutations and cache
reads/writes to absent or false. Neither layer contains a READY signal.

## Adversarial requirements

- Exact request and verification-context fields; extras fail closed.
- Source hash, gate commitment or receipt verification drift becomes UNKNOWN.
- Forged source or presentation authority is rejected even if an upstream mock
  claims PASS.
- Candidate receipt, source bindings and verification context are never echoed.
- Permission, transport and envelope tampering fail exact rebuild.
- No Electron import, server route, runtime bridge, writer or current reference.

## Boundary

This is a presentation contract, not a UI mount or external endpoint. It does
not prove that an anchor exists, establish timing or preregistration authority,
change natural-forward maturity, publish evidence, modify pointer-v2, or grant
paper/live permission. The current single-look chain and legacy pack-v5 UNKNOWN
behavior remain unchanged.
