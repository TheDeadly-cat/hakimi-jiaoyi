# ADR 0442: Verified risk-reduction effective-budget binding candidate V1

- Status: Accepted as an unbound synthetic candidate
- Date: 2026-08-25
- Scope: pure in-memory research contract only

## Evidence before decision

The synthetic adversarial chain reproduced three distinct states:

- effective-budget-v3 returned PASS and RISK_REDUCTION_PATH for a same-direction add when the caller supplied risk_increasing=false;
- binding-v1 remained fail-closed at CROSS_SOURCE_BINDING with only cross_source_hash_binding_failed;
- effective-budget-v4 blocked the same input because a verified position transition was missing.

Therefore this is not a current authorization bypass. It is a lower-level v3 classification gap plus a legitimate-risk-reduction availability gap at the current binding boundary.

## Decision

Add a new consumer candidate that accepts only the intersection of:

- an exactly rebuilt binding-v1 document that blocks solely at its conservative cross-source tier while admission-v2 and budget-v3 decisions are independently PASS;
- an exactly rebuilt budget-v4 PASS proving one existing position is reduced by an opposite-side order without crossing zero, changing another position, or accepting the caller flag alone;
- exact admission-v2, v3, v4, transition, proposal-scope, and authority-lock bindings.

The candidate does not modify binding-v1, budget-v3, budget-v4, any provider, route, current pointer, scheduler, runtime, or UI asset.

## Consumer-first activation order

1. SYNTHETIC_GAP_EVIDENCE
2. CANDIDATE_CONTRACT
3. ADVERSARIAL_REVIEW
4. READONLY_CONSUMER_PREREGISTRATION
5. SEPARATE_CURRENT_DECISION

This ADR completes only steps 1 through 3. Steps 4 and 5 remain unauthorized.

## Adversarial matrix

- Same-direction add labeled as reduction: BLOCKED.
- Missing or mismatched positions-after transition: BLOCKED.
- Cross-zero, reversal, new symbol, or unrelated position change: BLOCKED by v4.
- Forged legacy binding status or blockers: BLOCKED by exact rebuild.
- Forged v4 authority or resealed promotion: BLOCKED by exact rebuild.
- Proposal-scope or predecessor splice: BLOCKED by cross-version hashes.
- Boolean aliases, non-finite values, container subclasses, and cycles: BLOCKED at input snapshot.
- Valid opposite-side no-cross reduction: local candidate PASS, while admission_status remains BLOCKED and all runtime, current, paper, live, writer, and release authority remains false.

## Dependency pins

- binding-v1 implementation: 7263b07df309ad3c2a4c79313e62ff8912c567ee0cf6a2ee9abdc336ce6bd9e9
- effective-budget-v4 implementation: f32239e4d3c2c5a015044ad2e5f8522b093b45746056f0656437cc92b23955f2
- strict canonical implementation: cb0217d9143f41b288eccf396d6385e54c422ec88afa82de88fb52c6476bc412

## Safety

No market data, historical bars, runtime state, database, cache, network, service, browser, scheduler, or trading task is accessed. A synthetic candidate PASS is not profitability evidence, maturity, current activation, paper permission, live permission, or release authority. The single-look evidence chain and pointer-v2 remain unchanged.
