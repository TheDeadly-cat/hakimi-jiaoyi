# ADR 0196: Shadow presentation local execution evidence binding v1

## Status

Accepted as a detached, local-only, fail-closed research contract. It is not a
current consumer activation and grants no paper or live authority.

## Context

ADR0194 preregistration v7 freezes the presentation fixture and registration
candidate pins while remaining `BLOCKED`. ADR0195 adds deterministic local Node
execution evidence for the unmounted fixture, but the two documents previously
had no narrow cross-binding contract. A consumer could therefore present a
valid v7 preregistration beside valid execution evidence from a different
fixture, projection, or card lineage.

## Decision

Add
`strategy_correlation_cluster_portfolio_risk_shadow_presentation_execution_evidence_binding_v1.py`.
The binding:

- calls the public exact verifiers for preregistration v7 and ADR0195 evidence;
- requires exact verification-context key sets with no compatibility aliases;
- pins the three implementation hashes for v7, the Node receipt builder, and
  the Python evidence envelope;
- binds fixture, projection, and card implementation identities across both
  source documents;
- binds the evidence projection-document hash to the explicit verification
  context;
- requires preregistration v7 to remain `BLOCKED` and both source authority
  maps to remain false;
- emits hashes and boolean conclusions only, never raw preregistration,
  receipt, descriptor, or rendered markup.

The exact upstream normalization is intentionally narrow. Public verifier
receipts must expose a true role-specific `*_exactly_verified` marker and an
empty blocker list. Authority maps may contain the sole descriptive capability
`descriptive_only: true`; every permission-bearing field must remain false.
The Node `receipt_hash` and descriptor hash are each cross-bound to the ADR0195
evidence source, rather than merely checked for hash-shaped syntax.
Projection lineage consumes the exact ADR0195 `source.projection_hash` field;
invented compatibility aliases are rejected rather than normalized.

`PASS` means only that the deterministic local fixture execution evidence is
bound to the frozen shadow lineage. It does not prove or activate presentation
consumer registration. Process identity, receipt signature, independent
review, DOM execution, browser execution, runtime mutation, profitability,
paper trading, and live trading all remain unproven or unauthorized.

## Consumer-first activation order

1. Freeze and verify v7 and ADR0195 independently.
2. Build this detached local binding and retain v7 `BLOCKED`.
3. Add a separate exact registration-execution evidence contract.
4. Add authenticated process identity and signed receipt verification.
5. Obtain independent review evidence.
6. Add DOM/browser evidence only through a separately authorized task.
7. Consider any current switch only after all remaining closures are explicit.

## Adversarial matrix

The targeted tests reject missing, extra, drifted, and non-string
implementation manifests; missing or extra verification contexts; projection
cross-splicing; each of the three implementation-pin mismatches; conflicting
summary aliases; upstream verifier failure or exception; source-status
promotion; non-boolean or true authority; binding tampering; raw evidence
leakage; and input mutation.

## Consequences

The first v7 presentation-fixture execution gap is closed locally without
claiming that preregistration is mature. The next narrow gap is registration
candidate execution evidence. The natural-forward artifact chain and all
pointer contracts are unchanged.
