# ADR 0095: Long-horizon calendar-session verifier v1

## Status

Accepted as an unmounted, research-only candidate verifier. It does not admit observations, activate evaluation, or change current evidence consumers.

## Context

Calendar registration v1 freezes positional identity and factor calendar assignments, but the existing observation-batch verifier does not consume them. The consecutive 80-row synthetic fixture has 24 invalid `XNYS` session labels, including 23 weekend dates and one exchange holiday, while all 80 labels are valid under `24/7`. Therefore neither a global weekend ban nor the existing structural batch check is sufficient.

## Decision

Add schema `strategy-correlation-cross-lag-factor-calibration-long-horizon-calendar-session-verifier-candidate-v1`. The current unmounted implementation revision fingerprint is `20260922-cross-lag-factor-calibration-long-horizon-calendar-session-verifier-2`; revision 1 was superseded before activation when upstream calendar IDs became canonical-only.

The verifier independently rebuilds the canonical-only calendar registration and batch verification, cross-binds their schedule, identity, factor, batch, and provider timestamp evidence, then requires every observation label to be a session in every distinct registered identity and factor calendar. Each session close must be no later than the signed provider UTC timestamp. Alias-equivalent IDs cannot inflate distinct-calendar or session-check counts. The public document exposes only hashes and aggregate counts, never row returns, observation IDs, session labels, or close times.

The highest state is `CALENDAR_SESSIONS_VERIFIED_BATCH_NOT_ADMITTED`. Provider identity, external registration time, replay registry, long-horizon activation, observation admission, profitability, paper, and live authority remain false.

## Consequences

Pure-synthetic contracts can now distinguish a valid 24/7 sequence, a valid 80-session exchange sequence, an invalid exchange weekend or holiday, a mixed-calendar intersection failure, and a session that has not closed at the signed provider timestamp. The verifier remains detached until a later consumer-first activation decision; the current natural-forward chain and existing synthetic batch are unchanged.
