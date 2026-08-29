# ADR 0127: Strategy correlation complete-link strict equality v1

## Status

Accepted as a verifier hardening change. No schema, builder, report version,
current reference, writer, pointer, paper permission, or live permission changes.

Static fingerprint: `20260822-strategy-correlation-complete-link-strict-equality-1`.

## Demonstrated gap

The complete-link audit and gate verifiers, plus their projection, protocol,
registry-binding, and report-consumer verifiers, used ordinary Python document
equality. Python treats `False == 0` and `True == 1`, so a document could replace
a strict boolean with its integer alias without resealing any hash and still pass
exact-rebuild verification.

A pure synthetic traversal attacked every boolean leaf in a valid gate and audit:

- gate boolean leaves attacked: 15;
- audit boolean leaves attacked: 5;
- aliases accepted before the fix: 20 of 20.

The accepted aliases included nested legacy-gate permissions, complete-link audit
permissions, `requires_new_report_schema`, current-admission flags, and writer
activation flags.

## Decision

Use `strict_json_contract_equal` for exact-rebuild comparison in all five
complete-link layers:

1. cluster complete-link audit and gate;
2. migration projection;
3. protocol registration;
4. registry binding;
5. report consumer.

The strict comparator preserves JSON type identity, so integer aliases cannot
stand in for booleans. Builders and sealed document schemas remain unchanged.

## Adversarial evidence

The persistent property contract traverses every boolean leaf and replaces each
value with `int(value)` while retaining all original hashes. Every tampered gate
and audit must block. It also statically rejects reintroduction of
`document == expected` or `document != expected` in the five family modules.

Post-fix evidence:

- in-memory compile: 6 of 6;
- new strict-equality contract: 4 of 4;
- complete-link family plus real provider-evidence chain: 37 of 37;
- independent replay: 20 aliases attacked, 0 accepted;
- refreshed provider-evidence family: 113 of 113.

## Compatibility and authority boundary

Valid untampered gate and audit documents continue to verify. No threshold,
overlap rule, clustering topology, preregistration, selection, report schema,
natural-forward reader, pointer, or UI behavior changes.

This verifier hardening is not profitability evidence, runtime evidence, or
trading authorization. Current admission, paper authorization, and live ordering
remain false.