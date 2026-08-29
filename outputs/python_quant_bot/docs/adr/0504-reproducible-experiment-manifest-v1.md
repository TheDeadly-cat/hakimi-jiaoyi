# ADR0504: Reproducible experiment manifest v1

Date: 2026-08-29

## Status

Accepted for historical BacktestReport production. This is a research evidence
contract, not strategy promotion, paper/live permission, or profitability proof.

## Context

The basic backtest report already bound OHLCV, parameters, strategy source, risk,
cost assumptions, and a run hash. It did not produce one manifest that also
bound Git commit, worktree cleanliness, dependency lock, strategy version,
configuration, sample interval, random seed, runtime, evaluation role, and the
final result payload. Existing portfolio experiment registration is a separate
SQLite workflow and cannot serve as a pure report-level contract.

## Decision

Every `quant_bot.backtest.BacktestReport` now contains an exact
`reproducible-experiment-manifest-v1`. The report is created even when provenance
is missing; missing Git identity, a dirty worktree, an unpinned dependency set,
or malformed hashes produce explicit BLOCK rather than silently omitting the
manifest.

The CLI and Streamlit consumers collect read-only local Git and requirements
facts when a historical backtest is explicitly run. No service, network, market
data, database, scheduler, browser, or trading path is activated by the
manifest builder itself.

Validation/Frozen Test ranking input additionally requires a verified protocol
hash. TRAIN and UNCLASSIFIED results remain excluded from ranking input.
`ranking_gate.input_allowed` is structural input evidence only; parameter
selection remains false and no ranking consumer is activated by this ADR.

## Result identity

The manifest seals the report payload without the manifest itself. A
deterministic experiment ID is derived from the source run hash and result hash,
so identical evidence maps to the same report filename. Any result mutation or
resealed authority promotion fails exact verification.

## Preserved boundaries

The single-look chain, legacy pack-v5 UNKNOWN behavior, pointer-v2 no-reissue,
and exact `capability-v1` wire contract are unchanged. No result is a
profitability proof, and paper/live/order/automatic parameter authority remains
false.
