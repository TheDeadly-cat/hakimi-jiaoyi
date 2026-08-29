# ADR0429: Correlation uncertainty card-style external review request v1

## Status

Accepted as a deterministic, undelivered external style-review request. It is
not an external review, review-claim intake, asset-pair preregistration, browser
review, host import, or mount decision.

## Context

ADR0348 supplies the unmounted semantic card. ADR0428 supplies the scoped,
responsive stylesheet candidate and static contract. The next consumer-first
step is independent semantic and style review, not host integration.

The witness-specific ADR0427 request binds a different projection, view model,
and rubric. Reusing it for this card and stylesheet would be target
substitution. A target-specific request is required.

## Decision

Add a zero-parameter, zero-I/O review-request builder. The deterministic target
manifest pins:

- the upstream sealed presentation, semantic card, card test, and ADR0348;
- the stylesheet, style test, and ADR0428;
- the strict-canonical JavaScript implementation;
- protected preimages for app.js, evidence_presentation.js, and styles.css;
- the card schema and static fingerprint;
- the exact stylesheet filename and namespace;
- the SOURCE -> GAP -> MATURITY -> PERMISSION order;
- the prior 14 card and 13 style contract counts, explicitly scoped as static
  and synthetic no-browser evidence; and
- the declared responsive, reduced-motion, contrast, forced-colors, print,
  finite-motion, external-resource, host-scope, and text-cue properties.

The fixed eleven-item rubric requires a future reviewer to assess the exact
card-style hash pair, scope isolation, responsive intent, external-resource
absence, fallback behavior, gap and permission distinction, host preimages,
disclosure, stage order, upstream validation, and neutral copy.

## Request-only boundary

AWAITING_EXTERNAL_INDEPENDENT_STYLE_REVIEW means only that a local target and
rubric are hash-bound. Request delivery, reviewer identity, reviewer process,
signature verification, replay durability, external review completion,
asset-pair preregistration, browser execution, DOM mount, current, writer,
paper, and live authority remain false.

This version accepts no review claim or signature compatibility field. A
resealed request cannot promote completion or registration authority because
the exact verifier rebuilds the full document.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact deterministic rebuild | verifier accepts |
| Eight explicit review artifacts | current hashes match |
| Three protected host preimages | current hashes match |
| Resealed review or registration promotion | verifier rejects |
| Resealed target hash substitution | verifier rejects |
| Non-native mapping | verifier rejects |
| Cyclic document | verifier rejects |
| Extra compatibility field | verifier rejects |
| Mutated returned hash maps | internal pins remain unchanged |
| Promotional or sensitive runtime wording | absent |

## Consumer-first continuation

1. Keep the card and stylesheet unmounted.
2. Bind the exact review target and rubric through ADR0429.
3. Deliver the request only through a separately authorized channel.
4. Authenticate reviewer and reviewer-process identity.
5. Verify a domain-separated signature and durable anti-replay state.
6. Record independently verifiable review completion through a future contract.
7. Only then consider exact asset-pair preregistration.
8. Keep isolated browser review, production import, route, DOM mount, current,
   writer, paper, and live authority behind separate decisions.

No step authorizes or automatically performs the next step.

## Evidence and permission boundary

This ADR does not contact a reviewer, accept a claim, authenticate an identity,
complete an external review, register an asset, modify protected host files,
execute a browser, mount UI, activate current, authorize paper/live activity,
or prove strategy performance or profitability.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
