# ADR 0124: Strategy correlation provider evidence presentation envelope v1

## Status

Accepted as an unmounted, application-only, research presentation candidate.
No HTTP route, server registration, current reference, writer, scheduler, paper
authorization, or live authorization is added.

Static fingerprint:
`20260822-strategy-correlation-provider-evidence-presentation-envelope-1`.

## Gap

ADR 0123 introduced the first redacted consumer of the provider lifecycle
replay evidence, but the application layer had no versioned presentation use
case for that projection. Existing application envelopes establish the required
pattern: sealed output, deterministic exact rebuild, four ordered evidence axes,
unknown fallback, and an explicit unmounted status.

## Decision

Add
`strategy-correlation-provider-evidence-presentation-envelope-v1` under the
application layer. It calls the ADR 0123 builder and verifier, performs a second
semantic authority audit, and emits a sealed presentation envelope with axis
order `SOURCE -> GAP -> MATURITY -> PERMISSION`.

The envelope never embeds source documents or verification contexts. It records
only the registered source projection schema and static fingerprint.

## Positive display calibration

The positive display state is
`SOURCE_CONTRACTS_VERIFIED_GATE_OUTCOME_UNPROJECTED`. It means both source
documents passed their registered verifiers. It does not mean the provider gate
passed.

Even in this state:

- provider gate outcome is absent;
- maturity is `UNKNOWN`;
- natural-forward maturity and market outcomes are unproven;
- current consumer binding and pointer writes are absent;
- profitability is unproven;
- paper and live remain unauthorized.

Any malformed source, non-dict context, verifier exception, verification block,
schema drift, fingerprint drift, source authority promotion, projected gate
outcome, maturity promotion, or redaction drift produces a sealed `UNKNOWN`
envelope.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Both registered source verifiers pass | Source is observed; gap remains blocked; maturity remains unknown |
| Either source verifier blocks | Sealed `UNKNOWN` envelope |
| Source verifier raises | Sealed `UNKNOWN` envelope |
| Projection exact-rebuild verifier blocks | Sealed `UNKNOWN` envelope |
| Projection permission is promoted despite a forged pass result | Sealed `UNKNOWN` envelope |
| Source documents or contexts contain private markers | Markers are absent from the envelope |
| Context is not a plain dict | Sealed `UNKNOWN` envelope |
| Envelope is rebuilt with identical inputs | Byte-equivalent canonical document |
| Envelope authority is tampered | Envelope verifier returns false |

## Activation order

1. Keep this module unmounted and exercise only synthetic application contracts.
2. Review redaction, strict equality, deterministic sealing, and import behavior.
3. Add an interface adapter only as a new versioned candidate contract.
4. Keep `server.py`, `services/http_contract.py`, current readers, and all
   natural-forward readers unchanged.
5. Review any HTTP mount or current migration separately and explicitly. No test
   result may trigger automatic activation.

## Compatibility and authority boundary

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`. Pointer-v2 fields and hashes remain
unchanged, with no automatic reissue.

This envelope is not browser or runtime evidence, profitability evidence, or
trading authorization.
