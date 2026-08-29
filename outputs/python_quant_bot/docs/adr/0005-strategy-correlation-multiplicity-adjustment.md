# ADR-0005: 跨簇相关性的多重比较调整

## 状态

已实现纯合成、consumer-first 前的 dormant 内部合同；未绑定正式协议、报告或 current。

## 缺口证据

strategy-correlation-uncertainty-audit-v2 对每个 pair 使用固定 95% Fisher-z 区间。该区间是单 pair 陈述，不是多个跨簇 pair 同时检查时的家族置信陈述。

在有效样本 60、绝对 Pearson 阈值 0.75 的纯数学例子中，r=0.86 的单 pair 95% 下界为 0.775404，可分类为 CONFIRMED_HIGH；当 family size 为 10 时，Bonferroni 双侧临界值为 2.807034，调整后下界为 0.726627，只能分类为 AMBIGUOUS。缺少预登记 multiplicity 政策会把单 pair 置信度误当成 family 置信度。

## 决策

新增两个版本化合同：

- strategy-correlation-multiplicity-policy-v1
- strategy-correlation-multiplicity-audit-v1

固定政策如下：

- correction method：BONFERRONI_TWO_SIDED_FWER_V1
- family scope：CROSS_CLUSTER_PAIRS_ONLY
- family-wise confidence：0.95
- per-pair alpha：0.05 / cross_cluster_pair_count
- critical value：Normal inverse CDF of 1 - 0.05 / (2 * family_size)
- minimum effective observations：12
- absolute Pearson threshold：0.75
- adjusted absolute interval lower >= 0.75 才是 CONFIRMED_HIGH
- adjusted absolute interval upper < 0.75 才是 CONFIRMED_LOW
- 其余为 AMBIGUOUS
- AMBIGUOUS、CONFIRMED_HIGH、样本不足与来源 BLOCK 均保持 BLOCK

该层具有单调失败关闭性质：它可以因家族区间变宽把来源的低相关描述降级为模糊，但绝不能把来源 audit-v2 的 BLOCK 翻转为 PASS。

## 完整性与隐私

builder 只接受 verifier PASS 的 audit-v2，并绑定 source audit Hash、完整 source artifact、policy Hash、family size、per-pair alpha、调整临界值、重算区间、分类与聚合计数。verifier 从内嵌 source 完整重放，不信任调用方自报状态或计数。

invalid source 不回显原始 symbol、pair、Hash 或 blocker，而是生成统一 SOURCE_INVALID 的可重放 BLOCK artifact。内部有效 artifact 可以包含 pair 明细，但它不是公共投影；任何未来公共 consumer 必须另建脱敏 schema。

## 激活顺序

1. 纯 builder、verifier、合成阈值与对抗测试。
2. 在任何 selection 数据读取前，使用新的不可覆盖事前登记绑定 multiplicity policy 与 family 定义。
3. 新 protocol consumer 同时绑定 audit-v2 与 multiplicity audit；旧 protocol 不追溯升级。
4. 新 report schema 才能消费该决策；不预先占用具体 protocol/report 版本号。
5. 完成恢复、publication、projection、公共脱敏与对抗矩阵后，才可另行评估 current 接线。

当前完成第 1 步，以及第 2 步的 dormant schema、builder、verifier 和只读 binding assessment。不可覆盖 publication/registry transaction 尚未实现，因此第 2 步没有成为正式门禁；protocol、report、current、parameter selection、paper 与 live 均未激活，live 永久硬锁。

## 验证

- 定向对抗测试：7/7 PASS
- 隔离 py_compile：PASS
- no-mock 61 根完成态合成价格链：source verifier PASS，multiplicity verifier PASS
- family size：7
- per-pair alpha：0.007142857143
- adjusted critical value：2.690109527159
- adjusted confirmed low：7

以上均为合成、描述性证据，不是收益数字、盈利证明或交易权限。

## 日期

2026-08-21
## 下一激活门槛：事前 Family Registration

multiplicity audit-v1 当前从已验证 audit-v2 读取 cross-cluster pair count。虽然 verifier 能证明该计数与冻结 matrix 一致，但正式激活仍不能把观察后的 artifact 当作 family 定义权威。

expected family size 必须在任何收益读取前从已预登记 cluster partition 推导：

expected_cross_cluster_pairs = C(total_symbols, 2) - sum(C(cluster_size, 2))

纯合成 partition 的簇大小为 1、1、3，总 symbol 数为 5，因此 expected family size 为 10 - 3 = 7，与 no-mock audit 的 cross-cluster pair count 7 一致。

本轮新增 `strategy-correlation-multiplicity-family-registration-v1` 及只读 `strategy-correlation-multiplicity-binding-assessment-v1`，绑定：

- 既有 correlation protocol registration-v2 及其 registration Hash
- cluster preregistration 及其 Hash
- multiplicity policy-v1 及其 policy Hash
- expected symbol count、cluster size multiset 与 expected cross-cluster family size
- 明确的组合公式与 source-before-returns 声明
- 永久 false 的 current、parameter selection、paper 与 live 权限

family registration 只接受通过验证的 correlation protocol registration-v2，并在收益输入前从其 cluster partition 重算 symbol 数、cluster size multiset、总 pair、簇内 pair 与 expected cross-cluster family size。invalid source 生成不回显 symbol、cluster 或来源身份的可 replay BLOCK artifact；duplicate member、partition 不闭合、Hash/policy 漂移、coherent reseal 与权限提升均失败关闭。

binding assessment 独立复核 source registration Hash、preregistration、multiplicity policy/Hash 以及 expected/observed family size。纯合成 1、1、3 partition 得到 expected=7，no-mock multiplicity audit 观测为 7；五层 verifier 均 PASS，local chain 与 local decision 为 PASS，但总状态仍固定 BLOCK，唯一下一证据为 `NEW_PROTOCOL_AND_REPORT_CONSUMER`。audit BLOCK 时只能返回 `RESOLVE_MULTIPLICITY_BLOCK_OR_REREGISTER`，不能越过到 consumer。

新增定向对抗测试 8/8 与隔离 py_compile 已通过，并已登记 lean test/syntax。以上只证明合成合同闭合，不是收益、盈利、外部真实性、选参、模拟或实盘证据。

剩余门槛是不可覆盖 family registration publication/registry transaction、新 protocol consumer、新 report schema，以及对应恢复、发布、公共脱敏和对抗矩阵。在这些边界闭合前不得切 current，也不预占具体 protocol/report 版本号。
