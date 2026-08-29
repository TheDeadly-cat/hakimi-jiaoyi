# ADR 0489: Identity-bound signed provider conformance bridge candidate v1

## Status

Accepted as an unmounted, synthetic-only candidate. It is not a current consumer and does not authorize provider activation, paper execution, or live execution.

## Context

ADR 0488 binds canonical proposal identity and replay-cursor CAS evidence to a locally verified signed provider receipt. The existing provider conformance contract preregisters 19 case identifiers, three structurally distinct observer registrations, and a two-of-three signed observer quorum.

The old conformance reports bind the old receipt evidence hash. They cannot be reused for the ADR 0488 receipt. The conformance plan may be reused only because it binds the receipt implementation and schemas rather than a specific business command. Each observer report and the final quorum must be rebuilt against the exact ADR 0488 receipt evidence hash.

## Decision

Add a narrow bridge that accepts only an exact pair:

1. An ADR 0488 identity-bound signed receipt bridge reconstructed under its original verification context.
2. A provider conformance quorum reconstructed from signed observer reports under its original plan, provider preregistration, observer registrations, and signed-receipt verification context.

The bridge cross-binds the ADR 0488 hash, quorum evidence hash, signed receipt evidence hash, conformance plan hash, provider preregistration hash, provider registry identifier, replay-cursor CAS hash, and provider command hash.

Old reports, old receipt evidence, single-observer evidence, duplicate identities, registry drift, context aliases, hash drift, and resealed permission promotion fail closed.

## Evidence semantics

A passing quorum proves only that preregistered local observer keys signed structurally complete claims for all 19 case identifiers. It does not prove that the cases were executed against an external provider. It does not prove observer legal identity, organizational independence, key-control continuity, test-execution source truth, provider endpoint identity, provider implementation identity, atomic compare-and-advance, durable commit, linearizable reads, restart recovery, or rollback resistance.

The output contains only bounded metadata and hashes. Raw observer reports, case rows, public keys, signatures, receipt documents, and cursor objects are not projected.

## Authority boundary

The neutral decision path remains:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

The final permission state remains `BLOCKED`. Runtime mounting, current admission, provider activation, paper authority, live authority, and profitability proof remain false.

## Consumer-first activation order

1. Keep ADR 0489 unmounted and validate it with pure synthetic fixtures.
2. Add a separately versioned provider-issued execution transcript and endpoint identity boundary.
3. Add restart and rollback-resistance evidence without granting cursor-write authority.
4. Add an isolated shadow observer that cannot mutate runtime state.
5. Collect natural-forward evidence under the existing single-look chain.
6. Consider a current switch only after separate authorization and complete acceptance evidence.

No step automatically activates the next step. No pointer is reissued by this ADR.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Exact ADR 0488 bridge plus exact rebuilt local quorum | Local candidate, permission blocked |
| Old quorum spliced onto the ADR 0488 receipt | Reject |
| One observer only | Reject |
| Identity bridge modified | Reject |
| Quorum evidence modified | Reject |
| Receipt evidence differs between consumers | Reject |
| Provider registry differs | Reject |
| Verification context adds compatibility aliases | Reject |
| Any expected hash differs | Reject |
| Mapping replaced by a shape-compatible object | Reject |
| External execution or conformance promoted | Reject |
| Raw reports, cases, keys, or signatures requested from output | Not present |

## Evidence scope

Validation is limited to targeted Python compilation, direct synthetic contracts, and an independent adversarial matrix. No historical bars, G50/G51, blind evaluation, provider endpoint, runtime provider, service, scheduler, browser, paper task, live task, or profit backtest is used.

The natural-forward chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain `UNKNOWN`/null, and pointer-v2 remains unchanged without automatic reissue.
