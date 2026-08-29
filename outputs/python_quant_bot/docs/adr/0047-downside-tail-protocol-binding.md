# ADR 0047: Downside-tail protocol registration and candidate binding

## Status

Candidate protocol and binding assessment implemented. Neither is formal or current.

## Registration boundary

The protocol is built only from the fixed downside-tail source registration. It pins the source registration hash, identity-set hash, stratum-assignment hash, gate schema/fingerprint, consumer schema/fingerprint, and BLOCK-preservation rules.

The protocol deliberately contains no evaluation hash or observed gate decision. Those values do not exist at preregistration time and adding them later would create a post-hoc protocol. Registration timing remains unattested until a separate formal registry exists.

## Binding decision

After observation, a candidate binding assessment requires:

- exact protocol reconstruction;
- an externally pinned protocol hash;
- externally pinned registration and evaluation hashes;
- an exact, verified read-only consumer receipt.

Observed PASS and observed BLOCK evidence may both be CANDIDATE_BOUND because binding validity is separate from the statistical gate decision. A sealed UNKNOWN becomes CANDIDATE_BLOCKED. Contract, hash, receipt, or authority drift becomes UNKNOWN.

## Authority boundary

CANDIDATE_BOUND is not formal registration, timing proof, independent-vote authority, current admission, writer activation, paper authorization, live authorization, or profitability evidence. All such fields remain false and a numeric false alias is rejected even when the document is resealed.

The assessment emits only hashes, source/gate/binding state, fixed blockers, and verification booleans. It emits no observations, returns, pair identities, strata, overlap values, or p-values.

## Next order

1. Candidate gate and read-only consumer.
2. This source-bound protocol and candidate binding.
3. Redacted public projection and optional unmounted neutral UI.
4. Separate formal registry/persistence migration only after independent review; no automatic current switch.
