# ADR 0361: Correlation provider-identity fixture seam closure v1

## Status

Accepted for synthetic, unmounted, research-only conformance evidence.

## Context

ADR 0360 closed the correlation-replay and calendar-session fixture seams in the real tree 3 -> 4 -> 5 bounded checkpoint-history chain. One persistent upstream fixture seam remained: provider-identity assertion verification.

The remaining failure was not a verifier defect. The deep legacy provider-window helper manufactured a positive provider-identity document but replaced `provider_identity_registration_v1`, its verification context, and the signed assertion receipt with empty objects. The original ADR 0100 verifier therefore returned `UNKNOWN` with `SOURCE_PROVIDER_IDENTITY_REGISTRATION_HASH_MISMATCH`.

ADR 0100 already provides a complete synthetic source: ADR 0099 registration replay context, a strict-canonical assertion receipt, Ed25519 registry signature, and bounded Merkle membership proof. Its provider ID and future-evaluation ID naturally match the complete ADR 0095 calendar evidence used by ADR 0360.

## Decision

Add a test-only source adapter in `test_strategy_correlation_persisted_checkpoint_history_coverage_provider_identity_seam_closure_v1.py`.

The adapter:

1. Builds one complete ADR 0100 provider-identity document and source bundle.
2. Injects that evidence at the deep provider-window return boundary, after the legacy helper has created its non-authoritative scaffold.
3. Lets ADR 0360 rebuild the calendar/provider composition, provider dataset registration, signed content attestation, and verification document against the complete provider source.
4. Captures the old provider-verifier mock calls and replays each call through the original verifier.
5. Classifies only the six raw legacy scaffold calls as failing original verification; those calls do not enter final evidence authority.
6. Stops the final provider-verifier patch.
7. Discovers every provider source embedded in the final tree 3 -> 4 -> 5 lineage and requires original-verifier acceptance.
8. Re-verifies bounded persisted-checkpoint history coverage after seam removal.

After ADR 0361, the final fixture material has no active correlation-replay, calendar-session, or provider-identity verifier seam.

## Consumer-first activation order

1. ADR 0100 source document and complete source bundle.
2. ADR 0119 calendar/provider composition rebuilt against both original-verifier sources.
3. ADR 0120 provider dataset registration, signed attestation, and verification rebuilt against the new composition.
4. Tree 3 lineage evaluation.
5. Tree 4 and tree 5 lineage generation and evaluation.
6. Bounded persisted-checkpoint history coverage re-verification after all three source seams are inactive.

No active consumer, current pointer, scheduled evidence, dashboard, pack, snapshot, summary, or trading path changes.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Complete final ADR 0100 source | Original verifier accepts |
| Empty provider registration | Original verifier rejects |
| Resealed `paper_authorized=true` provider document | Original verifier rejects |
| Raw legacy scaffold call | Excluded from final authority and explicitly counted |
| Missing middle persisted-checkpoint segment | Coverage is `UNKNOWN` and locked |
| Complete tree 3 -> 4 -> 5 lineage | Original coverage verifier accepts, permissions remain false |

## Evidence boundaries

- Pure synthetic and in-memory only.
- No historical market data, K-line task, G50/G51 task, blind test, service, browser, scheduler, publication, paper trading, or live trading.
- No profitability evidence or profitability claim.
- A valid local registry signature and Merkle proof do not prove external registry authority or provider identity truth.
- No external registration-time, assertion-time, replay-registry, durable-registry, complete-history, paper, or live authority.
- Natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
- Legacy pack-v5 public reads and pointer-v2 behavior are unchanged.
- UI and protected frontend assets are unchanged.

## Implementation fingerprints at design time

- Provider-identity assertion verifier: `17ba6cad39fe61163dca877ffec5cde01a796ee333d8d8cb7d2ce9109cd4a600`
- Provider-identity assertion verifier tests: `455ae9c1cc7be09cce0ff40df83b21bc91f0b274899f4c47c6a8a0561d82243b`
- ADR 0100: `c992476ea177201fe111d4d67c2160d5ae76161e189c8f39f9d455aca0f36b9b`
- ADR 0360 calendar seam-closure fixture: `e972e5ef5046aed4d989ecdeb3b2c8a6006c4a357b189a194ece67a67f7ba9b8`
- ADR 0360: `bd7bbbe7e21595e1cb78621362870b19db9dc85d55269d3359ab2334df76146d`

## Consequences

The bounded history fixture no longer depends on a persistent source-verifier mock. Final calendar and provider source evidence, composition, signed provider dataset attestation, lineage gates, and bounded coverage all remain independently re-verifiable by their original implementations. The result is still local synthetic conformance, not external provider identity, complete history, profitability, or trading authority.
