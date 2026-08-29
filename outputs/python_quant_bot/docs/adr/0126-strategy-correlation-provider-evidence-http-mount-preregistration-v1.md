# ADR 0126: Strategy correlation provider evidence HTTP mount preregistration v1

## Status

Accepted as a blocked, research-only pre-mount preregistration. It does not
register, expose, or authorize the ADR 0125 HTTP candidate.

Static fingerprint:
`20260822-strategy-correlation-provider-evidence-http-mount-preregistration-1`.

## Gap

The existing server provides loopback filtering, origin checks, no-store
responses, and baseline security headers. No versioned contract registers an
authentication mechanism, rate limit, request-body limit, trusted verification
context provider, request-log redaction policy, independent mount review, or the
candidate route itself.

Choosing arbitrary control values or mounting ADR 0125 directly would convert
unknown policy into accidental authority. The missing boundary is therefore a
blocked preregistration, not a route implementation.

## Decision

Preregister the proposed read-only transport:

- method: `POST`;
- route: `/api/v1/research/strategy-correlation/provider-evidence`;
- loopback and same-origin required;
- JSON request and response;
- `Cache-Control: no-store` and the current security-header baseline;
- no runtime or cache reads or writes;
- no request-body logging;
- verification contexts may not be supplied by the client.

The preregistration pins the SHA-256 values of the ADR 0125 adapter,
`server.py`, and `services/http_contract.py`. It accepts no caller overrides.

## Deliberately unresolved controls

The following controls remain unregistered and are permanent blockers in v1:

1. Authentication mechanism.
2. Rate-limit window, request count, and burst policy.
3. Maximum request-body bytes.
4. Server-owned trusted verification-context provider.
5. Request-log redaction policy.
6. Independent mount review.
7. Route registration.

Consequently `mount_allowed`, `registration_allowed`, and
`externally_callable` are always false. Passing verification proves only that
the blocked preregistration is exact and untampered.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Current source files match pinned hashes | Source pin contract passes |
| Caller tries to override route or controls | Builder rejects unexpected argument |
| Route or method is tampered | Exact-rebuild verification fails |
| Route is marked registered | Exact-rebuild verification fails |
| Authentication is forged as registered | Exact-rebuild verification fails |
| Mount authority is promoted | Exact-rebuild verification fails |
| Client context or request logging is enabled | Exact-rebuild verification fails |
| Document is rebuilt unchanged | Deterministic sealed preregistration |

## Activation order

1. Keep all seven blockers open in v1.
2. Design each missing control as a separate versioned contract with adversarial
   evidence.
3. Bind server-owned context provenance without exposing trust material.
4. Perform an independent combined policy review.
5. Only then design a mount admission gate. Do not modify `server.py` or
   `services/http_contract.py` before that gate exists.
6. Any route registration remains a separate explicit decision and must never be
   inferred from passing tests.

## Compatibility and authority boundary

ADR 0125 remains unregistered. `server.py`, `services/http_contract.py`, current
readers, pointer-v2, legacy pack-v5 behavior, and the natural-forward chain are
unchanged. Paper and live remain unauthorized.

This preregistration is not endpoint availability, runtime evidence,
profitability evidence, or trading authorization.
