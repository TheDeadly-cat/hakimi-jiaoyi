# ADR0213: portfolio-risk adapter-v5 multi-window joint gate

## Status

Accepted as an unmounted, local research adapter. It does not invoke runtime risk
services, write current, or authorize paper/live trading.

## Observed gap

Adapter-v4 can pass a single-window weighted budget while the separately verified
multi-window stability gate blocks because long-window cluster membership merges.
A synthetic call chain proved six predicates: v4 PASS, stability BLOCK, exact
partition-drift reason, no stability input in the v4 API, no stability fact in the
v4 output, and no existing joint consumer.

## Decision

Add adapter-v5 without changing pinned adapter-v4 or gate-v1. It fully reverifies
both documents and requires four cross-bindings:

1. The configured anchor window occurs exactly once in gate summaries.
2. The adapter weighted-budget-v2 document equals the anchor window document.
3. The adapter weighted verification context equals the anchor window context.
4. The adapter budget hash and canonical trade-identity hash match gate lineage.

The gate preregistration hash must also equal its out-of-band expected hash.

For a known joint evaluation, adapter-v4 BLOCK is preserved. If adapter-v4 passes
but stability gate blocks, adapter-v5 blocks. A PASS is possible only when both
components pass and every cross-binding is exact.

## Evidence and authority boundary

The output contains component hashes, states, decisions, anchor window ID, trade
identity hash, and boolean checks only. It does not embed matrices, positions,
source documents, or verification contexts. All writer/runtime/current/paper/live
authority remains false.

Synthetic contract evidence does not prove market stability, profitability, or
trading authority. Adapter-v5 remains unmounted and does not change the current
natural-forward chain, pack-v5 UNKNOWN behavior, or pointer-v2 non-reissue rule.
