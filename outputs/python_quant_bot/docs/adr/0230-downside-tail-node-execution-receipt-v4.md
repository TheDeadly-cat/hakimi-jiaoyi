# ADR 0230: Downside-tail Node execution receipt-v4

## Status

Accepted as local, preregistered, unmounted execution evidence. It is not a formal presentation registration, process identity attestation, signature, browser review, runtime mount, current admission, or paper/live authorization.

## Context

ADR0229 established an unmounted projection-v6 Node consumer. Receipt-v3 proves execution for the older projection-v5 consumer and is bound to registration-v4. Reusing that registration binding for v6 would falsely imply that the new downside-tail consumer is already registered. Requiring a future registration-v7 would create a consumer-first dependency cycle.

## Decision

Add `portfolio-risk-downside-tail-consumer-execution-receipt-v4` and a sealed execution preregistration-v1.

The preregistration binds a caller-provided identifier to the exact projection, strict-canonical JavaScript, card, stylesheet, and consumer implementation hashes plus the fixed `LOCAL_NODE_CONTRACT_PROCESS_UNMOUNTED` profile. Its authority permanently denies formal registration, mount, current, paper, and live actions.

The execution receipt records:

- observation of a local Node contract process;
- exact preregistration verification;
- projection-v6 seal and v5 schema-alias rejection;
- exact card view-model and consumer descriptor construction;
- preservation of clear, downside-tail block, and exact UNKNOWN semantics;
- descriptor hash without embedding descriptor or markup;
- unmounted, no-DOM, no-browser, no-network, no-runtime-asset facts;
- explicit `formal_registration_bound=false` and null formal registration lineage;
- strict canonical receipt and verification hashes.

A receipt PASS means only that the preregistered local Node contract executed exactly and remained unmounted. It does not mean that the local strategy gate passed. A tail BLOCK or exact UNKNOWN source can and should coexist with a PASS execution receipt.

## Consumer-first activation order

1. Envelope, HTTP candidate, Python projection, and Node consumer, ADR0226 through ADR0229.
2. Local execution receipt-v4, this ADR.
3. Future Python execution evidence-v4 that independently verifies receipt output and source pins.
4. Future registration-v7 pins after evidence exists.
5. Separately authorized application integration and admission review with no automatic route, current, or pointer change.

## Consequences

The v6 consumer now has calibrated local execution evidence without claiming formal registration. No service, browser, DOM, runtime asset, or market task was used. No result proves profitability or authorizes paper/live activity. Existing natural-forward artifacts, legacy public reads, pointer-v2, and current admission remain unchanged.
