# ADR0211: unmounted presentation HTTP candidate-v4

## Status

Accepted as an unregistered, unmounted, research-only interface candidate. It
does not create a method or route, access runtime/cache state, change current, or
authorize paper/live use.

## Observed gap

Candidate-v3 is pinned to preregistration-v8, request-v3, fixture-v3, and
registration-v1 semantics. It cannot accept or reverify preregistration-v10. A
pure synthetic API audit proved all six expected version-gap predicates.

## Decision

Add candidate-v4 without modifying v3. Its exact request carries v10 and the
three source documents required by the v10 verifier. The verification context
remains a separate exact dictionary and is never included in the response.

The response projects only:

1. SOURCE: exact v10 local reconstruction.
2. GAP: external trust, independent review, execution provenance, transport,
   browser, mount, and current gaps.
3. MATURITY: signed claim plus local execution binding-v2 only.
4. PERMISSION: unauthorized, with no route, mount, current, paper, or live grant.

Source documents, signatures, public keys, review contexts, and execution
evidence are not embedded. The transport and authority blocks are hard-coded to
false and the response is strict-canonical sealed.

## Frontend boundary

The existing correlation ledger remains the presentation surface, but this ADR
does not mount candidate-v4 or alter HTML/JavaScript. A pre-existing uncommitted
styles.css change was detected before editing, so CSS enhancement remains
deferred pending explicit direction rather than overwriting that work.

## Evidence boundary

Contract tests can prove deterministic local projection and redaction only. They
do not prove an HTTP route, runtime behavior, independent review, browser visual
quality, profitability, or trading authority. The natural-forward current chain,
legacy pack-v5 UNKNOWN behavior, and pointer-v2 non-reissue contract remain
unchanged.
