# ADR 0090: Long-horizon anchor-adapter registration v1

## Status

Accepted as an unmounted, research-only local declaration. It is not an externally time-attested registration and does not allow observation admission.

## Context

Observation protocol v1 freezes schemas, required binding fields, adapter interface, and fail-closed policies. A synthetic contract audit showed that it intentionally contains no selected adapter, provider, trust-root value, or registration state. Treating those field requirements as selected values would leave post-observation choice freedom.

## Decision

Add schema `strategy-correlation-cross-lag-factor-calibration-long-horizon-anchor-adapter-registration-candidate-v1` with fingerprint `20260918-cross-lag-factor-calibration-long-horizon-anchor-adapter-registration-1`.

The registration fully re-verifies observation protocol v1. It binds one adapter ID, adapter static fingerprint, adapter implementation SHA-256, provider ID, trust-root SHA-256, signature algorithm, receipt encoding, and local declaration timestamp. The timestamp claim must be no earlier than the source preregistration and strictly before the evaluation-not-before date.

Even a valid declaration has state `DECLARED_NOT_EXTERNALLY_TIME_ATTESTED`. It leaves adapter implementation verification, external registration timing, external authenticity, observation collection, evaluation, profitability, paper authority, and live authority false. A local timestamp and canonical hash cannot prove when the registration existed.

## Activation order

The consumer-first order is observation protocol -> adapter value declaration -> externally time-attested registration -> trusted adapter implementation verification -> externally attested observation batch -> tail gate. This ADR activates only the local value declaration.

## Consequences

Specific adapter/provider/trust-root choices become hash-bound before any downstream candidate can be admitted, while downstream consumers still must reject the declaration until independent external registration timing and implementation verification exist. No current pointer or natural-forward artifact changes.
