# ADR 0488: Identity-bound signed replay-cursor provider receipt bridge candidate v1

## Status

Accepted as an unmounted, synthetic-only candidate. It is not a current consumer and does not authorize paper or live execution.

## Context

ADR 0487 binds canonical proposal identity, position-derived post-merge exposure, v9 freshness, and an in-memory replay-cursor CAS result. The signed provider receipt contract separately proves that a receipt was signed by a preregistered local test key while keeping external provider identity and source truth blocked.

The existing fixtures expose a real compatibility gap: their projection, sequence, intent, command, and cursor identities differ. Reusing the old signed receipt would therefore be a splice, not compatibility. The provider outcome is also a strict `str` Enum. A plain string that looks equal is not an admissible provider result.

## Decision

Add a narrow bridge that accepts only the following exact chain:

1. An ADR 0487 identity-bound CAS bridge that reconstructs successfully under its original verification context.
2. A canonical compare-and-advance command whose stream, projection, intent, freshness fingerprint, attestation, sequence, nonce, transition receipt, base cursor, and proposed cursor match the ADR 0487 CAS result.
3. A provider result whose command, intent, observed cursor, returned cursor, and strict provider outcome match that command and CAS result.
4. A signed provider receipt evidence document that reconstructs successfully under the existing preregistered-key verifier.

The only admitted success mapping is:

`ADVANCED_IN_RETURNED_CURSOR -> ReplayCursorProviderOutcomeV1.ADVANCED`

CAS conflict, duplicate, already-consumed, sequence rejection, plain-string outcome aliases, and all other mappings fail closed.

The bridge output includes hashes and bounded registry metadata only. It does not expose raw receipt documents, cursor objects, public keys, or signatures.

## Authority boundary

A valid result proves only local structural and signature consistency. It does not prove external provider identity, external source truth, provider conformance, durable commit, linearizable read, replay-registry persistence, runtime mounting, current admission, profitability, or trading authority.

The neutral decision path remains:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

The final permission state remains `BLOCKED`.

## Consumer-first activation order

1. Keep this bridge unmounted and validate it with pure synthetic fixtures.
2. Add a separate provider-conformance evidence consumer that binds registry identity, command/result transcript, and signed receipt evidence.
3. Add an isolated shadow observer with no cursor writes and no current admission.
4. Collect natural-forward evidence under the existing single-look chain.
5. Consider a versioned current switch only after separate authorization and complete acceptance evidence.

No step automatically activates the next step. No pointer is reissued by this ADR.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR 0487 command/result plus valid signed receipt | Local candidate, permission blocked |
| Old signed fixture spliced onto ADR 0487 | Reject |
| Intent or transition-receipt hash changed and command resealed | Reject |
| Returned cursor changed | Reject |
| Registry identity changed | Reject |
| Provider rejection outcome used as success | Reject |
| Receipt evidence modified | Reject |
| Wrong signature | Reject |
| Verification context incomplete | Reject |
| Dataclass replaced by a shape-compatible alias | Reject |
| Expected hash changed | Reject |
| Raw receipt, cursor, key, or signature requested from output | Not present |

## Evidence scope

Validation is limited to targeted Python compilation, the direct synthetic contract, and an independent adversarial matrix. No historical bars, G50/G51, blind evaluation, runtime provider, service, scheduler, browser, paper task, or live task is used.

The natural-forward chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain `UNKNOWN`/null, and pointer-v2 remains unchanged without automatic reissue.
