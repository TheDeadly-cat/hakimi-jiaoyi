# ADR 0349: Correlation uncertainty multi-window observation-overlap gate v1

- Status: Accepted as an unmounted synthetic research candidate
- Date: 2026-08-24

## Context

ADR0345 requires unique window identifiers, unique uncertainty-audit hashes,
exact audit verification, and conservative union of every non-confirmed-low
pair. Those controls prevent simple document replay but do not establish that
the windows contain distinct observations.

The existing contracts do not close this cross-window gap:

- ADR0262 binds one common-sample-set hash and count inside one edge audit.
- ADR0267 proves that all registered pairs share one ascending unique
  observation-membership digest inside one evidence unit, while intentionally
  excluding raw observation identifiers.
- ADR0151 hashes each symbol's exact price-date grid and proves equality inside
  one report identity, but does not compare two report windows.

A pure synthetic counterexample therefore remains possible: two exactly
verified low-correlation audits can have distinct audit hashes and make
ADR0345 return `PASS`, while both are associated with the same hypothetical
observation membership. ADR0345 correctly reports
`independence_units_claimed=false`; uniqueness of audit hashes is not
independence evidence.

## Decision

Add an unmounted ADR0349 post-gate veto. Do not mutate ADR0345 or ADR0346.

The ADR0349 preregistration hash-binds:

- the exact ADR0345 preregistration;
- the ADR0267 ascending-unique observation identifier ordering and digest
  algorithm;
- the ADR0151 date-grid schema and rule as provenance metadata;
- a fixed maximum pairwise Jaccard overlap of 5000 basis points;
- a fixed minimum per-window unique contribution of 2500 basis points;
- a study identity, observation-identifier scheme, window order, and evidence
  sequence.

Evidence supplies one ascending unique synthetic observation-ID sequence per
window. Its common-membership digest is rebuilt with the existing strict
canonical hash. The sequence length must equal every pair's
`overlap_observations` count in that window's exactly verified ADR0345 source
audit. Date-grid and ADR0267 gate hashes are retained as provenance bindings,
but their trusted issuer is not claimed by this candidate.

For every window pair, the gate computes:

`ceil(10000 * intersection_count / union_count)`

It blocks an exact duplicate or a value above 5000. For every window it also
computes the observations absent from the union of all other windows:

`floor(10000 * unique_count / window_observation_count)`

It blocks a value below 2500. Ceiling overlap and floor unique-contribution
rounding are deliberately conservative. An exact ADR0345 `BLOCK` is preserved.
Malformed, reordered, spliced, count-mismatched, or non-exact upstream evidence
returns `UNKNOWN`.

The gate output contains counts and hashes, not observation identifiers or
source audit documents. A `PASS` means only that the supplied synthetic
memberships satisfy the fixed overlap policy. It does not prove statistical
independence, market-data authenticity, or profitability.

## Consumer-first activation order

1. Verify the exact ADR0345 preregistration and gate.
2. Preregister the fixed ADR0349 policy before membership evidence exists.
3. Bind one common-observation membership and count to every verified window.
4. Bind a trusted ADR0267/date-grid membership issuer and exact source rebuild.
5. Evaluate pairwise overlap and per-window unique contribution.
6. Make ADR0349 a mandatory veto in a versioned successor to ADR0346.
7. Independently review any HTTP or runtime consumer.
8. Consider current activation only under separate explicit authorization.

ADR0349 remains at steps 1 through 3 in a synthetic, unmounted candidate. The
trusted membership issuer, effective-budget successor, runtime consumer, and
current activation do not exist.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Distinct audit hashes, identical memberships | `BLOCK` |
| Pairwise Jaccard overlap above 5000 bps | `BLOCK` |
| One window fully covered by the union of other windows | `BLOCK` |
| Disjoint memberships with exact ADR0345 `PASS` | research-only `PASS` |
| Membership count differs from verified audit pair count | `UNKNOWN` |
| Window order, audit hash, preregistration, or evidence splice | `UNKNOWN` |
| Unsorted or duplicate observation identifiers | evidence rejected |
| Reused date-grid or membership-gate source hash | `BLOCK` |
| Exact ADR0345 `BLOCK` with distinct memberships | preserved `BLOCK` |
| Resealed authority promotion | verification failure |

## Boundary

This ADR accesses no historical K-line data, runtime assets, database, cache,
logs, credentials, broker, scheduler, browser, paper account, or live account.
It creates no profitability number and grants no writer, HTTP, runtime,
effective-budget, current, paper, or live authority. It does not alter the
natural-forward single-look chain, legacy pack-v5 behavior, pointer-v2, or any
frontend presentation.
