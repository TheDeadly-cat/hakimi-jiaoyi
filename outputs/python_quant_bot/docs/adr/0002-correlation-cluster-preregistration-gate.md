# ADR-0002: 跨标的相关簇预登记与分层门禁

## 状态

已实现 consumer-first 纯合同；current writer/admission 未激活

## 缺口证据

现有正式 strategy research 的 validation、frozen test 与 holdout 聚合按 symbol 计票。纯合成只读调用证明：AAPL、MSFT、NVDA 三个高度相关标的均为正，TLT、GLD 为负时，旧 3/5 symbol 比例可以 PASS；若前三者预登记为同一 `mega_cap_tech` 簇，则只有 1/3 独立簇为正，按 60% 簇门槛应 BLOCK。旧结果不是错误计算，而是缺少独立票单位。

## 决策

新增两个独立 sidecar 合同，不追溯改变 hypothesis-v3、report schema 14、固定 pointer 或 current 公共投影：

- `strategy-correlation-cluster-preregistration-v1`
- `strategy-correlation-cluster-gate-v1`

固定治理参数如下，调用方不能覆盖：

- 来源：完成态日收益 `COMPLETED_DAILY_RETURNS`
- lookback：60 个观察
- 最小成对重叠：40
- 高相关阈值：绝对 Pearson 相关系数大于等于 0.75
- 最少独立簇：2
- 每簇最多一票
- 簇内所有成员必须通过，该簇才通过
- 通过簇要求：`ceil(cluster_count * 0.60)`
- 正或负的跨簇高相关都在 TOPOLOGY 层 BLOCK，并要求新的预登记；不能在观察结果后静默合并簇
- `RAW_EXCESS` 与 `RISK_ADJUSTED` 两条 lane 分别评估，不互相借票

门禁顺序固定为 `PREREGISTRATION -> COVERAGE -> TOPOLOGY -> CLUSTER_VOTE`。任一前层失败时，后层为 `NOT_EVALUATED`。所有输入使用 exact field、原生类型、完整 pair coverage、canonical Hash 与共享 execution-authority 扫描；伪数字、布尔冒充、重复/漏 symbol、Hash 重封漂移和权限真值均失败关闭。

## 激活顺序

1. 先落地纯 builder/verifier/gate 与合成对抗测试。
2. 再为公共 verifier/projection 增加只读识别能力，但仍不改变 admission。
3. 通过新 formal CLI 在任何 selection 数据读取前发布不可覆盖的 cluster sidecar，并把 sidecar Hash 绑定到 protocol/registry。
4. 只有新的 report schema 能消费该门禁，用于 admission、candidate freeze、TEST 与 holdout；旧 schema 不追溯升级。
5. 完整 consumer、恢复、publication、projection 和对抗矩阵闭合后，才可另行切换 current。

当前实现永久返回 `current_writer_activation_allowed=false`、`current_admission_allowed=false`、`requires_new_report_schema=true`。门禁 PASS 只说明给定合成/冻结输入满足该 sidecar 合同，不是盈利证明，不授权 paper，live 仍永久硬锁。

### 冻结价格直接复算补强

shape-only matrix Hash 只能证明调用方自报相关系数自洽，不能证明系数来自冻结收益。consumer-first 第二层因此新增 `strategy-correlation-completed-price-input-v1`、`strategy-correlation-matrix-replay-v1` 与 `strategy-correlation-replayed-gate-v1`：每个预登记 symbol 精确封存截止日前最后 61 根完成态日收盘，绑定 SELECTION manifest、alignment input Hash 与 preregistration Hash；verifier 从价格重算 60 个 close-to-close 简单收益、成对重叠与 Pearson，再逐值重建 matrix 和 gate。常量价格、缺行、伪数字、未来行、跨簇负相关、coherent matrix reseal 与权限别名均失败关闭。

新增 `strategy-correlation-cluster-public-summary-v1` 只公开 replay 状态、固定方法、簇/票/pair 计数与固定 gap category，不公开 symbol、cluster/variant ID、Hash 或原始 blocker。它明确声明 local replay 不是 external authenticity；即使 `DESCRIPTIVE_PASS`，writer/admission/parameter selection/paper/live 仍全部为 false。该纯投影已接入现有 strategy-lab 只读 projection/UI consumer，但未接入 current report、admission 或 writer route。

### Consumer-first 公共投影顺序

1. 在正式 writer 之前，只让冻结研究投影识别顶层 `correlation_cluster_replayed_gate`。
2. 先调用 `strategy-correlation-cluster-public-summary-v1` 生成脱敏摘要，再从公开 payload 删除原始门禁。
3. 父级 `strategy-lab-research-projection-v1` 保持兼容，新增子合同独立版本化。
4. 前端共享展示层精确校验固定方法、状态、计数关系及永久 false 权限位；任何偏差降级 UNKNOWN。
5. 策略实验室复用既有请求，以中性 SOURCE -> GAP -> MATURITY -> PERMISSION 账页展示，不增加数据请求或运行时副作用。
6. 正式 manifest、事前 cutoff、registry 和新报告 schema 全部绑定前，禁止切 current writer 或 current admission。

当前已完成第 1 至 5 步的只读 consumer 接线；第 6 步仍是显式阻断边界，不因本地 replay 或 UI 展示自动推进。

## 对抗矩阵

- 3 个同簇正票不能冒充 3 个独立票。
- 单个簇成员失败会使该簇失败，包括 risk-adjusted lane。
- 相关系数恰好 0.75 与负高相关均触发跨簇阻断。
- cluster partition 必须完整、互斥、canonical；重复 symbol 阻断。
- preregistration/matrix Hash 篡改和 authority alias 阻断。
- matrix 缺 pair、overlap 小于 40、cell 漏项/重复/伪状态阻断。
- 即使 2/3 独立簇 PASS，current admission 仍固定为 false。

## 日期

2026-08-21
