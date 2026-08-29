# ADR 0220: Consumer-v5 receipt-v3 Python evidence-v3

## Status

Accepted for synthetic cross-document verification only.

## Context

ADR 0219 adds a strict-canonical receipt produced by a local Node contract
process. That receipt proves that projection-v5, card-v5, and consumer-v5 were
invoked together and that the unmounted descriptor preserved either local
joint-gate PASS or BLOCK.

The receipt remains a self-reported local execution artifact. A second
language boundary is needed to recompute its canonical seal and bind it to the
exact projection-v5 and registration-v4 documents. That second boundary must
not claim that it independently witnessed the Node process or authenticated
its identity.

The predecessor Python evidence-v2 cannot be reused. It binds receipt-v2,
projection-v4, fixture-v4, and registration-v2. Its implementation remains
unchanged and its public compatibility boundary remains fail closed.

## Decision

Introduce
strategy_correlation_cluster_portfolio_risk_presentation_consumer_execution_evidence_v3.py.

The evidence builder accepts exactly three documents:

1. A receipt-v3 document returned by the Node contract.
2. The projection-v5 document consumed by that receipt.
3. The registration-v4 document whose dynamic hash the receipt binds.

The Python verifier independently performs these checks:

1. Recompute the receipt-v3 strict-canonical seal.
2. Require the exact receipt-v3 schema and static fingerprint.
3. Require a PASS receipt with no receipt blockers.
4. Require all receipt dependency pins.
5. Require the exact ten receipt checks, all true and blocking.
6. Require the exact receipt authority and fact locks.
7. Recompute the projection-v5 strict-canonical seal.
8. Require the projection-v5 identity and authority lock.
9. Bind the receipt projection hash to the supplied projection.
10. Exactly verify registration-v4 against its expected static manifest.
11. Bind the receipt registration hash to the supplied registration.
12. Cross-bind local joint-gate PASS or BLOCK without promoting it.
13. Bind the descriptor hash and neutral stage order.

The resulting evidence is itself strict-canonical sealed. It embeds no input
document, source evidence, descriptor, markup, position, return series, or
correlation matrix.

## Evidence calibration

Evidence-v3 can state that a Python contract process independently recomputed
the document seals and cross-document hash edges. It can also state that the
receipt reports local Node execution.

Evidence-v3 cannot state that Python independently witnessed the Node process.
It does not authenticate process identity, verify a signature, replay the
projection candidate semantics, execute CSS, access a DOM or browser, access
runtime assets, or establish external authority.

An evidence PASS therefore means only that the supplied receipt, projection,
and registration form an exact, authority-locked local contract bundle.

## Adversarial matrix

1. A valid local PASS receipt must produce PASS evidence.
2. A valid local BLOCK decision must remain BLOCK inside PASS evidence.
3. A resealed receipt authority promotion must block.
4. A valid alternate projection must break the receipt-projection edge.
5. A substituted registration hash must break the receipt-registration edge.
6. A substituted implementation pin must block.
7. A substituted local-gate state must block.
8. A resealed receipt-v2 schema alias must block.
9. A resealed evidence authority promotion must fail exact verification.
10. All process identity, signature, browser, runtime, profitability, paper,
    live, writer, current, and mount claims must remain false.

All cases use synthetic or in-memory documents. No service, browser, scheduler,
runtime store, database, cache, log, secret, market task, or trading path is
used.

## Activation order

Consumer-first activation remains:

1. registration-v4 static dependency lock.
2. receipt-v3 local Node execution observation.
3. evidence-v3 Python seal and cross-document binding.
4. future versioned registration that pins evidence-v3 and its tests.
5. future independent execution identity or signature evidence.
6. future descriptor and load-order review.
7. separate explicit decision for any production route or mount.

This ADR authorizes only step 3. It does not change current pointers, publish a
route, mount UI, or authorize paper or live trading.
