# ADR 0305: Portfolio correlation admission and effective-budget binding v1

## Status

Accepted as an isolated, consumer-only, research binding.

## Context

Portfolio correlation admission v2 verifies the research universe,
complete-link gate, preregistered strata gate, and their exact evidence chain.
Effective-bet budget v3 verifies positions, a proposed trade, complete-link
cluster gross, weighted effective cluster count, and preregistered-strata
concentration.

Both predecessors are valid but independent. Admission v2 has no positions,
proposed notional, or effective-budget input. Effective-budget v3 has no
admission-v2 hash. A consumer can therefore observe an exact admission PASS
beside an exact effective-budget BLOCK without either document carrying the
other document hash.

The pure synthetic gap proof used one A/B/C preregistration, matrix,
complete-link audit and gate, and independent strata. Admission v2 returned
PASS. A concentrated A and B proposal at 50 percent gross each with a 45
percent cluster limit made effective-budget v3 return BLOCK. Both documents
verified exactly and neither contained the other hash.

This is not an error in either predecessor. It is a missing consumer binding.

## Decision

Add a versioned summary-only binding without modifying v2 or v3.

The builder takes one strict JSON snapshot and passes that same snapshot to:

- the admission-v2 exact verifier;
- the effective-budget-v3 exact verifier.

It then requires one shared hash chain across:

- report universe contract;
- correlation preregistration;
- correlation matrix;
- complete-link audit;
- complete-link gate;
- strata preregistration;
- strata gate;
- strategy identity;
- proposal scope;
- admission-v2 candidate;
- effective-budget-v3 candidate.

The binding tier order is:

1. INPUT_SNAPSHOT
2. ADMISSION_V2_EXACT
3. EFFECTIVE_BUDGET_V3_EXACT
4. CROSS_SOURCE_BINDING
5. ADMISSION_V2_DECISION
6. EFFECTIVE_BUDGET_V3_DECISION
7. PERMISSION

An exact admission PASS cannot bypass an exact budget BLOCK. The binding stops
at EFFECTIVE_BUDGET_V3_DECISION. An exact budget PASS cannot bypass an
admission BLOCK.

## Output boundary

The output contains hashes, statuses, checks, tiers, blockers, policy facts,
and negative authority facts. It does not contain source documents, positions,
proposed symbols, raw symbol lists, selection cells, strategy identifiers, or
cluster exposure rows.

The strategy identity and proposal scope are represented only by canonical
hashes.

## Fail-closed behavior

- Non-native containers, cycles, and non-finite numbers fail at INPUT_SNAPSHOT.
- Admission drift fails at ADMISSION_V2_EXACT.
- Budget drift or proposal mismatch fails at EFFECTIVE_BUDGET_V3_EXACT.
- Shared-source mismatch fails at CROSS_SOURCE_BINDING.
- Exact predecessor BLOCK decisions remain BLOCK decisions.
- Resealed permission promotion fails exact verification.
- No compatibility fallback or partial source match is accepted.

## Non-goals

- No change to admission v1 or v2.
- No change to effective-budget v1, v2, or v3.
- No migration to portfolio-risk adapter v7.
- No host, endpoint, route, UI, browser, scheduler, or writer integration.
- No historical market data, backtest, blind test, paper, live, or order task.
- No profitability claim.
- No change to the natural-forward evidence chain.
- No pack-v5 compatibility promotion.
- No pointer-v2 field, hash, or publication change.

## Authority

The binding is descriptive and consumer-only. Runtime gate activation, writer
use, current admission, internal backtest activation, paper authorization, and
live orders remain false. A local PASS proves only exact shared-source
agreement and two local research decisions.
