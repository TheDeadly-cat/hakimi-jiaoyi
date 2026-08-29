# ADR0469: Multi-window market-data common-cutoff gate v6

Date: 2026-08-25

## Status

Accepted as a versioned research-only consumer candidate. It is not wired to
`current`, runtime, schedulers, paper, live, or public evidence pointers.

## Context

ADR0468 verifies canonical `market-data-envelope-v1` payloads and recomputes the
20/60/120 correlation lineage. It binds every provider, dataset hash, completed
close row, timestamp grid, return panel, and downstream lineage hash.

That contract does not accept an independently declared observation cutoff. A
pure synthetic gap proof shifted all symbol timestamps by ten years, rebuilt the
canonical envelopes, v4 lineage, and v5 preregistration, and obtained v5 `PASS`
without changing any close or return value. This is correct for a content-binding
adapter, but insufficient for a common-vintage admission gate.

Three older contracts were reviewed before adding a new boundary:

- `native_cutoff_manifest_v1` binds a different 61-session completed-price and
  matrix-replay stack and explicitly does not prove freshness.
- `session_freshness_v1` depends on that legacy cutoff, calendar runtime, and a
  trusted-clock attestation while explicitly leaving external clock authority
  unauthenticated.
- `provider_dataset_content_attestation_v1` binds a legacy composition and
  provider signing key while explicitly leaving external key control and data
  issuance unproven.

Adapting any of those documents directly would create two competing source
authorities instead of closing the envelope-native seam.

## Decision

Add an envelope-native preregistration and exact-rebuild gate:

- preregister the sorted symbol set and per-symbol provider identities;
- preregister the envelope timeframe and exact final completed-row timestamp;
- lock 131 close rows, 130 close-to-close returns, and 20/60/120 windows;
- exact-verify the complete ADR0468 v5 context before reading chronology;
- recompute every timestamp grid and require strict order, uniqueness, equality,
  completion, and exact alignment with the preregistered cutoff;
- bind the recomputed panel cutoff and hash without embedding raw rows;
- return `UNKNOWN` for any mismatch, including a coherently resealed v5 chain
  whose common final timestamp differs by one millisecond.

The cutoff semantics are intentionally narrow:

`LAST_COMPLETED_ENVELOPE_ROW_TS_MS_NOT_FRESHNESS_SESSION_CLOSE_OR_INGESTION`

The gate does not claim that preregistration occurred before observation, that
the data is fresh, that a timestamp is a market-session close, that ingestion
time is known, that provider identity is authenticated, or that provider dataset
content is externally attested.

## Consumer-first activation order

1. Produce and retain the v6 preregistration outside gate evaluation.
2. Produce and exact-verify the existing v5 envelope-binding document.
3. Evaluate v6 in synthetic or isolated read-only consumers.
4. Collect adversarial evidence for cutoff, provider, payload, and authority
   drift while keeping all authority fields false.
5. Consider any `current` integration only under a separate ADR and explicit
   authorization. This ADR does not grant that authorization.

## Adversarial matrix

- coherent ten-year timestamp shift with fully rebuilt v4/v5 lineage;
- one-millisecond cutoff drift;
- preregistered provider drift;
- boolean cutoff and row-count values;
- case and whitespace variants of an unknown provider;
- symbol-order and provider-shape drift;
- payload completion tamper without envelope reseal;
- v5 authority injection;
- coherently resealed v6 cutoff and authority output tamper;
- raw-row and input-mutation checks.

## Consequences

The correlation-cluster evidence now distinguishes content identity from common
native cutoff. A v5 `PASS` remains necessary but is no longer sufficient for the
v6 cutoff condition. Freshness, external chronology, provider authentication,
profitability, paper/live permission, publication, and runtime activation remain
unproven and unauthorized.
