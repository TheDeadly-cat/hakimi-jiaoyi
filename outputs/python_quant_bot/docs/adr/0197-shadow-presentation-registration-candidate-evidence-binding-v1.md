# ADR 0197: Shadow presentation registration candidate evidence binding v1

## Status

Accepted as detached, local-only successor evidence. It does not activate a
registration, mount a consumer, switch current, or grant paper/live authority.

## Context

ADR0196 exactly binds local Node fixture execution evidence to the immutable v7
shadow preregistration. ADR0193 provides a static, unmounted registration
candidate whose document and implementation are pinned by v7. The two chains
previously remained separate, leaving the v7 blocker
`presentation_consumer_registration_candidate_v1_evidence_not_bound` open.

## Decision

Add
`strategy_correlation_cluster_portfolio_risk_shadow_presentation_registration_evidence_binding_v1.py`.
It:

- exactly re-verifies ADR0196 and the ADR0193 registration candidate through
  their public verifiers;
- freezes the ADR0196 and ADR0193 implementation hashes;
- binds the ADR0193 registration hash and implementation hash to v7;
- cross-binds fixture, projection, card JavaScript, and card stylesheet pins;
- proves that ADR0196 consumed the same canonical v7 document;
- requires v7 and ADR0193 to remain `BLOCKED`, with registration inactive and
  all source authority locked;
- emits hashes and boolean conclusions only, never source documents, fixture
  evidence, descriptors, or markup.

A binding `PASS` closes only the local registration-candidate evidence gap in a
successor document. The immutable registration candidate still says
`CANDIDATE_ONLY` and remains inactive. Independent descriptor review, DOM
contract review, browser visual review, presentation HTTP versioning, mount,
current, authenticated process identity, receipt signature, profitability,
paper trading, and live trading remain unproven or unauthorized.

## Consumer-first order

1. Verify v7, ADR0196, and ADR0193 independently.
2. Build this detached exact cross-binding.
3. Preserve both source documents unchanged and blocked.
4. Obtain independent descriptor review evidence.
5. Version the presentation HTTP contract before any mount consideration.
6. Authorize DOM/browser work only through a separate task.
7. Consider registration activation, mount, and current only as separate final
   permissions.

## Adversarial matrix

Tests reject context aliases, implementation-manifest drift, registration hash
cross-splice, registration implementation drift, each presentation-pin
mismatch, v7 document cross-splice, absent fixture execution evidence, source
status promotion, registration activation leakage, authority leakage, upstream
verifier failure, raw source output, and exact-document tampering. A non-mocked
integration case consumes the real frozen v7, ADR0196, and ADR0193 contracts.

## Consequences

The local registration candidate can now be evidence-bound without being
activated. A later preregistration successor may reference this contract, but
must remain fail-closed on every external, review, HTTP, DOM/browser, runtime,
mount, current, and trading gate.
