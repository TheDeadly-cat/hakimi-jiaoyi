# ADR 0007: Protocol-v5 Schema16 Ownership and Dormant Schema8 Consumer

- Status: Accepted for dormant internal consumption; not activated as current
- Date: 2026-08-21

## Context

Cross-symbol correlation clusters prevent highly related assets from being counted as independent votes. The family-wise multiplicity layer adds a second requirement: the number of cross-cluster comparisons and its correction policy must be fixed before returns are observed.

The consumer side already has versioned preregistration, protocol, registry, lineage, report-evidence, and schema8 verification contracts. A first implementation incorrectly treated the legacy schema7 matrix runner as the protocol-v5 producer and attempted to inject a separate multiplicity artifact at finalization. That runner executes one legacy strategy matrix, while protocol-v5 freezes a nested schema16 research batch with multiple variants. Wrapping schema7 therefore crossed workflow ownership boundaries and could not prove the registered schema16 computation.

## Decision

- `run_internal_strategy_research.py` is the only protocol-v5 producer. It derives multiplicity evidence from frozen selection payloads, manifests, alignment, cells, and rankings, then emits and verifies the schema16 research report before registry completion.
- `strategy-matrix-report-v8` is a dormant consumer envelope. It accepts one exact, independently verified schema16 formal report and derives the nested multiplicity identity from that report; callers cannot inject a separate evidence artifact.
- The legacy matrix runner remains a schema7 owner for its historical protocols. Recovery, main pre-claim, finalization, and report construction all explicitly reject protocol-v5 with `strategy_matrix_legacy_runner_protocol_v5_not_owned` before market-data loading.
- Schema8 validity and multiplicity decision remain separate. A replayable envelope may retain `decision_status=BLOCK`; current writer/admission, parameter selection, profitability claims, paper, and live permissions remain false.
- No current pointer, public projection, or UI consumer is switched by this decision.

## Consumer-first activation order

1. Freeze correlation, uncertainty, multiplicity, and family registration inputs.
2. Bind those inputs in protocol-v5 and its single-use registry transaction.
3. Produce and verify schema16 through the nested research runner using frozen selection inputs.
4. Replay schema16 into a dormant schema8 consumer envelope without a second evidence input.
5. Consider any current/public consumer change only under a separate versioned decision and evidence review.

Steps 1 through 4 are implemented with isolated synthetic evidence. Step 5 is not authorized.

## Consequences

- Old protocol/report hashes and behavior are not silently migrated.
- A protocol-v5 registration cannot be claimed or executed by the legacy schema7 runner.
- The no-mock synthetic chain proves schema16 production and schema8 replay mechanics only; it is not external market validity, a profitability result, or trading authority.
- No backtest, blind evaluation, service, scheduler, publication, paper execution, or live execution is activated by this decision.
- The natural-forward public chain and pointer-v2 contracts are unaffected.
