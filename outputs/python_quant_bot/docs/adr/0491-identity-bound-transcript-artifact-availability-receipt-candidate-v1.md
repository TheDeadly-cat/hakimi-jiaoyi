# ADR 0491: Identity-bound transcript artifact availability receipt candidate v1

## Status

Accepted as an unmounted, synthetic-only candidate. It performs no publication or retrieval operation and does not authorize current, runtime, paper, live, writer, provider activation, or trading activity.

## Context

ADR 0490 proves that caller-supplied transcript content matches the hashes and size bounds committed by the identity-bound local observer chain. It does not distinguish direct function input from content published at an immutable locator and independently retrieved.

ADR 0113 was audited for reuse. Its transparency log, Merkle checkpoint, specialized provider-identity role graph, time bounds, and source receipt chain belong to a different authority domain. Reusing it would create a false cross-domain alias. Copying it would create a parallel transparency authority before any real log governance exists.

## Decision

Add a narrower replay-cursor transcript protocol with five layers:

1. An exact ADR 0490 upstream and an artifact catalog derived from its two content bundles.
2. Redacted immutable locator and version commitments for each bundle.
3. One preregistered publisher key, two preregistered retriever keys, and structural key separation from the provider and all conformance observers.
4. A publisher signature over the complete artifact catalog and publication nonce.
5. Two challenge-bound retriever signatures per artifact, each committing to the publication receipt, artifact identity, locator/version commitments, content bundle hash, and total payload byte count.

Publisher and retriever identifiers, key hashes, organization claim hashes, and trust domains must be distinct. Exactly two retriever receipts are required for every artifact. Receipt pairs, receipt hashes, and challenge nonces must be unique.

No raw locator, URL, artifact payload, private key, public key, signature, publication claim, or retrieval claim is projected into aggregate evidence.

## Evidence semantics

A passing result proves only that preregistered local keys signed exact publication and retrieval claims over the ADR 0490 artifact catalog. Production code performs no network access and has no external time source. The signatures therefore do not prove legal identity, organizational independence, key custody, publication, retrieval, public visibility, persistence, or external time truth.

The state remains `OBSERVED_LOCAL_SIGNED_PUBLICATION_DUAL_RETRIEVAL_CLAIMS_CANDIDATE`, not external availability.

## Authority boundary

The neutral decision path remains:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

The final permission state remains `BLOCKED`. Provider conformance, runtime mounting, current admission, paper authority, live authority, and profitability proof remain false.

## Consumer-first activation order

1. Keep ADR 0491 unmounted and validate only synthetic in-memory claims and signatures.
2. Define an externally governed content-addressed publication service and retrieval API without changing this consumer.
3. Add detached network transport evidence and externally anchored timestamps.
4. Establish publisher/retriever identity, key custody, revocation, and operational independence.
5. Add repeated retrieval and persistence evidence across separately authorized checkpoints.
6. Bind runner/environment provenance and provider endpoint identity.
7. Collect natural-forward evidence under the existing single-look chain.
8. Consider a current switch only after separate authorization and complete acceptance evidence.

No step automatically activates the next step. No pointer is reissued by this ADR.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR 0490 plus one publisher and dual retrieval signatures | Local claim candidate, permission blocked |
| Missing or duplicate retrieval receipt | Reject |
| Wrong publisher or retriever signature | Reject |
| Reused challenge nonce | Reject |
| Publisher/retriever key collides with provider or observer key | Reject |
| Publisher/retriever organization or trust domain collides | Reject |
| Locator or immutable version commitment changes | Reject |
| Content bundle hash or byte count changes | Reject |
| Verification context adds compatibility aliases | Reject |
| Any expected hash differs | Reject |
| Mapping replaced by a shape-compatible object | Reject |
| External availability or identity promoted | Reject |
| Raw locator, key, signature, claim, or artifact requested from output | Not present |

## Evidence scope

Validation is limited to targeted Python compilation, direct synthetic contracts, and an independent adversarial matrix. No URL, network request, filesystem artifact, log, runtime state, cache, database, credential, provider endpoint, service, scheduler, browser, historical bars, G50/G51, blind evaluation, paper task, live task, or profit backtest is used.

The natural-forward chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain `UNKNOWN`/null, and pointer-v2 remains unchanged without automatic reissue.
