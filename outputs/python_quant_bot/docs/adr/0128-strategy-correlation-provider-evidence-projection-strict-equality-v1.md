# ADR 0128: Strategy correlation provider evidence projection strict equality v1

## Status

Accepted as verifier-only hardening for the ADR 0123 public projection. The
projection schema, static fingerprint, builder output, application envelope,
interface candidate, pre-mount policy, current state, and permissions are
unchanged.

Static fingerprint:
`20260822-strategy-correlation-provider-evidence-projection-strict-equality-1`.

## Demonstrated gap

The ADR 0123 verifier compared its rebuilt projection with ordinary Python
document equality. The projection is intentionally redacted and has no separate
projection hash, so Python's `False == 0` and `True == 1` aliasing directly
weakened exact-rebuild verification.

A synthetic observed projection contained 27 boolean leaves. Replacing each leaf
with its integer alias, without any other edit, was accepted in all 27 cases.
Affected fields covered semantic gate outcome, maturity, activation, claims,
redaction, profitability, current admission, writer activation, paper authority,
and live authority.

## Decision

Replace ordinary equality with `strict_json_contract_equal` in
`verify_strategy_correlation_provider_evidence_public_projection_v1`. Keep the
builder, schemas, static fingerprint, source verification, redaction, and
permission semantics unchanged.

Add a persistent property contract that attacks all 27 boolean leaves in both an
observed projection and an exact `UNKNOWN` projection. The two-state matrix makes
54 alias attempts and requires every attempt to block.

## Evidence

- pre-fix observed projection: 27 aliases attacked, 27 accepted;
- in-memory compile: 2 of 2;
- strict-equality contract: 4 of 4;
- provider-evidence family: 117 of 117;
- independent two-state replay: 54 aliases attacked, 0 accepted;
- application, interface, and pre-mount implementation fingerprints unchanged;
- remaining ordinary-equality strategy-correlation files after this slice: 14.

## Compatibility and authority boundary

Untampered observed and exact `UNKNOWN` projections continue to verify. A
verifier `PASS` still proves document contract integrity only, not provider gate
outcome, maturity, profitability, current admission, paper authorization, or
live authorization.

No route, writer, pointer, scheduler, runtime read, cache access, browser flow,
or natural-forward reader changes.