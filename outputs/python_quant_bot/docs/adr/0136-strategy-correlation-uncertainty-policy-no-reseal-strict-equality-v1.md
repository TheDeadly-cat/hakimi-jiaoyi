# ADR 0136: Uncertainty policy no-reseal strict equality v1

## Status

Accepted on 2026-08-22.

## Context

The uncertainty policy verifier enforced an exact field set and rebuilt the
canonical policy, but its final document comparison used Python's ordinary
container equality. Python treats `False == 0` and `True == 1`.

A pure-synthetic pre-fix matrix attacked all six boolean leaves:

| Mode | Attacks | Accepted |
| --- | ---: | ---: |
| Preserve the original `policy_hash` | 6 | 4 |
| Recompute the outer `policy_hash` | 6 | 0 |
| Total | 12 | 4 |

The four accepted no-reseal paths were `descriptive_only`,
`requires_new_report_schema`, `current_writer_activation_allowed`, and
`current_admission_allowed`. The two permission aliases were independently
blocked by authority validation. None of the accepted aliases granted execution
authority, but accepting non-canonical policy types was a replay-integrity defect.

## Decision

Keep the exact field-set check and replace only the policy's final ordinary
equality comparison with `strict_json_contract_equal`.

Keep the policy builder, schema version, canonical hash algorithm, blocker name,
fixed values, and all authority semantics unchanged. Add a pure-synthetic
regression that attacks all six boolean leaves in no-reseal and outer-reseal
modes; all 12 attacks must return `BLOCK` with the contract mismatch blocker.

## Consequences

- Bool/int aliases can no longer pass uncertainty policy verification.
- Existing canonical policies remain valid with unchanged schema and hash.
- Together with ADR0134 and ADR0135, every remaining whole-document ordinary
  equality site is either removed through evidence-backed strictness or covered
  by dual-mode negative evidence.
- Natural-forward evidence, pointer-v2, current wiring, UI wording, and paper/live
  authorization remain unchanged.
- The evidence uses no runtime files, database, cache, logs, services, browser,
  scheduler, backtest, or trading task.
