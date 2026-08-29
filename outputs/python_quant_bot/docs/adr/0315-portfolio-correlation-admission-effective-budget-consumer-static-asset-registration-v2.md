# ADR 0315: Portfolio Correlation Admission Effective-Budget Consumer Static-Asset Registration v2

- Status: Accepted as an unbound registration contract
- Date: 2026-08-24
- Scope: Synthetic, deterministic, read-only registration evidence

## Context

ADR0314 preregistered the Python provider, read-only HTTP projection, five
JavaScript assets, isolated stylesheet, and mount slot as binding candidates.
Every active host slot remained null.  Its next explicit step was a separate
version of the static-asset registration that includes the ADR0312 inspection
consumer and ADR0313 cross-runtime parity acceptance consumer.

ADR0308 remains a valid public v1 registration.  Rewriting it would blur the
compatibility boundary and could make a delta consumer appear active.  Loading
only the two new scripts would be incomplete because they depend on the exact
canonical, delivery, and bridge scripts already registered by ADR0308.

## Decision

Add a new wrapper over `static-presentation-asset-registration-v1` with:

- registration ID `portfolio-correlation-admission-effective-budget-consumer-assets-v2`;
- exact verification of ADR0308 registration hash
  `265a897bb11a9d2df873f23a3faf5dc21bc4f66bb93ef8d313994e35938d04c4`;
- exact verification of ADR0314 preregistration hash
  `132eb51549337575ebb1ff80c870e7eb51d66a63b52f73930634e9e0467e9e6b`;
- ADR0314 as the pinned source contract;
- all 10 ADR0308 assets preserved byte-for-byte;
- 10 additive ADR0312/ADR0313 implementation, test, fixture, and decision assets;
- a five-script dependency order matching ADR0314 exactly;
- the existing isolated bridge stylesheet;
- every host-plan field null and every authority field false.

The resulting deterministic contract is:

- `spec_hash=bb14803ac0b8ff6aba6d5a9aed3ee3368339a1abf73e84457fa5a2613319aa6d`
- `asset_manifest_hash=21a70bdf26842d15fc6e6d0067c3beb7b5b28545546e4bf71fa171631d1a02bf`
- `registration_hash=098a8952afbf3459cdcd046b1695bb296a32bdbe44f54d061300ba128c2b2cc0`
- `status=BLOCKED`
- `registration_state=STATIC_PRESENTATION_ASSETS_REGISTERED_UNBOUND`

## Consumer-first activation order

1. Verify the exact ADR0308 v1 registration.
2. Verify the exact ADR0314 host-binding preregistration.
3. Verify the ADR0315 v2 registration and all pinned source bytes.
4. Implement a Python provider binding in a separate version.
5. Implement a read-only HTTP projection in a separate version.
6. Implement application import and host asset loading in a separate version.
7. Run an explicitly authorized browser review before any route or mount.
8. Consider current activation only through a separate explicit decision.

The registered script order is:

1. `strict_canonical_json_v1.js`
2. `evidence_portfolio_correlation_admission_effective_budget_in_memory_delivery_v1.js`
3. `evidence_portfolio_correlation_admission_effective_budget_bridge_v1.js`
4. `evidence_portfolio_correlation_admission_effective_budget_inspection_consumer_v1.js`
5. `evidence_portfolio_correlation_admission_effective_budget_cross_runtime_consumer_parity_acceptance_v1.js`

## Adversarial matrix

| Mutation | Required result |
| --- | --- |
| ADR0308 registration drift | Reject |
| ADR0314 preregistration drift | Reject |
| Source-contract hash drift | Reject |
| Registered asset removal or hash drift | Reject |
| Five-script load-order drift | Reject |
| Browser-global substitution | Reject |
| Host script, route, stylesheet, or mount binding | Reject |
| Any authority escalation | Reject |
| Unknown top-level field | Reject |

## Non-authority

This registration does not import an application module, expose an HTTP route,
load a browser asset, bind a stylesheet, mount DOM, mutate runtime state, or
change any current pointer.  It does not alter the natural-forward evidence
chain, promote legacy pack-v5 reads, or reissue pointer-v2.  It is not evidence
of profitability and grants no paper, live, writer, route, browser, or trading
authority.
