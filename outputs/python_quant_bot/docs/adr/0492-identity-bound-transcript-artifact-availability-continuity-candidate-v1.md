# ADR 0492: Identity-bound transcript artifact availability continuity candidate v1

## Status

Accepted as an unmounted, synthetic-only candidate. It does not change any `current` selector, public evidence reader, pointer, runtime consumer, scheduler, or trading permission.

## Problem

ADR0491 verifies one exact local publication signature and one exact 2-artifact by 2-retriever set of challenge-bound retrieval signatures. That closes same-epoch duplication and role-collision gaps, but the same epoch evidence could still be presented repeatedly as if it represented continued availability.

An external availability claim cannot be manufactured from local timestamps. The narrow missing contract is therefore a preregistered logical sequence that makes replay and reordering detectable while preserving the explicit absence of external time, network, durability, identity, and independence evidence.

## Decision

Introduce `strategy-correlation-identity-bound-transcript-artifact-availability-continuity-evidence-v1` with these constraints:

1. ADR0491 remains the exact upstream verifier for every epoch.
2. The candidate supports exactly three logical epochs in v1.
3. The ADR0491 publisher signs the complete epoch plan under a new signature domain. Reusing the already-bound publisher key avoids inventing a new independence claim.
4. Each epoch preregisters one unique logical-slot commitment and the exact Cartesian product of two artifacts by two retrievers.
5. Every artifact/retriever/epoch pair has a globally unique challenge nonce hash.
6. Each epoch must produce a distinct four-receipt ADR0491 evidence document.
7. Signed retrieval receipt hashes must be globally unique across all three epochs.
8. Epoch descriptors form a previous-descriptor hash chain. Epoch observations form a separate previous-observation hash chain rooted in the signed schedule hash.
9. The aggregate exposes only source hashes, observation hashes, counts, neutral facts, blockers, and permission state. It does not expose raw schedules, challenge rows, public keys, signatures, receipts, locators, or artifact content.
10. The result remains `UNMOUNTED_CANDIDATE` and `BLOCKED`.

The three epochs are logical commitments only. They do not represent wall-clock truth, elapsed duration, external persistence, or public reachability.

## Consumer-first activation order

1. Keep builders and strict verifiers isolated in the application layer.
2. Exercise only pure synthetic, in-memory producer and adversarial consumer fixtures.
3. If a future consumer is proposed, make it read an explicit candidate version and fail closed on absent or malformed evidence.
4. Add genuinely external time, publication, retrieval, identity, and independence evidence under separate versioned contracts.
5. Require an explicit review before any selector or public reader can change.

No activation step is authorized by this ADR.

## Adversarial matrix

The candidate must reject:

- missing, duplicated, or reordered epochs;
- non-contiguous ordinals;
- duplicate slot commitments;
- incomplete or duplicate artifact/retriever pairs;
- challenge nonce replay within or across epochs;
- invalid publisher schedule signatures;
- schedule aliases or extra context fields;
- availability evidence replay across epochs;
- signed retrieval receipt replay across epochs;
- fixed-upstream registration, publication, or content-context drift;
- previous observation hash drift;
- final observation hash drift;
- raw key, signature, receipt, schedule, or challenge disclosure in aggregate evidence.

## Non-claims

Passing this contract proves only that three synthetic logical epochs are bound to one signed plan and contain distinct locally verified ADR0491 receipt sets.

It does not prove:

- external or trusted time;
- public artifact availability;
- network retrieval;
- publisher identity or operation;
- retriever identity or independence;
- storage durability or persistence;
- provider conformance outside the inherited local evidence boundary;
- profitability;
- paper or live trading authorization.

## Compatibility

The natural-forward public chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain `UNKNOWN`/null. Pointer-v2 fields and hash contract remain unchanged, and no pointer is automatically reissued.
