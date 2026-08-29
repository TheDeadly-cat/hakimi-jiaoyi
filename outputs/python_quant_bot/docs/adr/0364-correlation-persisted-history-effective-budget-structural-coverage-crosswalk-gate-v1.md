# ADR 0364: Persisted-history/effective-budget structural coverage crosswalk gate v1

- Status: Accepted for synthetic research evidence only
- Date: 2026-08-24
- Scope: Unmounted correlation-cluster coverage audit

## Context

ADR 0363 records a signed review claim that the persisted-history and
effective-budget sources share research intent. A signature cannot establish
structural study equivalence.

Read-only inspection of the exact synthetic source chain found:

- both sources use the same multi-window gate schema, implementation,
  uncertainty policy, activation sequence, and conservative aggregation
  parameters;
- persisted history covers symbols `A,B` and windows
  `window-01,window-02`;
- the effective-budget source covers symbols `A,B,C` and windows `short,long`;
- the shared-symbol cluster projection for `A,B` agrees;
- the full cluster partition differs because budget adds `C`;
- both source contracts retain `WINDOW_LABEL_ISSUER_BINDING_UNPROVEN`.

Equal window counts and a signed review statement are therefore insufficient.
In particular, `C` has no persisted-history coverage in the bound history
source and cannot be treated as an independently validated budget ticket.

## Decision

Add a versioned structural coverage crosswalk gate with policy:

`EVERY_BUDGET_SYMBOL_REQUIRES_PERSISTED_HISTORY_COVERAGE_NO_IMPLICIT_INDEPENDENCE`

The gate:

1. Re-verifies the exact ADR 0362 provenance preregistration.
2. Re-verifies both source multi-window cluster preregistrations with external
   expected symbols, clusters, windows, and hashes.
3. Cross-binds the history and budget window, symbol, and cluster hashes to the
   ADR 0362 pins.
4. Compares policy profiles separately from study identities.
5. Computes full-universe coverage and shared-symbol cluster projections.
6. Accepts only an order-preserving alias candidate crosswalk whose fixed
   relationship is `ORDER_ONLY_ALIAS_CANDIDATE_SEMANTICS_UNPROVEN`.
7. Keeps semantic equivalence, effective-budget activation, runtime, current,
   writer, paper/live, and profitability authority closed.

For the current synthetic source pair, the gate state is:

`BLOCKED_BUDGET_UNIVERSE_NOT_FULLY_HISTORY_COVERED`

The machine-readable uncovered symbol list is `['C']`.

## Claim boundary

The gate may prove that policy profiles match and that cluster partitions agree
after projection onto shared symbols. It does not prove:

- full symbol-universe identity;
- full cluster-partition identity;
- window semantic identity;
- issuer-bound window labels;
- semantic study-identity equivalence;
- permission to consume or activate effective budgets;
- profitability or trading authority.

`semantic_study_identity_equivalence_verified` remains `false`.
`effective_budget_activation_allowed` remains `false`.

## Consumer-first order

Any later consumer must follow this order:

1. Verify ADR 0362 provenance.
2. Verify both exact source preregistrations.
3. Require every budget symbol and cluster member to have persisted-history
   coverage.
4. Require shared-symbol cluster projections to agree.
5. Require issuer-bound semantic window descriptors, not ordinal aliases.
6. Require a separate governed semantic-identity decision.
7. Only then consider a still-unauthorized candidate consumer.

This ADR does not mount such a consumer or change `current`, pointer-v2, HTTP,
scheduler, runtime, or UI behavior.

## Adversarial matrix

The synthetic tests cover:

- uncovered budget symbol rejection;
- policy-match versus study-identity separation;
- shared-projection versus full-partition separation;
- order-only window alias non-promotion;
- resealed history-source tampering;
- resealed budget-source tampering;
- duplicate and semantic-promotion crosswalk rejection;
- resealed authority promotion rejection;
- exact document re-verification and permanent authority locks.

## Consequences

The signed review chain now has an objective structural counterweight. Future
work must either extend persisted-history coverage to the complete budget
universe or reduce the budget source to the covered universe before any
semantic decision or consumer registration can be considered.
