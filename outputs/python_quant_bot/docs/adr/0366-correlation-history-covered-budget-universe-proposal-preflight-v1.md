# ADR 0366: History-covered budget-universe proposal preflight v1

- Status: Accepted as an unmounted synthetic application consumer candidate
- Date: 2026-08-24
- Scope: Hash-only proposal classification before any runtime consumer

## Context

ADR 0365 preregisters a cluster-atomic projection from budget universe `A,B,C`
to history-covered universe `A,B`. It deliberately does not generate fresh
projected audits or an effective-budget evaluation.

A consumer-first sequence needs executable proposal behavior before any HTTP or
runtime mount. The behavior must not interpret projected membership as
permission, and it must distinguish an explicitly excluded symbol from an
unknown symbol.

## Decision

Add an unmounted application preflight with three outcomes:

| Proposal class | State | Meaning |
| --- | --- | --- |
| Excluded by ADR 0365 | `BLOCKED_HISTORY_COVERAGE_EXCLUDED_SYMBOL` | Missing history coverage or cluster-atomic exclusion |
| Member of projected universe | `BLOCKED_FRESH_PROJECTED_EVIDENCE_INCOMPLETE` | Projection exists, but fresh projected evidence is absent |
| Outside verified budget sets | `UNKNOWN_SYMBOL_OUTSIDE_VERIFIED_BUDGET_UNIVERSE` | No verified source classification |

Every outcome has `proposal_admission_allowed=false`.

The public result is hash-only. It emits hashes for the proposed symbol, source
cluster identifier, and source cluster members, but does not echo raw values.

## Neutral decision path

The response uses the fixed order:

`SOURCE -> GAP -> MATURITY -> PERMISSION`

For projected symbols such as `A` or `B`:

- `SOURCE`: ADR 0365 projection exactly verified;
- `GAP`: fresh projected budget evidence incomplete;
- `MATURITY`: projected universe preregistered only;
- `PERMISSION`: not authorized.

The contract contains no `READY` state or equivalent implication.

## Source and authority boundary

Before classifying a symbol, the preflight re-verifies ADR 0365 and its complete
ADR 0364 verification context. It does not trust self-sealed projection changes.

The preflight is not registered and does not authorize:

- proposal admission;
- effective-budget activation;
- the existing read-only projection adapter;
- HTTP or runtime mounting;
- current or pointer writes;
- paper/live orders;
- profitability claims.

## Adversarial matrix

The synthetic tests cover:

- excluded symbol classification;
- projected-but-immature classification;
- unknown symbol classification;
- neutral decision-path order and no `READY` wording;
- raw symbol and cluster identifier redaction;
- malformed symbol rejection;
- resealed ADR 0365 projection tampering;
- resealed permission promotion;
- deterministic exact verification and permanent authority locks.

## Consequences

ADR 0366 provides the first executable consumer behavior for the new covered
universe while remaining fail-closed. A later consumer may add a positive
research-only maturity state only after fresh projected evidence is available
and exactly verified. This ADR does not create that evidence or mount a route.
