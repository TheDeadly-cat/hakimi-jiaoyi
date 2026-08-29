# ADR 0118: Strategy correlation common-support derivation receipt v1

## Status

Accepted as an inactive, fail-closed research candidate. It composes the existing completed-price matrix replay with ADR0117 but does not replace either source, change current reports, or authorize writer, admission, paper, or live paths.

## Context

The existing return replay verifies frozen completed close inputs and recomputes Pearson correlations, but it chooses each pair's date intersection independently. ADR0117 requires one shared observation-index commitment, but its v2 matrix accepts supplied correlation values rather than deriving them from prices.

A pure synthetic three-symbol construction gives each symbol 60 return labels, every pair 40 shared labels, and only 20 labels shared by all three. The existing replay verifier and three-singleton cluster gate both pass. The pairwise replay has no common-index hash. Neither source contract alone proves that every reported correlation was computed from the same return intervals.

## Decision

Add a detached derivation receipt and derived-gate consumer:

1. Reverify the complete existing matrix replay through its public verifier.
2. Intersect completed close dates across every preregistered symbol.
3. Select the latest at most 61 shared close dates and require at least 41.
4. Compute every symbol's returns over the same consecutive selected price endpoints, yielding 40 to 60 common observations.
5. Recompute every Pearson correlation with a versioned two-pass `math.fsum` method.
6. Build and reverify the ADR0117 v2 matrix from those correlations and the derived common observation index.
7. Seal source replay, completed-input, pairwise-matrix, preregistration, common-price-index, common-observation-index, and v2 matrix hashes in the receipt.
8. Do not project dates, prices, returns, payloads, or manifests in the receipt.
9. Let the detached derived gate reconstruct the private index and replay ADR0117 internally.
10. Keep current writer activation, current admission, paper authorization, and live-order permission false for every result.

The price-index policy is `LATEST_UP_TO_61_LISTWISE_COMPLETE_COMPLETED_DAILY_CLOSES`. The derivation scope is `LOCAL_VERIFIED_REPLAY_TO_LISTWISE_COMMON_SUPPORT_NOT_EXTERNAL_MARKET_TRUTH`.

## Proof boundary

The receipt proves deterministic local composition of a supplied verified replay into one listwise common-price window and one recomputed v2 matrix. It does not prove that the supplied closes came from an authoritative provider, that selected dates are genuine or consecutive market sessions, that missing sessions are correctly explained, that the cutoff is externally timed, that symbols are economically independent, or that the strategy is profitable.

## Consumer-first activation order

1. Keep receipt and derived gate synthetic-only and inactive.
2. Add calendar/session and provider-evidence composition without changing the derivation algorithm.
3. Add a versioned report consumer and neutral presentation only after those evidence layers are independently reviewed.
4. Require a separate migration ADR before any selection writer or current report consumes the result.

No market data, K-line task, backtest, browser, service, scheduler, report writer, paper path, or live path is used.

## Adversarial validation plan

- Reproduce pairwise 40/global 20 and require derivation failure.
- Check the exact 41-price/40-return lower bound and 61-price/60-return upper bound.
- Reject source replay drift, coherently resealed matrix drift, authority injection, source substitution, and derived-gate drift.
- Preserve ADR0117 topology, cluster-vote, and coverage blockers.
- Confirm deterministic output, index-hash sensitivity, source-row privacy, and permanently negative authority.

## Validation evidence

1. The targeted ADR0118 contract passes 17/17, and the service and test compile in memory 2/2.
2. An independent public-API matrix passes 18/18. It reproduces pairwise 40/global 20, independently recomputes Pearson with the Python standard library, and rejects source substitution, source drift, coherent matrix drift, authority injection, identity drift, and derived-gate drift.
3. The narrow v1 replay/ADR0117/ADR0118 core family passes 48/48 across four TestCase classes, preserving topology, cluster-vote, and coverage blockers.
4. The research lean profile lists and dry-runs 15 grouped checks. The ADR0118 TestCase and service source each occur once; executed, completed, and reused counts are zero; runtime mutation, paper, and live flags are false.
5. Eight explicit active entrypoints contain zero receipt, derived-gate schema, fingerprint, policy, or module references.

Implementation fingerprints:

- Static fingerprint: `20260822-strategy-correlation-common-support-derivation-receipt-1`.
- Service SHA-256: `343972949097F23BC3B33DADA9D897D1A820CB0D0FD2F6ECEA39EFB89AD8147C`.
- Test SHA-256: `863E3BC9BC7088345BF6936189B8009465E9CCD290CD7970B2936DF8181825F0`.

The provider-identity factor-calibration family is outside this slice and was not rerun. The current natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`; legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 fields, hash contract, and no-auto-reissue behavior remain unchanged.
