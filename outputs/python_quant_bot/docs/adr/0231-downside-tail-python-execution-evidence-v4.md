# ADR 0231: Downside-tail Python execution evidence v4

- Status: Accepted
- Date: 2026-08-23
- Scope: research-only, synthetic contract evidence

## Context

The unmounted downside-tail consumer has a local Node execution receipt-v4 and
an execution preregistration-v1. The previous Python evidence-v3 is bound to the
older joint-evidence consumer, projection-v5, receipt-v3, and formal
registration-v4. Reusing it would create two compatibility errors: it would
collapse exact source UNKNOWN into a two-state local gate, and it would imply a
formal registration edge that receipt-v4 explicitly does not have.

Receipt-v4 PASS means only that the local Node contract process produced the
expected unmounted consumer receipt. It does not mean the local strategy state
is PASS. Clear, downside-tail block, and exact source UNKNOWN must remain three
distinct semantic outcomes inside otherwise valid execution evidence.

## Decision

Add a versioned Python execution evidence-v4 with four explicit inputs:

1. receipt-v4;
2. receipt-v4 sealed verification;
3. projection-v6;
4. execution preregistration-v1.

The builder does not execute Node. It independently rebuilds the execution
preregistration and receipt verification, verifies strict canonical seals,
checks exact implementation pins, and cross-binds receipt, projection, and
preregistration hashes. Projection lineage is checked as a sealed, versioned,
summary-only hash shape; lineage source documents are not replayed or embedded.

The accepted semantic tuples are intentionally narrow:

| Evidence semantic state | Local status | Downside-tail decision | Source |
| --- | --- | --- | --- |
| `CLEAR` | `PASS` | `PASS` | `OBSERVED` |
| `TAIL_BLOCK` | `BLOCK` | `BLOCK` | `OBSERVED` |
| `EXACT_UNKNOWN` | `UNKNOWN` | `UNKNOWN` | `UNKNOWN` |

Evidence status PASS means that one of those tuples was preserved exactly. It
does not promote `TAIL_BLOCK` or `EXACT_UNKNOWN`, authenticate the Node process,
prove profitability, mount a consumer, or grant paper/live authority.

Formal registration remains explicitly absent at every edge:

- receipt source registration schema and hash are null;
- preregistration disallows formal registration;
- receipt facts and verification report no formal registration binding;
- evidence authority cannot activate registration, current, runtime, paper, or
  live paths.

## Consumer-first activation order

1. Keep projection-v6, card-v6, consumer-v6, preregistration-v1, receipt-v4, and
   evidence-v4 unmounted and synthetic.
2. Validate exact and adversarial contracts for clear, tail block, and source
   UNKNOWN.
3. Design a separate formal registration-v7 that binds evidence-v4 and its
   implementation fingerprint.
4. Only after an independently reviewed registration contract may a separate
   activation decision be proposed. No current pointer or route changes are
   part of this ADR.

## Adversarial contract matrix

The targeted contract covers:

- receipt, projection, preregistration, and verification hash substitution;
- resealed authority promotion;
- dependency pin replacement and extra source fields;
- formal registration insertion;
- legacy receipt schema aliasing;
- clear/tail-block/UNKNOWN semantic aliasing;
- evidence resealing after authority mutation;
- summary-only and non-authority assertions.

## Consequences

- The Python evidence layer now matches receipt-v4 without inventing a formal
  registration boundary.
- Exact UNKNOWN remains observable and fail-closed rather than being counted as
  a strategy PASS or an execution failure.
- The evidence is stronger against compatible-looking resealed documents, but
  remains local descriptive evidence with unauthenticated process identity.
- The natural-forward current chain, pointer-v2, paper/live locks, routes, and
  mounted UI remain unchanged.
