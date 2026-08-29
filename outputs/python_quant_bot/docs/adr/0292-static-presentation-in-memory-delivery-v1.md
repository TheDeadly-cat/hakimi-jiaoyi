# ADR 0292: Static presentation in-memory delivery v1

## Status

Accepted as a pure in-memory Python-to-JavaScript delivery candidate. It has no
endpoint, route, host slot, DOM mount, browser execution, or runtime authority.

## Problem

ADR0289 produces the exact portfolio correlation admission candidate. ADR0290
defines the JavaScript rail, and ADR0291 registers its static assets. The remaining
consumer-first gap is a versioned handoff that proves the same candidate can cross
the Python/JavaScript boundary and produce a deterministic presentation receipt
without activating the application.

The existing source-baseline delivery adapter is bound to unrelated load-descriptor,
style-binding, source-envelope, identity, and nonce contracts. Reusing it would
create a false dependency and a duplicate compatibility path.

## Decision

Add a narrow pair:

- Python `static-presentation-in-memory-delivery-envelope-v1`; and
- JavaScript `static-presentation-in-memory-delivery-receipt-v1`.

The Python builder snapshots all inputs as native JSON, independently verifies
the exact ADR0291 registration and ADR0289 candidate against its source evidence,
then embeds only the ADR0289 candidate. It does not embed the source report,
correlation matrix, selection cells, cluster topology, strata map, or identity
context.

The JavaScript adapter verifies the sealed envelope, fixed ADR0291 registration
hash, exact ADR0290 consumer contract, ADR0289 candidate hash, and all permission
locks. It derives the rail view model and markup in memory, then stores only the
markup SHA-256 and length in a sealed receipt. Raw markup is not returned in the
receipt and no DOM API is available to the adapter.

Both local PASS and local BLOCK candidates are deliverable. Delivery status stays
`BLOCKED` because host activation is absent. An exact fail-closed Python envelope
may use `UNKNOWN` with a null payload; JavaScript preserves that state without
partial view or markup hashes.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact local PASS candidate | sealed no-DOM receipt with `LOCAL CLEAR` |
| Exact high-correlation BLOCK candidate | sealed receipt with `LOCAL BLOCK` |
| Registration authority promotion | Python UNKNOWN |
| Admission authority promotion | Python UNKNOWN |
| Source context drift | Python UNKNOWN |
| Mapping subclass or cyclic input | snapshot failure |
| Envelope hash substitution | JavaScript rejection |
| Registration hash swap after reseal | JavaScript rejection |
| Payload substitution without source-hash update | JavaScript rejection |
| Receipt authority promotion after reseal | exact-rebuild rejection |

## Activation order

1. ADR0291 static asset registration exact.
2. ADR0289 source candidate exact against source evidence.
3. Python in-memory envelope exact.
4. JavaScript envelope and rail candidate exact.
5. No-DOM receipt and markup hash exact.
6. Future adapter asset registration.
7. Future app import and stylesheet preregistration.
8. Future unmounted render review and browser visual review.
9. Future explicit route, mount, and current migration.

No step authorizes the next step.

## Permission and evidence boundary

The transport mode is `IN_MEMORY_ARGUMENT_ONLY`; endpoint, route, and host slot
are null. Delivery attempted, browser executed, DOM mounted, runtime mutations,
profitability proven, current admission, paper authorization, and live orders are
all false.

This work is not market evidence, profitability evidence, fresh holdout evidence,
forward observation, browser validation, paper/live authority, or release approval.
No runtime, cache, database, log, key, service, scheduler, browser, backtest, or
trading task is accessed or started.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
