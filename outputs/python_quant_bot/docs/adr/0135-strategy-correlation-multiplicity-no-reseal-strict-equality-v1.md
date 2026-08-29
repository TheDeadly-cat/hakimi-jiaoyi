# ADR 0135: Multiplicity no-reseal strict equality v1

## Status

Accepted on 2026-08-22.

## Context

The multiplicity audit and registration verifiers rebuilt canonical documents but
compared those documents with Python's ordinary container equality. Python treats
`False == 0` and `True == 1`, so an attacker could replace selected boolean leaves
with integer aliases while retaining the original document hash.

A pure-synthetic chain using an actual correlation protocol registration v2,
uncertainty audit, multiplicity audit, family registration, and binding assessment
proved the gap before production changes:

| Document | Boolean leaves | No-reseal accepted | Outer-reseal accepted |
| --- | ---: | ---: | ---: |
| Multiplicity audit | 350 | 8 | 0 |
| Family registration | 32 | 10 | 0 |
| Binding assessment | 11 | 8 | 0 |
| Total | 393 | 26 | 0 |

The accepted aliases included descriptive-policy flags, report and activation
flags, preregistration assertions, family requirements, and binding facts. No
accepted case granted paper or live authority, but accepting a non-canonical
document at a replay boundary was still a contract-integrity defect.

## Decision

Use `strict_json_contract_equal` for the final canonical rebuild comparison in:

- `verify_strategy_correlation_multiplicity_audit`
- `verify_strategy_correlation_multiplicity_family_registration`
- `verify_strategy_correlation_multiplicity_binding_assessment`

Keep all builders, schema versions, canonical hash algorithms, blocker names,
status semantics, and authority fields unchanged. This is verifier hardening, not
a new evidence schema and not current-chain activation.

Add one pure-synthetic actual-upstream contract that attacks every boolean leaf in
both no-reseal and outer-reseal modes. The locked matrix contains 393 leaves and
786 attacks; every attack must return `BLOCK` with at least one blocker.

## Consequences

- Integer aliases can no longer satisfy these three replay comparisons.
- Existing canonical documents remain valid and retain the same schema and hash.
- Correlation multiplicity remains descriptive and non-current.
- Natural-forward evidence, pointer-v2, UI wording, and paper/live authorization
  are unchanged.
- The matrix uses no runtime files, database, cache, logs, services, browser,
  scheduler, backtest, or trading task.
