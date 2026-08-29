# ADR 0119: Strategy correlation common-support calendar/provider composition v1

## Status

Accepted as an inactive, fail-closed research candidate. It composes ADR0118 with existing calendar-session and provider-identity assertion verifiers but does not activate observation admission, current writers, reports, paper, or live paths.

## Context

ADR0118 proves that one locally supplied completed-close replay deterministically yields a common-price window and recomputed correlations. It does not establish that those dates are registered completed sessions or that the dataset source label refers to a provider with a verified identity assertion.

The existing calendar and provider contracts are independently strong but unbound to ADR0118. A pure synthetic audit produced valid ADR0118, calendar-session, and provider-identity documents with zero shared lineage hashes. ADR0118 accepts only `matrix_replay`, contains no `provider_id` or calendar-verification hash, and remains unchanged when unrelated evidence is altered. Both existing source contracts also correctly keep external provider truth false.

## Decision

Add one detached composition receipt that:

1. Reverifies ADR0118 through its public verifier.
2. Reverifies the existing calendar-session document from its complete registration, batch, and verification contexts.
3. Reverifies the existing provider-identity assertion from its complete registration and signed membership contexts.
4. Requires ADR symbols to equal every calendar-batch return identity.
5. Requires the ADR common-price index to equal a contiguous suffix of the verified calendar-batch date index.
6. Requires exact symbol-index to registered-calendar assignment coverage.
7. Requires calendar evidence, provider-identity evidence, provider registration, provider assertion, and every ADR dataset source label to name the same provider ID.
8. Binds dataset data/manifest hashes into one aggregate provider-label binding hash.
9. Projects only aggregate counts and hashes; it does not project dates, prices, returns, symbols, calendar IDs, source labels, payloads, manifests, or verification contexts.
10. Keeps provider data-content attestation, external calendar authority, external provider identity, observation admission, profitability, paper, and live false.

The alignment policy is `ADR_COMMON_PRICE_INDEX_EQUALS_VERIFIED_BATCH_CONTIGUOUS_SUFFIX`. The source-label policy is `EXACT_DATASET_SOURCE_LABEL_EQUALS_VERIFIED_PROVIDER_ID`.

## Proof boundary

The receipt proves local exact composition: the ADR price endpoints form a suffix of dates accepted by the supplied calendar verifier, identities map to registered calendar indexes, and local dataset source labels match the provider ID in a cryptographically checked identity assertion. It does not prove that the provider issued or signed the dataset bytes, that the identity registry is externally authoritative, that the calendar library is externally governed, that timestamps are externally true, or that the strategy is robust or profitable.

## Consumer-first activation order

1. Keep ADR0119 synthetic-only and detached.
2. Add a provider-signed dataset-content attestation that binds every data hash and manifest hash.
3. Add independently governed calendar-library and registry trust evidence.
4. Add a versioned report consumer and neutral presentation only after those sources are reviewed.
5. Require a separate migration ADR before current admission or writer activation.

No market data, K-line task, backtest, browser, service, scheduler, report writer, paper path, or live path is used.

## Validation plan

- Unit-test exact suffix, identity, assignment, provider-ID, dataset-hash, source-fact, authority, privacy, deterministic-seal, and source-verifier boundaries.
- Run a separate public-API matrix with the real existing calendar and provider verifiers rather than mocked source results.
- Confirm active consumers remain unreferenced and all permissions remain false.

## Validation evidence

1. The targeted ADR0119 contract passes 19/19, including explicit per-field calendar and provider authority-injection matrices. The service and test compile in memory 2/2.
2. An independent real-source public-API matrix passes 18/18. It invokes the actual calendar-session verifier 13 times and provider-identity verifier 10 times rather than substituting source PASS values.
3. The independent matrix accepts an exact 80-session batch/61-price suffix composition and rejects shifted dates, identity drift, dataset source mismatch, derivation substitution, calendar/provider document drift, expected-hash drift, authority injection, and coherently resealed output drift.
4. The directly related calendar-session/provider-identity/ADR0118/ADR0119 family passes 84/84 across four TestCase classes.
5. The research lean profile lists and dry-runs 15 grouped checks. The ADR0119 TestCase and service source each occur once; planned is 15, while executed, completed, and reused are zero. Runtime mutation, paper, and live flags are false.
6. Eight explicit active entrypoints contain zero composition module, schema, fingerprint, state, or policy references.

Implementation fingerprints:

- Static fingerprint: `20260822-strategy-correlation-common-support-calendar-provider-composition-1`.
- Service SHA-256: `922E626C72C3EB6BE64A7A7D07EA0339655318EACAC44A5121370CF8E11B1197`.
- Test SHA-256: `0D74F312416721D057E315B960592DF5FADBC91028D78ED38F9D4899C67BE420`.

The broader provider-identity history family is outside this slice and was not rerun. The current natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`; legacy pack-v5 public reads remain UNKNOWN, and pointer-v2 fields, hash contract, and no-auto-reissue behavior remain unchanged.
