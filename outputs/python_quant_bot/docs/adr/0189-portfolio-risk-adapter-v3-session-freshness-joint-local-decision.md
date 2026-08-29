# ADR 0189: Portfolio-risk adapter v3 session-freshness joint local decision

## Status

Accepted as a detached research-only contract. It is not mounted, is not
`current`, and grants no runtime, paper, live, registry, writer, migration, or
shadow-consumer authority.

## Context

ADR0184 joins the base portfolio-risk budget with temporal correlation
stability. ADR0188 proves that adapter-v2, session freshness, and the legacy
matrix share the same native signed-content lineage, but intentionally does not
make a joint admission decision. Two policy gaps remain:

1. A risk-increasing proposal can have a valid adapter-v2 result while its
   completed-session freshness component is `BLOCK`.
2. A risk-reducing proposal must not be trapped by stale research evidence when
   adapter-v2 has already verified its dedicated reduction path.

## Decision

Add `strategy-correlation-cluster-portfolio-risk-adapter-v3` as a detached
consumer of the exact ADR0188 lineage-v2 document and an exact six-key
verification context:

1. `adapter_v2_document`
2. `freshness_evaluation`
3. `legacy_matrix_binding`
4. `adapter_v2_verification_context`
5. `freshness_verification_context`
6. `legacy_matrix_binding_verification_context`

The adapter first invokes the public ADR0188 exact verifier. It then requires a
`PASS` lineage, shared native lineage, exact component-state identity, no joint
admission in the lineage, and all authority flags locked.

| Proposal class | Adapter-v2 | Freshness | Adapter-v3 result |
| --- | --- | --- | --- |
| Risk increase | `PASS` | `PASS` | local research `PASS` |
| Risk increase | `PASS` | `BLOCK` | `BLOCKED_SESSION_FRESHNESS` |
| Risk increase | base or temporal `BLOCK` | any exact state | preserve adapter-v2 blocker |
| Risk reduction | verified reduction `PASS` | `PASS` | reduction-path `PASS` |
| Risk reduction | verified reduction `PASS` | `BLOCK` | reduction-path `PASS` plus stale warning |
| Any | invalid or cross-spliced lineage | any | `BLOCKED_ADAPTER_FRESHNESS_LINEAGE` |

`PASS` means only that this detached local research policy is satisfied. It is
not an admission, execution, profitability, or authorization claim.

## Output minimization

The result exposes schema/fingerprint, statuses, decisions, source hashes,
policy facts, blockers, warnings, and permanently locked authority. It does not
embed positions, completed prices, return series, correlation matrices, source
documents, or verification contexts.

## Consumer-first activation order

1. Keep adapter-v3 detached and validate only with synthetic in-memory chains.
2. Add a neutral public projection only after its exact consumer contract is
   separately preregistered.
3. Add an unmounted presentation only after projection equality is proved.
4. Extend the shadow-consumer preregistration in a later versioned ADR.
5. Consider activation only after independent evidence; never switch `current`
   as a side effect of this ADR.

## Adversarial contract matrix

The targeted contract covers fresh risk increase, stale risk increase, base
budget block preservation, stale risk reduction, lineage hash tampering,
fresh/stale cross-splicing, extra context keys, malformed inputs, exact rebuild,
non-mutation, output redaction, and authority lock.

## Compatibility and evidence boundaries

The natural-forward chain remains
`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`.
Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 fields and hash contract
are unchanged and no pointer is automatically reissued. No runtime assets,
market tasks, backtests, services, browsers, schedulers, or trading paths are
used by this change.
