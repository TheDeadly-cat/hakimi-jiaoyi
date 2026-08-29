# ADR 0250: Stratified portfolio-risk presentation v7

## Status

Accepted as an inactive, unmounted, neutral presentation consumer. It creates
no HTTP registration, UI mount, current migration, runtime gate, writer, paper,
or live authority.

## Context

Portfolio-risk presentation v6 exactly projects adapter-v6, which combines the
linear multi-window portfolio-risk chain with downside-tail evidence. It keeps
the neutral `SOURCE -> GAP -> MATURITY -> PERMISSION` order and remains safely
unmounted.

ADR0249 added effective-bet-budget-v3 so active complete-link clusters are
collapsed by preregistered parent strata. Presentation v6 predates that source.
An explicit source audit found zero budget-v3 or active-strata bindings across
the v6 adapter, envelope, projection, registration, shadow preregistration, and
HTTP candidate.

A pure synthetic contrast made the gap executable. Budget-v3 produced one PASS
document for balanced separate strata and one BLOCK document for two active
clusters concentrated in one stratum. With the same v6 source, the v6 envelope
was byte-for-byte identical for both cases. Its builder, projection, and HTTP
candidate APIs accept no budget-v3 document, and its output has no active-strata
count, weighted-effective-strata count, or maximum-stratum-gross field.

## Decision

Add an unmounted joint presentation-v7 consumer. It accepts:

1. one v6 presentation envelope plus an exact-key v6 verification context;
2. one budget-v3 document plus an exact-key budget-v3 verification context.

The consumer calls both existing public exact verifiers. It accepts no
precomputed verification result. If either source or context is unknown,
substituted, inexact, or authority-promoted, the entire projection becomes
`UNKNOWN_SOURCE_PROJECTED_UNMOUNTED` and hides partial risk metrics.

When both sources are exact, v7 preserves v6's local status and budget-v3's
local status separately. A budget-v3 BLOCK overrides a v6 local clear state; a
v6 BLOCK also remains blocking. Only two local PASS components produce a local
joint PASS. The outer presentation remains `BLOCK` because it is unmounted and
unauthorized.

The bounded risk summary exposes only:

1. active dimension count;
2. conservative weighted effective strata count;
3. prior v2 weighted effective cluster count;
4. total active gross and trigger state;
5. dimension-level active-strata count, weighted count, dominant share, maximum
   stratum gross, and neutral PASS/BLOCK/NOT_APPLICABLE states.

It embeds no positions, matrix, return series, raw correlation, cluster gross
row, strata registration, source document, or verification context. Contexts
are represented only by strict canonical hashes after exact verification.

## Neutral presentation order

1. `SOURCE`: exact v6 and budget-v3, or unknown;
2. `GAP`: local research block, or local clear with governance gaps;
3. `MATURITY`: unmounted presentation candidate;
4. `PERMISSION`: no execution or activation permission.

No `READY`, directional color, profit language, or execution implication is
introduced.

## Consumer-first activation order

1. exact adapter-v6 envelope and exact budget-v3 source;
2. this unmounted joint presentation and exact verifier;
3. separately versioned HTTP candidate with no route registration;
4. static fixture and browser review under explicit authorization;
5. presentation consumer registration and independent cross-runtime receipt;
6. separate current/mount migration review;
7. runtime input admission only through an independently authorized gate.

## Adversarial matrix

- v3 PASS/BLOCK must change joint local status while v6 source stays fixed;
- v6 or v3 context substitution hides all partial strata summaries;
- budget BLOCK overrides v6 local clear without promoting outer status;
- source-free risk reduction stays visible but grants no authority;
- unknown, malformed, missing, extra-key, or spliced contexts fail closed;
- resealed authority, metric, stage, permission, source-state, or decision drift
  becomes verifier `BLOCK/UNKNOWN`;
- inputs remain immutable and output remains summary-only.

## Consequences

- The neutral presentation can no longer show a locally clear v6 result while
  silently omitting an exact active-strata budget block.
- V6 remains unchanged and independently valid for its original source scope.
- Presentation-v7 remains source-only research evidence. It is not browser QA,
  runtime acceptance, current admission, profitability evidence, route, mount,
  migration, receipt, paper, or live authorization.
