# ADR 0207: Weighted diversification presentation registration v2

Date: 2026-08-23

Status: accepted for a static blocked registration candidate only

## Context

ADR 0206 completed an unmounted projection-v4 to card-v4 to consumer-v4
render-descriptor path with cross-runtime seal verification. No service-layer
registration referenced the new consumer. The immutable registration-v1
contract remains pinned to projection-v3, card-v3, and consumer-v3; injecting a
v4 artifact into its manifest correctly fails closed.

The next consumer-first step is an independent static registration candidate.
It must bind exact artifact identities and loading order without reading files,
executing the fixture, registering a route, touching the DOM, or granting
activation.

## Decision

Add
`strategy_correlation_cluster_portfolio_risk_presentation_consumer_registration_v2.py`
as a standalone successor. It does not modify registration-v1 and pins ten
artifacts supplied through one exact manifest:

- one immutable predecessor: registration-v1;
- five production artifacts: projection-v4, strict canonical SHA dependency,
  card-v4 JavaScript, card-v4 CSS, and consumer-v4 JavaScript;
- four verification artifacts: projection-v4 test, card-v4 Node test,
  consumer-v4 Node test, and Python-to-Node cross-runtime test.

The candidate declares the browser dependency order as strict SHA dependency,
card, then consumer. It records that the SHA dependency supplies only the
UTF-8/SHA256 primitive while card-v4 supplies the projection-specific
Python-compatible floating-point encoding.

The service never reads those paths. A caller-provided manifest matching the
hardcoded contract proves only exact local agreement. It is not external
artifact attestation. The output therefore remains `BLOCKED/CANDIDATE_ONLY`,
keeps all authority false, and records both `artifact_files_read: false` and
`implementation_manifest_externally_attested: false`.

## Activation order

1. Bind and exactly verify projection-v4 evidence.
2. Version and execute a synthetic fixture-v4 execution receipt.
3. Independently bind the execution evidence.
4. Independently review the render descriptor and dependency load order.
5. Separately authorize an isolated DOM contract review.
6. Separately authorize browser visual review.
7. Version an HTTP contract while transport remains unregistered.
8. Separately authorize consumer registration.
9. Separately authorize presentation mount.
10. Separately authorize any `current` switch.

This ADR completes only the static candidate portion before step 1. It does not
perform any activation-order step.

## Adversarial matrix

- every individual artifact hash drift fails closed;
- missing, extra, scalar, and bool-alias manifests fail closed;
- predecessor, schema, fingerprint, dependency-order, seal, mount, and
  permission policies are exact;
- a resealed authority tamper fails exact rebuild verification;
- an exactly rebuilt invalid-manifest document does not claim manifest
  verification;
- output embeds no supplied manifest, projection, descriptor, markup, browser
  result, DOM instance, or runtime handle;
- build and verification remain deterministic and summary-only.

## Non-claims

This candidate is not execution evidence, external artifact attestation,
independent review, DOM evidence, browser visual QA, HTTP registration, runtime
activation, natural-forward maturity, profitability evidence, paper/live
authorization, or permission to trade. The established natural-forward chain,
legacy pack-v5 behavior, and pointer-v2 contract remain unchanged.
