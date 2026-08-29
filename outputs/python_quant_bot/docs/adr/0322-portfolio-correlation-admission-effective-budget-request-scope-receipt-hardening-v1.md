# ADR 0322: Request-scope receipt hardening v1

## Status

Accepted as a fail-closed hardening of the synthetic, unregistered ADR0321
candidate. No consumer, handler, route, runtime, paper, or live capability is
activated.

## Problem

Independent review of ADR0321 found two trust gaps:

1. A consumption receipt was compared with a caller-supplied creation receipt,
   but the creation receipt had no exact-rebuild verifier. A mutually forged
   creation/consumption pair could therefore pass the relative comparison.
2. `RequestLocalSourceContextCandidateV1` had a public constructor, allowing a
   caller to bypass the JSON snapshot, source-count, scope-evidence, and receipt
   checks performed by the builder.

The creation receipt also claimed source-hash provenance while exposing only the
aggregate context hash. That was insufficient evidence for an independent
rebuild without disclosing source documents.

## Decision

Revise the still-unregistered candidate to static fingerprint `lock-2` and pin
the new candidate contract hash:

`7fd73f90c797621c2df621cf5163bf9c83ba77d49f3262518c6c0a7cb72c72b1`

The prior `lock-1` contract hash
`5524137b7e093a197cdfaa256263540a3f50f09cb87d222bed084989d7fa3ac5`
remains embedded as lineage, not as accepted current authority.

The hardened implementation:

1. Adds the 13 positional and 10 keyword source hashes to the creation receipt
   in the already frozen ADR0319 contract order.
2. Still excludes every source document and source value from all receipts.
3. Adds `verify_context_creation_receipt_v1`, which exact-rebuilds the complete
   receipt from a fully verified request-scope candidate and the disclosed hash
   lists.
4. Requires `verify_context_consumption_receipt_v1` to validate that creation
   receipt before comparing the consumption receipt.
5. Requires an internal identity token in the context constructor. Only the
   validated builder receives that token; direct public construction fails.

The token is an API integrity guard inside the process, not a security boundary
against hostile Python code with module introspection. Runtime isolation and
real authentication remain external prerequisites.

## Adversarial acceptance matrix

| Case | Required result |
| --- | --- |
| Valid scope, creation, and consumption chain | All three exact verifiers pass |
| Mutation of any source hash | Creation verification fails |
| Reordered, missing, or extra source hash | Creation verification fails |
| Creation receipt from another scope | Creation verification fails |
| Forged creation receipt paired with consumption receipt | Consumption verification fails |
| Direct class construction | `TypeError` |
| Source sentinel search in receipts and `repr` | No match |
| Second resolution | `None` |
| HTTP, runtime, paper, live, or profitability inference | Explicitly false |

## Compatibility and activation

No registered consumer exists, so the hardening introduces no supported runtime
compatibility break. Any future adapter must require the `lock-2` contract and
must not accept a `lock-1` receipt through a compatibility fallback.

Consumer-first order remains: real security receipt producers, actual request
content hashing, request-lifecycle ownership, exact projection adapter proof,
internal consumer registration, mount controls, then independent exposure
review. The natural-forward chain and pointer-v2 contracts are unchanged.
