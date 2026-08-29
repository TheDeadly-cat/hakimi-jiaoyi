# ADR 0089: Long-horizon external-observation protocol v1

## Status

Accepted as an unmounted, research-only protocol declaration. No observation batch, external attestation, evaluation result, or authority is activated.

## Context

The long-horizon preregistration supplement pins the future lag, support, tail-score, timing, and external-anchor reference hash. It does not pin the future observation-batch schema, trusted adapter interface, trust-root binding, provider receipt fields, or the rules that distinguish an externally verified timestamp from a caller-generated hash.

Pure-synthetic replay demonstrates the gap without using runtime data: the historical calibration replay can report `OBSERVED/MATCH` for a structurally valid caller-sealed batch while still declaring `external_calibration_timing_attested=false`. The local forward-source anchor cannot close this gap because its contract permanently states `external_authenticity_proven=false`.

## Decision

Add schema `strategy-correlation-cross-lag-factor-calibration-long-horizon-observation-protocol-candidate-v1` with fingerprint `20260917-cross-lag-factor-calibration-long-horizon-observation-protocol-1`.

The protocol fully re-verifies the long-horizon preregistration and its exact source context. It pins the future observation-batch schema, external-attestation schema, append-only verification adapter interface, trust-root and provider bindings, and five time rules. Missing external attestation and unsupported adapters remain `UNKNOWN`; caller clocks and self-attested anchors are `BLOCK`.

The only positive state in this version is `PROTOCOL_DECLARED_NO_OBSERVATIONS`. The document contains no rows, returns, attestation, result, profitability field, or execution authority. Hash equality is a binding fact only and never proves external authenticity.

## Activation order

The consumer-first order is long-horizon preregistration -> observation protocol -> trusted external adapter -> externally attested observation batch -> tail gate -> precommit join -> report consumer -> presentation -> detached UI. This ADR activates only the observation protocol.

## Consequences

Future observation code has a versioned contract and cannot choose an adapter, trust root, timestamp rule, or support threshold after seeing results. No current pointer, natural-forward artifact, paper permission, live permission, or profitability claim changes.
