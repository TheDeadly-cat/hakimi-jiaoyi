# ADR 0219: Consumer-v5 local Node execution receipt-v3

## Status

Accepted for the synthetic, unmounted, research-only contract surface.

## Context

Registration-v4 pins projection-v5, card-v5, stylesheet-v5, consumer-v5,
cross-runtime tests, and their predecessor contracts. That registration proves
an exact static dependency set, but it does not prove that consumer-v5 was
actually invoked in a Node contract process.

The predecessor receipt-v2 is not reusable. It binds projection-v4, card-v4,
fixture-v4, and registration-v2. It also fixes one registration hash as a
constant, so aliasing a newer registration into that receipt would create a
false compatibility path.

## Decision

Introduce
evidence_portfolio_risk_joint_evidence_consumer_execution_receipt_v3.js as a
new, non-mounted local execution receipt.

The builder accepts exactly two inputs:

1. A sealed projection-v5 document.
2. A four-field registration-v4 binding containing schema version, static
   fingerprint, registration implementation SHA-256, and the actual dynamic
   registration hash.

The receipt performs these local checks:

1. Observe an actual Node contract process.
2. Verify the registration-v4 binding with exact keys.
3. Verify the projection-v5 seal through card-v5.
4. Reseal a v4 schema alias and prove that card-v5 rejects it.
5. Build the card-v5 view model.
6. Build and exactly verify the consumer-v5 descriptor.
7. Preserve either local joint-gate PASS or local joint-gate BLOCK without
   converting that state into presentation permission.
8. Confirm that the descriptor remains unmounted.
9. Confirm that projection and descriptor authorities remain locked.
10. Confirm that the stylesheet is declared but not executed.

The result is sealed with strict-canonical JSON and recursively frozen. It
binds only contract identities and document hashes. It does not embed the
projection, descriptor, markup, positions, return series, or source evidence.

A receipt status of PASS means only that this exact local Node execution path
was observed and rebuilt. A locally blocked strategy decision can and must
still produce a PASS execution receipt when the blocked state was preserved
exactly.

## Registration binding

The registration hash is supplied by an actual registration-v4 document. It is
not a source-code constant. The registration schema, static fingerprint, and
implementation SHA-256 remain exact constants so a hash from another
registration family cannot be substituted.

## Adversarial matrix

1. Valid projection with local PASS must produce a PASS execution receipt.
2. Valid projection with local BLOCK must remain BLOCK inside a PASS receipt.
3. A resealed projection-v4 alias must produce a BLOCK receipt.
4. A missing or extra registration-binding field must produce a BLOCK receipt.
5. A different valid registration hash must alter the receipt hash.
6. A resealed receipt authority promotion must fail exact verification.
7. A resealed projection authority promotion must remain blocked.
8. Receipt facts must deny process authentication, signature, browser, DOM,
   network, stylesheet execution, runtime binding, profitability, and trading
   authority.

All inputs are synthetic or in-memory. No runtime asset, database, cache, log,
secret, market task, browser, service, scheduler, or trading path is accessed.

## Activation order

Consumer-first activation remains:

1. registration-v4 static dependency lock.
2. receipt-v3 local Node execution observation.
3. future Python evidence-v3 binding the receipt independently.
4. future independent execution identity or signature evidence.
5. future descriptor and load-order review.
6. separate explicit decision for any production route or mount.

This ADR authorizes only step 2. It does not authorize the later steps.

## Consequences

The frontend-v5 chain now has a narrow execution-observation artifact without
changing production routes or current pointers. Python evidence-v3,
independent process identity, browser review, runtime mount, paper trading, and
live trading remain unimplemented or unauthorized.
