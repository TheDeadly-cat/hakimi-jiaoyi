# ADR 0475: v9 signed-snapshot canonical position-claim adapter v1

- Status: accepted as an unmounted synthetic research adapter
- Date: 2026-08-25
- Scope: exact local v9 snapshot-to-gross-position conversion

## Context

ADR 0474 removed caller control over aggregate cluster gross by deriving it
from a canonical per-symbol gross-position claim. The remaining seam was the
origin of that claim: a caller could still submit positions different from the
signed portfolio snapshot already verified by dual-budget reconciliation v9.

An exact v9 `PASS` binds the signed snapshot claim hash, signed snapshot hash,
dynamic pre-proposal positions hash, equity, integer unit scale, sequence, and
observation time. Its document intentionally does not expose a canonical gross
position consumer claim. Directly copying another position list would reopen
the semantic freedom closed by ADR 0474.

## Decision

Add an application adapter that:

1. Accepts only an exact v9 document with local portfolio reconciliation
   `PASS`, `LOCAL_RESEARCH_SCOPE_RECONCILED`, and admission still `BLOCKED`.
2. Calls the real v9 verifier with the complete detached verification context.
3. Extracts positions only from the signed snapshot claim build arguments that
   the exact v9 chain already binds.
4. Rechecks the preregistered legacy snapshot claim hash, signed snapshot hash,
   dynamic positions hash, equity, integer unit scale, sequence, observation
   time, and snapshot semantics.
5. Converts each nonzero notional to gross basis points using
   `CEILING(notional_minor * 10000 / equity_minor)`.
6. Preserves a directional source fingerprint and never nets `LONG` against
   `SHORT`; the downstream claim is intentionally gross-only.
7. Builds the ADR 0474 canonical position claim with the consumer's exact
   projection preregistration hash.
8. Emits a bounded result without provider registration data, public keys,
   signatures, or the raw v9 verification context.
9. Provides deterministic exact reconstruction and rejects any promoted
   authority field.

## Safety interpretation

The adapter proves a local semantic statement only: the canonical gross claim
was derived from the same synthetic signed snapshot inputs accepted by exact
v9 reconciliation. It does not prove that the snapshot provider is externally
identified, that its portfolio data is true, that the snapshot is currently
fresh, or that any execution is permitted.

Provider identity, source truth, freshness, runtime binding, current admission,
paper, live, profitability, and trading authority remain false or unauthorized.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Raw v9 `PASS` has no canonical gross claim | Adapter supplies a versioned bounded claim |
| v9 hash, status, combined scope, or verifier drifts | Adapter returns no result |
| Signed position notional is changed | Real v9 verifier rejects the context |
| Sequence, observation time, equity, or unit scale mismatches preregistration | Adapter rejects |
| Duplicate, noncanonical, boolean, or invalid position | Adapter rejects |
| LONG and SHORT positions coexist | Both contribute gross exposure; no netting |
| Gross conversion has a remainder | Ceiling rounding is applied |
| Projection hash is malformed | Adapter rejects |
| Provider or signature material is present upstream | It is not projected |
| Authority field is promoted | Exact reconstruction rejects it |

## Consumer-first continuation

1. Keep this adapter unmounted and outside HTTP, registries, and current.
2. Feed only its embedded canonical position claim to ADR 0474 v2.
3. Bind the resulting incumbent cluster snapshot hash to the existing
   freshness/replay chain.
4. Bind provider identity and source truth through the existing signed provider
   registration and attestation contracts.
5. Add a neutral presentation consumer only after those bindings are exact.

## Non-effects

- No runtime portfolio reader, database, cache, log, key, network, service,
  browser, scheduler, backtest, blind test, paper task, live task, cursor
  mutation, route, registry, current pointer, or publication flow is used.
- No frontend or existing evidence artifact is changed.
- The natural-forward single-look evidence chain, legacy pack-v5 behavior, and
  pointer-v2 contract remain unchanged.
- No profitability claim or trading authority is created.
