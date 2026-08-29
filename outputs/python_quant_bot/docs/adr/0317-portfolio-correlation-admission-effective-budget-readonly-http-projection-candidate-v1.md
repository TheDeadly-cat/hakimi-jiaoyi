# ADR 0317: Portfolio Correlation Admission Effective-Budget Read-Only HTTP Projection Candidate v1

- Status: Accepted as an unregistered candidate
- Date: 2026-08-24
- Scope: Pure synthetic, side-effect-free interface projection

## Context

ADR0316 made the Python provider callable resolvable from an exact internal-only
binding.  The next consumer-first boundary is an HTTP-shaped projection, not an
HTTP route.  ADR0314 requires its input source to be
`INTERNAL_PROVIDER_RESULT_ONLY` and forbids raw source inputs.

Allowing a client request to carry positions, reports, correlation matrices, or
provider verification context would make untrusted input look internally
verified.  Mounting directly in `server.py` would also skip authentication,
rate-limit, body-limit, log-redaction, and independent mount-review decisions.

## Decision

Add an interface candidate with:

- an exact external request shell containing only schema version and fixed
  projection ID;
- keyword-only internal provider binding, positional context, and keyword
  context parameters that are never embedded in the response;
- one safe snapshot of request, binding, and provider context;
- exact ADR0316 provider resolution;
- exactly one provider invocation followed by the existing ADR0311 verifier;
- structural rejection of provider authority, transport, source-document, or
  promotional drift even if a verifier is incorrectly forced true;
- deterministic KNOWN, UNKNOWN, and BLOCKED response states;
- a KNOWN payload containing only the existing hash-only presentation payload
  and lineage hashes;
- no payload for UNKNOWN or BLOCKED states.

## Three-state mapping

| Verified provider result | Projection state | Payload |
| --- | --- | --- |
| KNOWN | KNOWN | Hash-only presentation and hashes |
| UNKNOWN | UNKNOWN | None |
| BLOCKED | BLOCKED | None |
| Unverified or exceptional | UNKNOWN | None |

The interface status is always `UNREGISTERED_CANDIDATE`.  Transport fields keep
method, route, and endpoint null.  Runtime, database, cache, network, request
logging, browser, and DOM capabilities are false.

## Neutral presentation boundary

The projected presentation preserves the existing tier order and permanent
permission lock.  It does not add READY, profitability, return, alpha, or win-rate
language.  Source documents, positions, raw symbol lists, strategy identity, and
request context remain absent from the response.

## Adversarial requirements

| Mutation or action | Required result |
| --- | --- |
| Extra or drifted external request field | UNKNOWN before provider resolution |
| Malformed internal provider context | UNKNOWN before invocation |
| Drifted ADR0316 binding | UNKNOWN before invocation |
| Provider exception | UNKNOWN with no payload |
| Provider verifier false | UNKNOWN with no payload |
| Forged provider authority with forced verifier true | UNKNOWN with no payload |
| Transport, authority, or top-level response promotion | Exact verifier rejects |
| Cyclic or second-read input | Fail closed or preserve first snapshot |

## Mount remains a separate decision

ADR0317 does not choose an HTTP method or route and does not modify `server.py`
or `http_contract.py`.  A later mount preregistration must separately freeze
loopback and same-origin policy, authentication, rate limiting, request body
limit, trusted internal context provider, request log redaction, source hashes,
and independent review before any route can be registered.

## Non-authority

The candidate does not read runtime, database, cache, logs, or market data.  It
does not run a backtest or trading task.  Reproducing the existing KNOWN source
result is compatibility evidence only, not profitability evidence or paper/live
authority.  The natural-forward single-look chain, legacy pack-v5 UNKNOWN
behavior, and pointer-v2 remain unchanged.
