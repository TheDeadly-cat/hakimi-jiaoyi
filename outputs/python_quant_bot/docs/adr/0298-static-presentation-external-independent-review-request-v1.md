# ADR 0298: Static presentation external independent review request v1

## Status

Accepted as a deterministic external-review request and unauthenticated local
claim intake. It does not complete or authenticate an independent review.

## Problem

ADR0297 registers the local no-DOM review package, but a future external reviewer
does not yet have one immutable target manifest and rubric. Local tests cannot
authenticate reviewer identity, establish process independence, verify a
signature, or prove replay durability.

Treating an all-true local claim as review completion would promote authority
without evidence.

## Decision

Add two exact contracts:

- `static-presentation-external-independent-review-request-v1`; and
- `static-presentation-external-independent-review-claim-intake-v1`.

The request public-verifies ADR0297 and binds:

- ADR0297 registration, manifest, implementation, test, and decision hashes;
- ADR0296 review implementation, Node test, and decision hashes;
- fixture-specific clear, high-correlation block, and exact unknown local
  receipt hashes;
- clear and block markup hashes and lengths; and
- a fixed nine-item reviewer rubric covering patch, no-DOM, behavior, neutral
  copy, privacy, dependency separation, permission, and non-profitability.

The local behavior hashes remain explicitly
`PURE_SYNTHETIC_NO_DOM_FIXTURE`. They are not browser, market, forward, or
profitability evidence.

The claim shape binds request and target-manifest hashes, requires strict
all-true rubric booleans and an independence declaration, and accepts stable
reviewer/process labels. Intake hashes those labels and embeds no raw claim or
identifiers.

Even a valid claim is only
`LOCAL_REVIEW_CLAIM_BOUND_EXTERNAL_INDEPENDENCE_UNPROVEN` with
`CLAIM_BOUND_UNVERIFIED`. Reviewer identity, process identity, signature,
replay durability, descriptor-content observation by the system, and external
review completion remain false.

Signature fields are not accepted by this version. An extra signature field is
a contract error rather than apparent authentication.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR0297 registration | awaiting external review request |
| Registration authority promotion | UNKNOWN request |
| Request or target cross-splice | UNKNOWN intake |
| Missing or extra claim field | UNKNOWN intake |
| Signature compatibility field | UNKNOWN intake |
| False, missing, extra, or integer rubric value | UNKNOWN intake |
| Blank or numeric reviewer label | UNKNOWN intake |
| Cyclic document | fail closed |
| Resealed completion/signature promotion | verifier rejection |

## Consumer-first activation order

1. Exact ADR0297 review-asset registration.
2. Bind the external-review target and rubric through ADR0298.
3. Deliver the request to a future external reviewer through a separately
   authorized channel.
4. Future reviewer/process authentication.
5. Future domain-separated signature verification.
6. Future durable nonce and replay enforcement.
7. Future independent-review completion only after all authentication evidence.
8. Future host-write authorization, browser review, DOM mount, and current
   activation through separate gates.

No step authorizes or automatically performs the next step.

## Permission and evidence boundary

This version does not send a request, contact a reviewer, accept a signature,
authenticate an identity, persist replay state, complete an independent review,
write host assets, execute a browser, mount UI, activate current, authorize paper
or live activity, or prove profitability.

No runtime, cache, database, log, key, service, scheduler, browser, backtest, or
trading task is accessed or started.

The public natural-forward chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
