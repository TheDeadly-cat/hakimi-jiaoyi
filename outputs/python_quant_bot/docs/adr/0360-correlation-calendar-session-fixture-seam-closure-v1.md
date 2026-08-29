# ADR 0360: Correlation calendar-session fixture seam closure v1

## Status

Accepted for synthetic, unmounted, research-only conformance evidence.

## Context

ADR 0359 removed the redundant correlation-replay verifier mock from the real tree 3 -> 4 -> 5 synthetic checkpoint-history fixture. Two upstream fixture seams remained: calendar-session verification and provider-identity assertion verification.

The calendar seam was not a hash-only drift. The legacy composition fixture supplied a positive calendar document but only a reduced registration assignment and empty registration, batch-verification, and verification-context objects. The original calendar verifier therefore returned `UNKNOWN` with `SOURCE_CALENDAR_REGISTRATION_HASH_MISMATCH`.

The legacy second window also used a 365-day offset. On 2026-08-24 the default `exchange_calendars` 24/7 instance ended at 2027-08-24, while that second 80-day window ended on 2027-12-19. The original verifier correctly returned `CALENDAR_SESSION_LOOKUP_FAILED`. Moving the window backward violated the preregistered observation chronology, and a zero offset violated the no-overlap gate.

## Decision

Add a test-only source-assembly adapter in `test_strategy_correlation_persisted_checkpoint_history_coverage_calendar_session_seam_closure_v1.py`.

The adapter:

1. Changes the second synthetic window offset from 365 days to the minimum complete non-overlap offset of 80 days.
2. Rebuilds the shifted observation batch with the existing ADR 0095 fixture builders.
3. Reissues the signed time-anchor receipt at one second after the final 24/7 session completes.
4. Rebuilds batch verification, calendar registration, calendar verification context, and the complete calendar verification bundle.
5. Requires the original calendar-session verifier to accept every rebuilt document and bundle.
6. Rebuilds the calendar/provider composition and the provider dataset registration, signed attestation receipt, and verification document against the new composition hash.
7. Removes the persistent calendar-session verifier patch before tree 3 evaluation and before tree 4 and tree 5 are built.

The adapter temporarily allows the legacy combined provider-window helper to create a scaffold. That scaffold is not evidence authority: the calendar document, complete source bundle, composition, registration, attestation, and verification are replaced and rebuilt; every retained calendar document is then reverified by the original verifier. The temporary scaffold patch is not active in the delivered fixture material.

After ADR 0360, exactly one persistent upstream fixture seam remains: provider-identity assertion verification.

## Consumer-first activation order

1. Calendar-session original-verifier conformance inside the source fixture.
2. Calendar/provider composition rebuilt against the conformed calendar source.
3. Provider dataset registration and signed attestation rebuilt against the new composition.
4. Tree 3 lineage gate evaluation.
5. Tree 4 and tree 5 lineage generation and evaluation.
6. Bounded persisted-checkpoint history coverage evaluation.

No `current` pointer, scheduled evidence, dashboard, pack, snapshot, or summary consumer changes.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Complete offset-0 calendar bundle | Original verifier accepts |
| Complete offset-80 calendar bundle | Original verifier accepts |
| Empty calendar registration source | Original verifier rejects |
| Resealed `paper_authorized=true` calendar document | Original verifier rejects |
| Missing middle persisted-checkpoint segment | Coverage is `UNKNOWN` and locked |
| Tree 3 -> 4 -> 5 complete bounded lineage | Gates and coverage pass, authority remains locked |

## Evidence boundaries

- Pure synthetic and in-memory only.
- No historical market data, K-line task, G50/G51 task, blind test, service, browser, scheduler, publication, paper trading, or live trading.
- No profitability evidence or profitability claim.
- No complete-history, external calendar-authority, external provider-authority, durable-registry, paper, or live authority.
- Natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
- Legacy pack-v5 public reads and pointer-v2 behavior are unchanged.
- UI and protected frontend assets are unchanged.

## Implementation fingerprints at design time

- Calendar-session verifier: `d769d2f7b18cb20e6563a244cf423471776c09b86b3573d5b7d7ba593c0a5be3`
- Calendar/provider composition: `922e626c72c3eb6be64a7a7d07ea0339655318eacac44a5121370cf8e11b1197`
- Provider dataset attestation: `91dcad9660f379c47c2e912bda5032cbabc72dc5af8c42ece2ea3bede19bc654`
- ADR 0358 real-tree fixture: `95b15b3b9f10aa34d6a77fd56f8f7cfa6d5119f5d7eb78f675fe4a15d75f3daf`
- ADR 0359 correlation seam-closure fixture: `d4826f3943b3020751e6b6fe4e3259d4986ef466e6892dc5686913b8cc3ad5fb`

## Consequences

The bounded history fixture no longer treats a positive but unverifiable calendar document as source authority. Calendar evidence is now complete enough for the original verifier, date windows remain preregistered and non-overlapping, and every dependent hash and signature is rebuilt. Provider identity remains deliberately unresolved and is the next source-fixture seam. This ADR does not activate any runtime or trading capability.
