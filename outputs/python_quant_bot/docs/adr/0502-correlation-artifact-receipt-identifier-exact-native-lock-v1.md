# ADR0502: Correlation artifact receipt identifier exact-native lock v1

Status: accepted, synthetic-contract only, not activated as `current`

## Context

ADR0491 validates retriever and artifact identifiers with `isinstance(value, str)` and then uses those values in equality lookups against preregistered rows. A `str` subclass can override equality and hashing while retaining a different underlying string value.

A pure in-memory PoC exercised the real ADR0491 retrieval-claim and signed-receipt path. The supplied values were `other-retriever` and `other-artifact`, but their overloaded comparisons selected a preregistered retriever and artifact. The resulting claim used the canonical preregistered identifiers, and a signed receipt could be built and verified. This is an identifier-boundary alias, not a cryptographic hash collision.

## Decision

ADR0491 token and hash boundaries accept only exact native Python strings:

- `_require_token` requires `type(value) is str` before regex validation.
- `_is_hash` requires `type(value) is str` before hash-shape validation.
- No `str()` coercion or subclass-controlled equality, hashing, or encoding is used to normalize identity-bearing input.

The existing v1 schemas, canonical JSON representation, signatures, artifact identifiers, receipt identifiers, and activation state remain unchanged. Native-string callers remain compatible; non-native string subclasses fail closed.

## Consumer-first activation

The lock is applied at the shared ADR0491 consumer boundary already used by role registration, retrieval selection, signed receipt verification, and digest validation. No new producer, pointer, scheduler, dashboard, or `current` alias is introduced.

## Adversarial contract

The focused contract preserves native token/hash acceptance and rejects equality-alias subclasses for retriever IDs, artifact IDs, and hash fields. The pre-fix real-path PoC is retained as design evidence; the regression contract targets the shared boundary that made that path reachable.

## Non-authority

This decision uses synthetic in-memory evidence only. It does not run market data, backtests, services, schedulers, paper trading, or live trading, and it provides no profitability, readiness, persistence, or trading authorization claim.
