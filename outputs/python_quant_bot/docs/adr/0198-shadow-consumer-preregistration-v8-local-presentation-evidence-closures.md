# ADR 0198: Shadow consumer preregistration v8 local presentation evidence closures

## Status

Accepted as an evidence-aware, detached preregistration. Public status remains
`BLOCKED`; no consumer, mount, current, paper, or live authority is granted.

## Context

V7 pinned the unmounted fixture and registration candidate but correctly left
two evidence blockers open. ADR0196 bound deterministic local fixture execution
evidence. ADR0197 then bound that execution lineage to the exact registration
candidate while preserving both source documents as blocked and inactive.

A preregistration successor is needed to consume the exact ADR0197 evidence,
close only those two local blockers, and expose the next real gates without
rewriting v7 or treating evidence binding as registration activation.

## Decision

Add `strategy_correlation_cluster_portfolio_risk_shadow_consumer_preregistration_v8.py`.
V8:

- public-reverifies immutable v7 and ADR0197 against the same canonical v7
  document;
- layers exactly three new implementation pins over v7's 36 pins: v7 itself,
  ADR0196, and ADR0197, for a total of 39;
- consumes the ADR0197 binding hash as evidence and closes exactly
  `presentation_consumer_fixture_v3_execution_evidence_not_bound` and
  `presentation_consumer_registration_candidate_v1_evidence_not_bound`;
- preserves all 14 shadow input schemas and the three predecessor local
  closures, then appends the two verified evidence closures;
- replaces the closed evidence blockers with explicit independent descriptor
  review and registration activation gates;
- removes only completed local evidence steps from the remaining activation
  order;
- embeds no v7, ADR0196, ADR0197, registration, receipt, descriptor, projection,
  or markup instance.

`contract_state=KNOWN` means the preregistration was exactly rebuilt with the
two local evidence closures. Its public `status` is still always `BLOCKED`.
Registration activation, independent review, DOM/browser review, presentation
HTTP versioning, mount, current, authenticated external authority,
profitability, paper trading, and live trading remain absent or unauthorized.

## Adversarial matrix

Tests reject missing, extra, drifted, or scalar implementation manifests;
verification-context aliases; v7 verifier failure or status promotion; ADR0197
verifier failure; canonical-v7 cross-splice; ADR0196 implementation splice;
false evidence facts; registration activation leakage; authority leakage;
source mutation; and document tampering. A real integration case builds v7,
ADR0196, ADR0197, and v8 entirely from synthetic in-memory contracts.

## Consequences

V8 advances local maturity without advancing permission. The next useful work
is independent render-descriptor review evidence and a separately versioned
presentation HTTP contract. DOM/browser, mount, registration activation, and
current remain later, separately authorized steps.
