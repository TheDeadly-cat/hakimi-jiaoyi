# ADR0210: signed-review and execution-binding preregistration-v10

## Status

Accepted as an unmounted, research-only successor candidate. It does not replace
v9, register transport, mount UI, switch current, or authorize paper/live use.

## Observed gap

The immutable v9 builder accepts neither signed-review evidence-v1 nor execution
binding-v2. Its known document still reports fixture-v3 and registration-v1
evidence, leaves the render-review blocker unrefined, and omits transport plus
DOM/browser work from its activation order. A pure synthetic call-chain audit
proved all ten expected gap predicates.

## Decision

Add preregistration-v10 as a successor instead of changing v9. It fully reverifies:

1. Immutable preregistration-v9 and its complete verification context.
2. Signed render-descriptor review evidence-v1 and its full source context.
3. Presentation execution-evidence binding-v2 and its full source context.
4. A four-entry successor implementation manifest.
5. Descriptor hash identity between the signed review claim and executed fixture.

The signed evidence proves a bounded cryptographic claim only. It does not prove
reviewer identity, process independence, registration governance, nonce uniqueness,
replay protection, observed content review, or completed independent review.

## Consumer-first order

The candidate explicitly orders provider governance, reviewer independence,
review governance, observed content review, artifact/process authentication,
receipt signing, stylesheet/DOM/browser review, read-only HTTP transport,
read-only mount, and a separately authorized current switch. Paper and live
activation are not steps and remain false.

## Fail-closed behavior

Any context shape drift, manifest drift, verifier failure, source promotion,
authority promotion, malformed seal, or descriptor cross-splice produces an
UNKNOWN contract state. A known document remains BLOCKED and summary-only.

## Evidence boundary

Synthetic and contract checks can establish deterministic local reconstruction
only. They do not establish external provider trust, independent review, process
identity, signed execution provenance, DOM/browser behavior, runtime mounting,
profitability, or trading authority. The natural-forward current chain, legacy
pack-v5 UNKNOWN behavior, and pointer-v2 non-reissue contract remain unchanged.
