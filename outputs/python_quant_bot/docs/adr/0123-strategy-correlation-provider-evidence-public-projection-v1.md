# ADR 0123: Strategy correlation provider evidence public projection v1

## Status

Accepted as an inactive, consumer-first, research-only projection. It does not
register a current consumer, alter a writer, mutate a pointer, or authorize
paper or live execution.

Static fingerprint:
`20260822-strategy-correlation-provider-evidence-public-projection-1`.

## Gap demonstrated

The provider dataset key lifecycle replay gate from ADR 0122 had no consumer in
the application, domain, infrastructure, interfaces, or service paths. Its only
references were its implementation and targeted test. Creating another strata
registry or report consumer would duplicate the existing report18/protocol-v7
boundary, so the missing slice is a narrow projection consumer.

## Decision

Add
`strategy-correlation-provider-evidence-public-projection-v1` as a redacted
composition of two already versioned verifier boundaries:

1. The strata protocol migration public summary verifier.
2. The provider dataset key lifecycle replay gate verifier.

The projection accepts source documents and caller-supplied verification
contexts. Contexts are forwarded only to their verifier and are never copied to
the output. Non-dict inputs, non-dict contexts, verifier exceptions, malformed
verification results, and any result other than `PASS` produce `UNKNOWN`.

## Semantic calibration

Verifier `PASS` proves only that an upstream document satisfies its verifier.
It does not prove that the provider gate outcome passed. Therefore the
projection always keeps maturity `UNKNOWN`, sets
`semantic_gate_outcome_projected=false`, and leaves the provider gate outcome
as `NOT_PROJECTED`.

The projection never claims:

- global dataset-key uniqueness;
- absence of future replay;
- durable external publication;
- external registry or auditor authority;
- natural-forward maturity;
- profitability;
- paper or live authorization.

## Redaction

The public document exposes no symbol identities, provider identities, dataset
identities, key identifiers, signatures, Merkle paths, source documents, or
verification-context values. It reports only verifier state and fixed gap,
maturity, activation, claim, redaction, and permission fields.

## Consumer-first activation order

1. Keep all existing protocol, report, pack, evidence, snapshot, summary, and
   pointer readers unchanged.
2. Land this projection and its exact-rebuild verifier as an inactive candidate.
3. Exercise only pure synthetic source documents and patched verifier outcomes.
4. Add a versioned application route only after an independent redaction and
   compatibility review.
5. Observe the candidate without adding a current reference.
6. Review any current migration separately and explicitly. No successful test
   or observation may trigger automatic activation.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Protocol verifier blocks | Projection source is `UNKNOWN` |
| Replay verifier blocks | Projection source is `UNKNOWN` |
| Either verifier raises | Projection source is `UNKNOWN` |
| Verification context is not a plain dict | Verifier is not called; projection is `UNKNOWN` |
| Source contains provider, key, signature, or Merkle material | Material is absent from output |
| Context contains trust material | Material is forwarded but absent from output |
| Upstream documents are valid | Inputs remain unmodified |
| Projection permission is tampered | Exact-rebuild verification blocks |
| Exact `UNKNOWN` projection is rebuilt | Document verification may pass while source verification remains false |
| Both verifiers pass | Source integrity is observed; gate outcome and maturity remain unprojected |

## Compatibility and authority boundary

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`. Pointer-v2 fields and hash
semantics remain unchanged, and no automatic reissue is introduced.

This ADR changes no paper or live authorization and provides no profitability
evidence.
