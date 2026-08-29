# ADR 0093: Long-horizon observation-batch verifier v1

## Status

Accepted as an unmounted, pure-synthetic-capable content verifier. It does not admit observations or evaluate strategy performance.

## Context

The fixed fold schedule pins the first 80 common-date positions, while the detached signature receipt binds an observation-batch hash. A batch can include the schedule hash inside its canonical payload, producing a transitive schedule -> batch -> signed receipt cross-binding without changing the frozen receipt schema.

## Decision

Add schema `strategy-correlation-cross-lag-factor-calibration-long-horizon-observation-batch-verification-candidate-v1` with fingerprint `20260921-cross-lag-factor-calibration-long-horizon-observation-batch-verifier-1`.

The private batch contains exactly 80 rows with global position, fold ID, fold position, unique observation ID, strictly increasing date, factor return, and an exact registered-identity return map. The verifier fully re-verifies the schedule and signature artifacts, exact source contexts, batch seal, signed hash, schedule hash, identity/factor hashes, four 20-row fold assignments, date window, finite numeric values, and receipt date range.

The public verification output redacts rows, returns, observation IDs, public key, and signature bytes. It exposes only hashes, counts, dates, factor/identity bindings, provider label, and support facts.

The highest positive state is `BATCH_CONTENT_VERIFIED_SIGNATURE_LIMITED`. Provider identity, external registration timing, replay uniqueness, external authenticity, observation admission, evaluation, result, profitability, paper authority, and live authority remain false.

## Consequences

Batch content and fold assignment can no longer drift independently from the signed hash or preregistered schedule. A later provenance/time/replay join is still required before observation admission, followed by the preregistered residual-order tail evaluation. The current natural-forward chain remains unchanged.
