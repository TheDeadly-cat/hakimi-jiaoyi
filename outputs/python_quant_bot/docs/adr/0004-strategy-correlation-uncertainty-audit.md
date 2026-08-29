# ADR-0004: 相关簇阈值不确定性审计

## 状态

Accepted for dormant research-only implementation.

## 问题

60 日样本中的点估计 Pearson 相关系数存在采样误差。仅以 `|r| >= 0.75` 划分相关关系，会把区间跨越阈值的标的错误当成确定高相关或确定独立；收益序列的自相关还会进一步降低有效样本量。

## 决策

1. 从已验证的 61 行完成日收盘直接重算 60 个简单收益，不信任外部自报区间。
2. 对每一对收益计算 lag-1 自相关，并使用两者乘积调整有效样本量，结果裁剪到 `[4,n]`。
3. 使用固定 95% Fisher-z 区间评估绝对相关系数。
4. 区间下界不低于 0.75 才是 `CONFIRMED_HIGH`；区间上界低于 0.75 才是 `CONFIRMED_LOW`；跨阈值为 `AMBIGUOUS_THRESHOLD`。
5. 有效样本量低于 12 为 `INSUFFICIENT_EFFECTIVE_SAMPLE`。
6. 跨簇 `CONFIRMED_HIGH`、跨簇 `AMBIGUOUS_THRESHOLD` 或任意有效样本不足均 BLOCK；簇内确认高相关不产生额外独立票。
7. 审计为描述性研究合同，不改变 current gate、writer、paper 或 live。

## 限制

该 lag-1 有效样本量是预登记的保守启发式，不是外部真实性证明，也不替代更完整的时间序列模型、正式 registry 或 schema15 report。


## 事前 policy 绑定补充

audit 升级为 v2 并嵌入 `strategy-correlation-uncertainty-policy-v1`。policy 固定全部数值、分类规则和动作，并由 registration v2 与 protocol v4 hash 事前绑定。binding assessment v3 要求 audit 与 gate 的 matrix replay 完全相同，且 policy hash 与 registration 完全相同；任何 downgrade 或 coherent reseal 都 fail closed。

## 2026-08-21 Correlation decision fail-closed calibration

- A valid local artifact chain does not override a correlation decision.
- gate_decision_status must be exactly PASS. BLOCK, UNKNOWN, or a missing value emits local_correlation_gate_decision_block and stops before any formal registry transaction with CORRELATION_GATE_DECISION_BLOCK_OR_REREGISTER.
- Uncertainty remains independently fail-closed. This calibration activates no report/current writer and grants no paper or live authority.

## 2026-08-21 相关性不确定性公共投影与账页

- strategy-correlation-uncertainty-audit-v2 现在通过 strategy-correlation-uncertainty-public-summary-v1 进入只读 consumer。公共面只保留固定方法参数、pair 聚合计数、gap、maturity 与 permission。
- pairs、symbol、cluster、相关系数、置信区间、matrix replay、Hash 与原始 blocker 均从 strategy-lab 公共 payload 删除；无效或缺失来源稳定降级 UNKNOWN/null。
- strategy-lab backend 不增加请求，递归移除 correlation_uncertainty_audit；共享前端 presenter 使用 exact fields、原生数字、计数关系和永久 false 权限校验。
- 策略实验室在跨标的独立性账页之后增加并列 uncertainty ledger，顺序固定为 SOURCE -> GAP -> MATURITY -> PERMISSION，并以 95% CI 边缘标记提升重复扫描效率。
- 静态指纹为 20260821-correlation-uncertainty-ledger-1。Python 投影 6/6、strategy-lab 组合回归 15/15、既有与新增 Node 合同、三项 node --check 以及无浏览器 VM load-to-render 均已通过。
- VM 证据证明一次 afterend 插入、7/10 聚合 pair、敏感键为 0；它不是服务、浏览器、设备或视觉验收证据。本次未启动服务或浏览器。
- 本地描述性未阻断不是外部真实性、盈利证明或交易权限。current writer/admission、parameter selection、paper 与 live 均保持 false，live 永久硬锁。
