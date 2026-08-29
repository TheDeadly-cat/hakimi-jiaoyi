# ADR 0125: Strategy correlation provider evidence HTTP candidate v1

## Status

Accepted as an unregistered, interface-only, research candidate. It adds no
route, method, server registration, runtime read, runtime mutation, cache access,
current reference, writer, scheduler, paper authorization, or live authorization.

Static fingerprint:
`20260822-strategy-correlation-provider-evidence-http-candidate-1`.

## Gap

ADR 0124 added an unmounted application presentation envelope, while the
interface layer contained only the existing health adapter. A consumer-first
interface boundary was therefore absent. Mounting the application envelope
directly in `server.py` would skip request-shape, redaction, transport, and
authority contracts.

## Decision

Add an unregistered HTTP candidate adapter with separate request and response
schemas. The request contains exactly:

- request schema version;
- protocol public summary document;
- provider lifecycle replay gate document.

Trusted verification contexts are keyword-only adapter inputs and are not part
of the request document. They are never embedded in the response.

The sealed response always declares:

- `interface_status=UNREGISTERED_CANDIDATE`;
- `registered=false` and `externally_callable=false`;
- null method and route;
- no runtime or cache reads or writes;
- no current, paper, or live authority.

## Unknown handling

Malformed requests, invalid context types, application exceptions, failed
application verification, schema or fingerprint drift, axis drift, redaction
drift, or authority promotion produce a sealed `UNKNOWN` response with no
payload.

A correctly verified application envelope whose display state is `UNKNOWN` may
be carried as a payload, but the interface response remains `UNKNOWN` with
`result_available=false`. Verification of an unknown document must never become
result availability.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Exact request and observed envelope | Sealed observation, transport still unregistered |
| Extra, missing, or malformed request field | `UNKNOWN`, no payload |
| Verification context is not a plain dict | Application is not called; `UNKNOWN` |
| Application builder raises | `UNKNOWN`, no payload |
| Application verifier returns false | `UNKNOWN`, no payload |
| Verified application envelope is itself unknown | Unknown payload carried without result promotion |
| Forged application authority promotion | `UNKNOWN`, no payload |
| Request or context contains private markers | Markers absent from response |
| Response transport is tampered to registered | Exact-rebuild verification fails |
| Identical inputs are rebuilt | Byte-equivalent canonical response |

## Activation order

1. Keep the adapter unregistered and validate only pure synthetic contracts.
2. Independently review request provenance and trusted-context ownership.
3. Define route authentication, rate limits, and cache policy before any mount.
4. Add a new route only through a separate versioned HTTP contract and explicit
   server registration review.
5. Keep current readers and the natural-forward chain unchanged.
6. Never activate automatically from passing tests or observations.

## Compatibility and authority boundary

`server.py`, `services/http_contract.py`, existing interface modules, current
readers, pointer-v2, and legacy pack-v5 behavior remain unchanged. The
natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.

This candidate is not a live endpoint, browser/runtime evidence, profitability
evidence, or trading authorization.
