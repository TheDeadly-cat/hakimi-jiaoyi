# ADR-0003: 相关簇事前注册与正式协议绑定边界

## 状态

Accepted for dormant research-only implementation. Current writer remains unchanged.

## 问题

本地冻结价格重放可以证明相关矩阵与簇门禁内部一致，但不能证明簇划分、cutoff、评估单元或 alignment hash 在观察结果前已进入正式注册。给已有 `strategy-matrix-protocol-v1/v2/v3` 事后追加字段并重算 hash 不能建立时间先验。

## 决策

1. 新增 `strategy-correlation-protocol-registration-v1`，固定簇 preregistration、cutoff、selection-alignment input hash、strategy/variant/lane 评估单元。
2. registration 固定目标为 `strategy-matrix-protocol-v4` 与 report schema 15；它本身不宣称已经进入正式 registry。
3. binding assessment 独立复核 replayed gate 的嵌套 preregistration、cutoff、alignment hash 和 evaluation。
4. `local_chain_status=PASS` 只表示本地链匹配；在 v4 protocol hash 与 schema15 report 同时正式绑定前，`status=BLOCK`、`formal_registry_bound=false`、`current_report_schema_bound=false`。
5. 现有 protocol v1/v2/v3 verifier 显式拒绝顶层或 batch spec 中的未来 correlation registration 字段，即使攻击者 coherent reseal。
6. 所有 registration 与 assessment 永久保持 current writer、current admission、paper、live 为 false。

## Consumer-first 激活顺序

1. 先部署 registration builder/verifier 与 assessment，不接 writer。
2. 再设计 protocol v4 canonical fields、registry transaction 和 immutable artifact binding。
3. 再设计 report schema15 的 producer 与 verifier，并绑定 v4 protocol hash。
4. 最后才允许公共投影读取 formal-binding receipt；仍不自动激活 current、paper 或 live。

## 非目标

- 本 ADR 不修改 current protocol 默认版本。
- 不创建或迁移正式 registry/DB。
- 不运行 blind test、收益回测、paper 或 live。
- 不把本地链匹配解释为外部数据真实性或盈利证明。


## 实施补充：dormant protocol v4

已实现显式 opt-in `strategy-matrix-protocol-v4`：

- registration 与 registration hash 进入 exact protocol 字段集合和 canonical protocol hash；
- protocol artifact 为必填；
- batch report schema 必须为 15；
- selection symbols 必须与 cluster partition 一致；
- registration 中每个 strategy/variant 必须存在于 batch；
- schema15 继承 schema14 的 search-lineage v1、hypothesis v3、nested workflow 与 canonical registry path 门禁。

binding assessment 升级为 v2，并验证 immutable sidecar。sidecar 验证只产生 `immutable_protocol_artifact_bound=true`，不产生 `formal_registry_bound=true`。下一激活门是独立设计和测试 v4 registry transaction；不得复用 sidecar 文件存在性代替数据库登记事实。



## Registration v2 补充

protocol v4 现在只接受 `strategy-correlation-protocol-registration-v2`。v2 在原 cluster/cutoff/alignment/evaluation 基础上增加 uncertainty policy 与 policy hash，并要求后续 uncertainty audit。v1 保留只读验证，但不得进入 v4，防止不确定性方法在结果观察后补写。

## 2026-08-21 Correlation decision fail-closed calibration

- A valid local artifact chain does not override a correlation decision.
- gate_decision_status must be exactly PASS. BLOCK, UNKNOWN, or a missing value emits local_correlation_gate_decision_block and stops before any formal registry transaction with CORRELATION_GATE_DECISION_BLOCK_OR_REREGISTER.
- Uncertainty remains independently fail-closed. This calibration activates no report/current writer and grants no paper or live authority.
