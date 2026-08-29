# ADR 0324: Projection provenance verifier v1

## Status

Accepted as a synthetic-only correction to the unregistered ADR0323 adapter.
No HTTP, runtime, paper, live, or trading capability is activated.

## Finding

ADR0323 initially exposed a verifier that rebuilt the adapter envelope and
checked the projection's public canonical hash without retaining source
documents. Targeted tests and the ADR0316 through ADR0323 regression passed, but
an independent adversarial check changed the projection and recomputed all
public hashes. The verifier accepted that fully self-consistent forgery.

This is expected for unkeyed canonical hashes: they prove deterministic
consistency, not origin. The initial verifier name and adversarial claim were too
strong even though the adapter facts said projection semantics were not
re-executed. The failed adversarial run stopped baseline promotion.

## Decision

Revise the unregistered adapter to static fingerprint `lock-2` and contract hash:

`dd03303578e6b070b9c5ec6d6891658f63dd453001f30cdb069a9a03ac38a00c`

The failed `lock-1` contract hash
`b5a0894605088509d85e70163c77b6c9bcf8957469577f95f00a4e996bc8ad51`
is retained as lineage only. It was never activated or promoted into baseline
authority.

The verification boundary is split explicitly:

1. `verify_*_consistency_candidate_v1` accepts request, binding, scope, and the
   adapter document. It verifies receipts, role contracts, projection seal, and
   envelope reconstruction. It is explicitly non-authoritative for provenance.
2. `verify_*_candidate_v1` is the semantic gate. It additionally requires the
   original 13 positional and 10 keyword synthetic source documents.
3. The semantic gate snapshots those sources, matches all 23 source hashes with
   the creation receipt, and invokes the real ADR0317 verifier with the exact
   request, binding, source order, and keyword roles.
4. Source documents are ephemeral verifier inputs and remain absent from adapter
   evidence, receipts, logs, persistence, and host state.

The adapter output declares
`evidence_verification_level=CONSISTENCY_ONLY_WITHOUT_EPHEMERAL_SOURCES` and
`consistency_verifier_proves_projection_provenance=false`. Therefore a caller
cannot promote a consistency-only pass into a semantic or activation claim.

## Adversarial acceptance matrix

| Case | Consistency verifier | Semantic verifier |
| --- | --- | --- |
| Genuine adapter and exact sources | Pass | Pass |
| Shallow mutation without reseal | Fail | Fail |
| Fully resealed forged projection | Pass by design | Fail |
| Genuine adapter with one changed source | Pass | Fail |
| Wrong request, binding, scope, or receipt | Fail | Fail |
| Positional or keyword source order drift | Not independently knowable | Fail |
| Source document embedded in evidence | Contract failure | Contract failure |

## Consequences

The adapter now provides an honest two-level contract: durable hash-only
evidence can prove consistency, while semantic provenance is available only
during a controlled source-bearing verification call. Public hashes are never
treated as authentication or signatures.

Real security receipt producers, actual request-content hashing, request
lifecycle ownership, internal registration, mount controls, and independent
external-exposure review remain blockers. Natural-forward evidence, legacy
pack-v5 `UNKNOWN`, pointer-v2, and paper/live locks remain unchanged.
