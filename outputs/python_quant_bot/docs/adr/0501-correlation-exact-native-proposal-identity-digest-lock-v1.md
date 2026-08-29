# ADR0501: Correlation exact-native proposal identity digest lock v1

Date: 2026-08-25

## Status

Accepted as fail-closed input hardening for the synthetic, unmounted ADR0486 and
ADR0487 candidates. It does not mount either candidate, change current evidence
pointers, register a consumer, persist a replay cursor, or authorize execution.

## Current gap evidence

ADR0486 accepted proposal identity fields through `isinstance(value, str)` and
hashed them through the virtual `value.encode()` method. ADR0487 repeated that
pattern while claiming proposal IDs were exactly cross-bound.

A pure in-memory adversarial subclass used the underlying proposal ID
`other-proposal-9` while overriding `encode()` to return the bytes of
`binding-p-1`. The two visible IDs were unequal, but their contract digest calls
were equal. The existing chain then built both the ADR0486 identity result and
the ADR0487 bridge, returning
`proposal_ids_symbols_amounts_bound_across_contracts=True` with an uncommitted
candidate status.

This is a Python object-semantics collision, not a SHA-256 collision. The digest
received attacker-selected bytes because a subclass method was invoked.

## Decision

1. Proposal collections and proposal occurrence records must be native
   `list`/`dict` objects at the ADR0486 and ADR0487 consumer boundaries.
2. Proposal ID, symbol, venue, registry identity, budget symbol, and hash inputs
   must be exact native `str` values. Requested gross basis points remain exact
   native `int` values, excluding booleans and numeric subclasses.
3. Identity digest helpers return no digest for non-native strings. They never
   coerce through `str()` and never call a subclass-controlled `encode()` path.
4. ADR0487 applies the same exact-native checks to both the identity proposal
   list and canonical freshness/CAS proposal tuple before claiming cross-binding.
5. Mapping, list, string, or numeric subclasses fail closed instead of being
   normalized into a valid ticket identity.
6. Existing exact-native synthetic fixtures retain their research-only outcome;
   all authority locks remain false.

## Consumer-first activation order

1. Keep ADR0486, ADR0487, and this lock synthetic and unmounted.
2. Require exact-native identity checks before any downstream provider receipt
   or replay-cursor conformance candidate consumes the bridge.
3. Rebuild dependent synthetic evidence rather than resealing old documents.
4. Obtain independent adversarial review before any registration proposal.
5. Require a separate activation decision. This ADR does not switch current.

## Adversarial matrix

- a `str` subclass with a different visible ID and aliased `encode()` bytes is
  rejected before ADR0486 construction and ADR0487 verification;
- a native-value `str` subclass is still rejected on the canonical side;
- a `dict` subclass cannot control proposal lookup or iteration;
- native proposal IDs, aliases, amounts, order, snapshot, and CAS bindings retain
  their prior uncommitted research-only behavior;
- amount/hash/context splices and resealed authority promotion remain rejected;
- outputs continue to redact raw proposal, symbol, venue, and stream identities.

## Safety boundaries

All evidence is generated in memory. No market data, old K-line, runtime,
database, cache, log, credential, backtest, blind test, scheduler, service,
browser, paper, or live task is used. Passing these contracts is not
profitability evidence, strategy maturity, provider persistence, trading
authorization, or release approval. The single-look chain, legacy pack-v5
UNKNOWN behavior, and pointer-v2 no-reissue contract remain unchanged.
