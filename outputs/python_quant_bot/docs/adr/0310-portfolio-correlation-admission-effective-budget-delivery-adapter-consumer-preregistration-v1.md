# ADR 0310: Portfolio Correlation Delivery Adapter Consumer Preregistration v1

Date: 2026-08-23

Status: Accepted as an isolated, host-unbound contract

## Context

ADR0309 registers exact Python and JavaScript delivery adapters, their load
order, the neutral presentation bridge contract, and an in-memory-only transport
boundary. It deliberately leaves every host binding null.

That registration does not identify the future consumers or freeze the order in
which their contracts must be implemented and reviewed. Without a separate
consumer-first contract, a future change could bind a route before the browser
consumer exists, load the JavaScript adapter without the strict canonical
dependency, or treat the Python and JavaScript halves as independently
activatable.

The missing boundary is therefore not another adapter registration. It is an
exact preregistration of the two consumers and their acceptance order.

## Synthetic gap proof

The gap is demonstrated without runtime, market, database, cache, network, or
browser access:

1. ADR0309 can verify exactly while no consumer identity is declared.
2. A proposed host can name the correct adapter registration hash while naming
   an incompatible JavaScript presentation contract.
3. A proposed route can be assigned before a Python hash-only source consumer or
   JavaScript verification consumer is implemented.
4. ADR0309 alone correctly blocks those actions, but it does not define the
   exact future consumer obligations that a later host-binding review must
   verify.

## Decision

Add schema
portfolio-correlation-admission-effective-budget-delivery-adapter-consumer-preregistration-v1.

The document preregisters exactly two ordered consumers:

1. A Python hash-only in-memory envelope source.
2. A JavaScript verifier, extractor, and unmounted neutral inspection bridge.

The Python consumer is pinned to the ADR0309 Python and transport subcontracts.
Its implementation module, provider, and host slot remain null. It may not
execute, register a route, or write.

The JavaScript consumer is pinned to the ADR0309 JavaScript, presentation, and
transport subcontracts. Its module, script, stylesheet, and mount slot remain
null. It may not execute in a browser, load runtime assets, or mount a DOM view.

ADR0310 pins the ADR0309 registration hash, direct asset manifest hash, source
file hashes, and seven subcontract hashes. It does not duplicate the complete
ADR0309 registration document.

## Consumer-first activation order

1. Verify the exact ADR0309 adapter registration.
2. Verify the exact ADR0310 consumer preregistration.
3. Implement the Python hash-only source in a separate version.
4. Validate the Python consumer using synthetic inputs.
5. Implement the JavaScript inspection consumer in a separate version.
6. Validate the JavaScript consumer using synthetic envelopes.
7. Declare host bindings in a separate version.
8. Run an explicitly authorized browser review before any mount.
9. Consider current activation only through a separate explicit decision.

The order is data in the sealed contract. Reordering and fully resealing the
document is rejected by the exact verifier.

## Exact predecessor pins

- ADR0309 registration hash:
  4c6eb60d842611d2babaf072527fe93d2a68f67bc6a7c2658b80fd1b9f07f4cb
- ADR0309 direct asset manifest hash:
  d5d4e3c829f99ba840cc945d11a8c8cec90386baa1ea2e7a0f6333e8d6d6c058
- Python contract hash:
  484dc34f1736c8f0cbb08f7a6d560b65af064400fe53831bf5215541d669df6f
- JavaScript contract hash:
  3831fc0e8c9610536d3420226ac0c80d501dddb367633c11de954e724fb8816e
- Presentation contract hash:
  d8c0462d451543b58ea8d25c2454347dd9129266020f371e47e9cc2d57a2e632
- Transport contract hash:
  5c5b7a00984408d3ce03e6f23a3a33e339fbdc457b77fc59cc317acd4f341b62
- Authority hash:
  c934ee41b56e2b1b53c4aacbe4f6a57749d195df4ba73a0fd4d7c43593847a80
- Activation-order hash:
  1ecc3a80c36f740853fa4120d490e56b6001dc97d10d11472590ba3bdd62caa9
- Host-plan hash:
  3f32db5e9329a64752580f3dd3a6c0c084ca0d6870ca9fcac27e165e8689a690

## Fail-closed behavior

The verifier accepts only the exact canonical document. It rejects malformed,
non-native, cyclic, extra-field, reordered, rebound, permission-promoted, and
fully resealed drift.

The builder also verifies ADR0309 and all pinned subcontract hashes before
constructing ADR0310. An exact-hash predecessor mutation therefore fails before
a preregistration can be produced.

## Consequences

The future host-binding review now has exact consumer identities, required
contracts, and an enforceable order. ADR0309 remains the adapter and asset
registration authority; ADR0310 adds consumer obligations rather than
duplicating that boundary.

This decision creates no route, endpoint, provider, host import, script tag,
stylesheet link, browser execution, DOM mount, runtime mutation, scheduler,
current activation, paper authority, live authority, or writer capability.

The public natural-forward chain remains:

audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 ->
snapshot-v4/summary-v2

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 remains unchanged
and is not automatically reissued. Synthetic contract evidence is not
profitability evidence and grants no trading permission.
