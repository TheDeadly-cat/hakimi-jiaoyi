# ADR 0456: Live authorized alias fail-closed V1

## Status

Accepted on 2026-08-25.

## Context

The shared execution-authority contract recognized fields such as
`live_trading_allowed` and `live_order_allowed`, but not the widely used
`live_authorized` field. Pure in-memory evidence showed that all of these claims
passed both the violation scanner and sanitizer unchanged:

- `live_authorized: true`;
- `live-authorized: "yes"`;
- `LIVE AUTHORIZED: 1`.

NFKC and punctuation canonicalization worked as designed; the canonical key was
simply absent from the registered set. The platform control-center projection uses
a narrower field set, so adding the alias only to the default set would leave a
second compatibility bypass.

## Decision

Add `live_authorized` to the shared execution-authority field registry and to the
mandatory key set applied under every narrowed sanitizer call.

Canonical underscore, hyphen, whitespace, case, camelCase, and full-width variants
therefore share the same fail-closed behavior. Native `False` remains the only
accepted authority value. Descriptive prefixed fields such as
`raw_live_authorized`, and source metadata such as `source_authority`, remain
untouched because matching is exact after canonicalization rather than suffix
based.

## Consumer activation

The shared `execution_authority` service is the source contract for normal runtime
consumers, backtest-pack reexports, and the platform control center's narrow
projection. `platform_control_center.py` remains unchanged because mandatory keys
are applied inside the shared sanitizer.

The archived replay driver intentionally cannot import runtime code because it must
remain self-contained inside frozen evidence archives. Its documented equivalent
field registry is therefore updated in the same version, and the existing parity
test prevents future drift between the shared and frozen scanners.

## Adversarial contract

The dedicated pure in-memory matrix covers:

- underscore, hyphen, whitespace, camelCase, case, and full-width aliases;
- nested lists and tuples with exact audit paths;
- sanitizer input non-mutation;
- mandatory behavior under a deliberately narrow field set;
- platform control-center narrow-projection inheritance;
- native `False` and descriptive prefixed-field compatibility.

## Evidence boundary

These tests sanitize constructed mappings only. No runtime state, database,
service, browser, scheduler, paper task, or live task is used. Correct authority
scanning does not grant paper/live permission or establish profitability.
