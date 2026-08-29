# ADR0283: Source-Baseline Provider-Conformance Consumer Registration v1

## Status

Accepted as a hash-bound, unmounted consumer asset registration.

## Context

ADR0281 preregisters the exact producer payload. ADR0282 adds a pure JavaScript
neutral-card candidate and verifies it with Node, a Python-to-JavaScript
in-memory handoff, and adversarial inputs. The candidate is still absent from
all application, server, route, stylesheet, browser, and mount bindings.

Reusing portfolio-risk registration V9 would collapse distinct schemas and
asset manifests. Automatically rewriting ADR0281 would also erase the
consumer-first preregistration boundary. A new source-specific registration is
therefore required.

## Decision

Add a service-layer registration that pins:

- ADR0281 preregistration schema, static fingerprint, implementation SHA-256,
  and deterministic document hash;
- the ADR0281 payload schema and static fingerprint;
- the ADR0282 card schema, static fingerprint, JavaScript SHA-256, test SHA-256,
  and ADR SHA-256;
- the existing strict-canonical JavaScript dependency and exact load order;
- the three exported consumer functions and four ordered stages.

The manifest deliberately leaves stylesheet, `app.js` importer, and HTML
template null. The protected stylesheet hash is recorded only as a guard;
binding, reuse, and modification remain unauthorized. Test source is pinned as
a conformance reference, but no test result is embedded as runtime authority.

Add a hash-only binding candidate that exact-verifies the registration and the
full ADR0281 payload source chain. A valid binding records only registration,
payload, source-envelope, and card hashes. It remains `BLOCKED` and
`PAYLOAD_AND_CARD_HASH_BOUND_UNMOUNTED`. Invalid, promoted, drifting, cyclic, or
exception-raising inputs fail closed to `UNKNOWN`.

Both registration and payload inputs are recursively snapshotted once before
verification and later hash projection, preventing second-read substitution.

## Consumer-first activation order

1. ADR0281 producer preregistration remains frozen.
2. ADR0282 card candidate remains an isolated executable asset.
3. ADR0283 registers exact asset hashes and binds only exact payload hashes.
4. A later version may preregister an isolated stylesheet and app load point.
5. Route, mount, browser execution, visual review, and current admission require
   separate evidence and explicit authorization.

No step automatically promotes the next one.

## Adversarial matrix

- registration or payload drift: binding `UNKNOWN`;
- identity context drift: binding `UNKNOWN`;
- registration or payload second-read hash substitution: first snapshot value
  retained;
- registration snapshot exception: binding `UNKNOWN`;
- resealed binding mount promotion: exact verifier failure;
- raw payload, source documents, and identity material: omitted;
- stylesheet, app import, route, browser, mount, current, paper, and live:
  locked.

## Non-claims

This registration does not import the card into `app.js`, bind CSS or HTML,
register a route, execute a browser, mount UI, visually review the card, call a
provider, mutate runtime state, activate current evidence, authorize paper or
live activity, prove market validity, demonstrate strategy performance, or
prove profitability.

The public natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`
