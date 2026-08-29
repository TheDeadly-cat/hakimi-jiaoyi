# ADR0427: Witness storage persistence admission presentation external review request v1

## Status

Accepted as a deterministic, undelivered external-review request. It is not an
external review, a review claim intake, a consumer registration, a host asset
registration, or an activation decision.

## Context

ADR0426 introduced an unmounted Python projection and a pure JavaScript view
model for the ADR0425 persistence decision. ADR0426 requires independent review
of redaction and out-of-band hash handling before consumer registration.

The ADR0298 review protocol cannot be reused as the review target because it
pins different ADR0296 and ADR0297 assets, behavior receipts, and host plans.
Treating that older request as compatible would create target substitution.
Proceeding directly to consumer registration would skip the declared activation
order.

## Decision

Add a witness-specific, deterministic external-review request. The builder has
no parameters and performs no filesystem, network, browser, storage, or runtime
operation. It binds constants that are independently checked against explicit
source paths by the targeted contract.

The target manifest pins:

- the ADR0426 Python projection, Python contract, JavaScript view model, Node
  contract, and ADR hashes;
- the Python and JavaScript strict-canonical implementations;
- protected preimages for `app.js`, `styles.css`, and
  `evidence_presentation.js`;
- source and view-model schema versions and static fingerprints;
- the `presentation_hash` and `view_model_hash` fields;
- the mandatory out-of-band exact source-presentation hash policy;
- the neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` order; and
- the prior local synthetic contract counts, explicitly scoped as no-DOM and
  not external evidence.

The request contains a fixed ten-item rubric. A future reviewer must assess
lineage verification, bounded projection, out-of-band hash use, strict input
shape, neutral stages, fail-closed behavior, redaction, absence of operations,
permission locks, protected preimages, and the unmounted boundary.

## Request-only boundary

`AWAITING_EXTERNAL_INDEPENDENT_REVIEW` means only that an exact target and
rubric are locally bound. The request remains undelivered. Reviewer identity,
reviewer process, signature, replay durability, and review completion are all
unverified. This version intentionally accepts no review claim and no
signature compatibility field.

Consumer preregistration remains explicitly blocked pending a future,
authenticated, independently verifiable review protocol. No parameter or
resealed document can promote this request into review completion or consumer
authority.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact deterministic rebuild | verifier accepts |
| Current explicit artifact hashes | exact target match |
| Protected host preimages | exact baseline match, no registration |
| Resealed completion or consumer authority | verifier rejects |
| Resealed target hash substitution | verifier rejects |
| Non-native mapping | verifier rejects |
| Cyclic document | verifier rejects |
| Extra compatibility field | verifier rejects |
| Mutable returned hash map | internal pins remain unchanged |
| Promotional or sensitive runtime wording | absent |

## Consumer-first continuation

1. Keep ADR0426 projection and view model unmounted.
2. Bind the exact target and rubric through ADR0427.
3. Deliver the request only through a separately authorized channel.
4. Authenticate reviewer and reviewer-process identity.
5. Verify a domain-separated signature and durable anti-replay state.
6. Record independently verifiable review completion through a future contract.
7. Only then consider consumer preregistration.
8. Keep host integration, browser execution, DOM mount, and current activation
   behind separate later decisions.

No step authorizes or automatically performs the next step.

## Evidence and permission boundary

This ADR does not contact a reviewer, accept a claim, authenticate an identity,
verify a signature, persist replay state, complete an external review, register
a consumer, modify a protected asset, execute a browser, mount UI, activate
current, authorize paper/live activity, or prove profitability.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
