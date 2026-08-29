# ADR0484: History-covered proposal instrument identity binding candidate v2

Date: 2026-08-25

## Status

Accepted as a synthetic, unmounted application candidate. It does not replace
or activate the v1 proposal preflight, an HTTP route, a current pointer, paper,
or live execution.

## Current gap evidence

The existing v1 preflight is correctly fail-closed, but it has no authoritative
instrument identity resolver. In the inherited synthetic projection, canonical
symbol `A` is known in the budget source and carries a source-cluster binding,
while alias `A.N` is `UNKNOWN_SYMBOL_OUTSIDE_VERIFIED_BUDGET_UNIVERSE` with no
cluster binding. Both remain `NOT_AUTHORIZED`. This is not a current admission
bypass; it is a missing prerequisite for any future activation because aliases
cannot yet be proven to represent one economic instrument and one cluster ticket.

## Decision

Introduce one versioned candidate containing two inseparable contracts:

1. An internal identity preregistration maps a venue-qualified alias to exactly
   one canonical instrument identity and one existing budget symbol.
2. Alias lookup applies NFKC and case-folding only for cosmetic equivalence.
   Punctuation aliases are never inferred and must be explicitly preregistered.
3. The registry rejects duplicate normalized aliases, one canonical instrument
   mapped to multiple budget symbols, and one budget symbol mapped to multiple
   canonical instruments.
4. A resolved alias is routed through the existing v1 preflight using the bound
   budget symbol. The v2 output binds the canonical identity, budget symbol,
   source cluster, registry, projection, and legacy preflight by SHA-256 only.
5. A syntactically valid but unknown venue/alias returns diagnostic UNKNOWN with
   no canonical identity or cluster binding. Invalid or unverifiable contracts
   return no candidate document.
6. All candidate outputs remain unmounted, redacted, synthetic, and explicitly
   `NOT_AUTHORIZED` with proposal admission set to native `False`.
7. The builder accepts only four-field source entries. The verifier separately
   validates the five-field sealed schema, projects it back to source fields,
   rebuilds the derived alias lookup key, and requires exact document equality.
   A forged derived key therefore fails even when an attacker reseals it.

## Consumer-first activation order

1. Keep this verifier-only candidate unmounted and gather independent synthetic
   collision, alias, tamper, and cluster-routing evidence.
2. Define an independently governed real-source identity registry contract with
   issuer, share-class, venue, and lifecycle provenance. Synthetic identities
   cannot satisfy that stage.
3. Require batch and post-merge consumers to collapse equal canonical identity
   hashes before calculating independent-ticket or cluster budgets.
4. Add a neutral read-only projection using `SOURCE -> GAP -> MATURITY ->
   PERMISSION`; do not expose raw internal identifiers.
5. Consider activation only after producer receipts, freshness/replay binding,
   consumer preregistration, adversarial review, and a new explicit decision.
   This ADR does not make that decision and does not switch current.

## Adversarial matrix

- canonical symbol and explicit aliases must bind the same canonical identity,
  budget symbol, and source-cluster hashes;
- case and NFKC variants must not create additional identity tickets;
- unregistered punctuation aliases and venues must remain UNKNOWN;
- aliases of history-excluded symbols must inherit the existing exclusion;
- normalized alias, canonical-to-budget, and budget-to-canonical collisions must
  prevent registry construction;
- a valid replacement registry must fail against the trusted original hash;
- resealed permission promotion must fail exact reconstruction;
- public evidence must redact raw identifiers and contain no authority violation.

## Safety boundaries

All evidence is pure synthetic and in memory. No market data, old K-line,
runtime, database, cache, log, credential, backtest, blind test, scheduler,
service, browser, paper, or live task is used. Passing these contracts is not
profitability evidence, strategy maturity, or trading authorization. The current
single-look chain, legacy pack-v5 UNKNOWN behavior, and pointer-v2 no-reissue
contract remain unchanged.
