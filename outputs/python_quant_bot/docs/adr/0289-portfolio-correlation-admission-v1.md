# ADR 0289: Portfolio correlation admission v1

## Status

Accepted as an additive, synthetic, research-only consumer candidate. It is not
mounted into the current admission writer and grants no paper or live authority.

## Problem

`portfolio-backtest-admission-v3` can establish internal backtest readiness from
dataset, schedule, causal, universe, provider, and experiment controls without
consuming the existing correlation-cluster evidence chain. A portfolio can
therefore satisfy that legacy contract even when highly correlated symbols are
still being interpreted as separate selection votes.

The repository already has the required producers:

- a preregistered symbol-to-cluster assignment;
- an exact complete-link correlation gate;
- a preregistered cross-cluster strata assignment; and
- an exact strata gate that collapses clusters sharing a declared parent stratum.

The missing boundary is a portfolio admission consumer that binds those results
to the legacy internal admission without changing the legacy contract.

## Decision

Add `portfolio-correlation-admission-v1` as a versioned consumer. The candidate
rebuilds the legacy admission from a native JSON source report, then independently
verifies the correlation preregistration, matrix, selection cells, complete-link
gate, strata preregistration, and strata gate.

The ordered tiers are:

1. `INPUT_IDENTITY`
2. `BASE_ADMISSION`
3. `CORRELATION_PREREGISTRATION`
4. `CORRELATION_MATRIX`
5. `COMPLETE_LINK`
6. `STRATA_PREREGISTRATION`
7. `STRATA_GATE`
8. `PERMISSION`

The candidate returns research-level `PASS` only when every tier is exact and
both gates pass. `PASS` is not an activation or profitability claim. The output
stores hashes, statuses, checks, and blockers only. It does not embed the source
report, selection cells, correlation matrix, cluster topology, or strata map.

Checks are tri-state. `true` means the tier was evaluated and passed, `false`
means it was evaluated and blocked, and `null` means `NOT_EVALUATED` because an
upstream dependency did not pass. A complete-link block therefore prevents both
strata preregistration verification and strata gate evaluation. Downstream tiers
cannot add secondary blockers or manufacture partial evidence after that point.

Native JSON containers are required at the snapshot boundary. Mapping/list
subclasses, cycles, non-finite numbers, and non-JSON values fail closed before
any downstream verifier runs. This prevents second-read mapping behavior from
changing a document after the admission consumer has started evaluating it.

## Compatibility

`portfolio-backtest-admission-v3` remains unchanged. Existing callers retain
their current behavior. No route, CLI, engine, scheduler, report writer, or
frontend consumer is switched to this candidate by this ADR.

## Consumer-first activation order

1. Produce a preregistered cluster assignment and exact return correlation matrix.
2. Evaluate and verify the complete-link gate against exact selection cells.
3. Produce and verify the preregistered strata assignment and strata gate.
4. Build and verify `portfolio-correlation-admission-v1` from the same evidence.
5. Add a separate consumer registration that pins this schema and implementation.
6. Only after independent review may a future migration candidate replace a
   legacy research admission consumer. `current` does not change automatically.

## Adversarial matrix

| Case | Expected result |
| --- | --- |
| Two low-correlation clusters in separate preregistered strata | research `PASS` |
| Highly correlated symbols preregistered as separate clusters | `COMPLETE_LINK` block; strata `NOT_EVALUATED` |
| Two passing clusters assigned to one parent stratum | `STRATA_GATE` block |
| Missing or malformed cluster preregistration | fail closed before matrix use |
| Matrix resealed without rebuilding its complete-link gate | exact gate rejection |
| Source report promotes paper authority | base admission and permission block |
| Candidate is resealed after authority promotion | exact rebuild rejection |
| Non-native mapping attempts second-read behavior | snapshot rejection |

## Permission and evidence boundary

The candidate is consumer-only. Current writer activation, current admission,
automatic internal backtest activation, paper authorization, and live orders are
all false. Synthetic checks are not market evidence, profitability evidence,
fresh holdout evidence, forward observation, browser validation, or release
authorization.

The public natural-forward evidence chain remains:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null. Pointer-v2 is unchanged and is
not reissued by this work.
