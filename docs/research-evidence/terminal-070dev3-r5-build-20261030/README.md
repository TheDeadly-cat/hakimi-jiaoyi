# dev3 r5：账户共享控制与离线券商候选

本完整原终端候选从干净提交 `b642227ca176d0f6c61984194d06177b2c0be495` 构建，包含账户共享停止标记、同窗离线计划、可信包身份和受核验 protobuf 加载器。唯一构建完成，包文件及 ZIP 完整性检查通过；首轮辅助夹具失败保留，修正夹具后的独立续查通过。[正式交接](originals/dev3-r5-delivery-handoff-r1.json)记录最终身份与边界。

| 项目 | 实际身份 |
| --- | --- |
| 版本与入口 | `0.7.0.dev3 candidate-r5 / HakimiTrade.exe → /quant/` |
| bundle ID | `7382e481c0fb98e21bae87276a7fb75af6f7c9743e4e55d2105ffdf25110a013` |
| ZIP SHA-256 | `aec1b2fd6ada4bb05d81616ff2ea071a7f62c0af2b3aae2d86c45e5279c1ed1b` |
| manifest SHA-256 | `f3380aa2f5919161e5020b7502000341c17c2e640ff04af48087979e84f9ad68` |
| 文件与大小 | 9,079 程序文件；含 manifest 为 9,080 ZIP 条目；193,207,046 字节 |
| 本机位置 | `Downloads/Hakimi-Astra-Delivery-20261029/HakimiTrade-0.7.0.dev3-candidate-r5` 及同名 ZIP |

## 门禁和提交分别记账

[本地完整门禁](originals/stage-c-frozen-gates-summary-dev3-r5-r2.json)实际运行于干净 `7e1b28e0c44b3441e808d31230204887e05eebe6`：终端 757/757，0 跳过、失败、错误；另有打包 15、runner 4、health 6、exit 4、Futu 状态 32 项通过。终端内部 199.585 秒，外层 203.455 秒；当时完整 desktop 19.230 秒。[原 handoff](originals/dev3-r5-r2-gate-handoff-r1.json)的“构建因文案等待”状态按原样保留。

随后 b642 的 2,102 个代码输入中仅两份 UI 文件变化；1,046 个打包输入中仅账户 UI 和 FIRST_USE 文案变化。其余 2,100／1,044 项一致，[准确差异绑定](originals/stage-c-copy-delta-binding-dev3-r5-r3.json)及[派生摘要](gate-source-binding.json)保存依据。b642 单独运行的[完整 desktop](originals/gate-dev3-r5-copy-evidence-r3/desktop-result.json)为 18.324 秒，通过；没有把它写成 b642 本地重跑全部 757 项。

[CI171](originals/ci171-completed-summary-r1.json)的 11/11 成功属于 7e1；另一个独立的 [CI172](originals/ci172-completed-summary-r1.json)明确匹配 b642，11/11 成功，远端实际运行 757 项终端和 273 项研究检查。两份 CI 原件分别保留，不混用提交身份。

## 构建、首轮失败和续查

[唯一构建](originals/final-candidate-build-result-dev3-r5-r3.json)退出码 0，耗时 255.530 秒。普通依赖探针核对 16 个锁定依赖并本地导入所需模块，含 Futu SDK；没有创建 SDK context 或连接券商。[独立身份探针](originals/final-candidate-broker-identity-dev3-r5-r3.json)不导入 SDK/server，两模式身份匹配，adapter 缺失及兼容性未核实如实保留。

[首次完整文件与 ZIP 校验](originals/final-candidate-package-verification-dev3-r5-r3.json)通过；随后外部 JS 夹具未创建第二个临时 programRoot，生产路径检查正确拒绝 ENOENT。[首轮 FAIL](originals/final-candidate-acceptance-boundary-dev3-r5-r3.json)和[原始错误日志](originals/final-candidate-installed-js-dev3-r5-r3.log)保留。失败发生在 JS JSON 回执写入前；没有补造该回执或不存在的主 verify 原始日志。

只修正外部夹具后，[r4 续查回执](originals/final-candidate-acceptance-boundary-dev3-r5-r4.json)记录三个检查均退出 0：安装 JS 5.623 秒、包内功能闭包 19.275 秒、冷启动 protobuf 24.565 秒。没有重建或重复经济运行，也没有重算 ZIP 全部条目；沿用首轮完整 ZIP 核验，并记录归档大小/时间未变及程序全部字节复核未变。这里的 r3/r4 是验证批次，交付包始终是 candidate-r5。

- [安装 JS](originals/final-candidate-installed-js-dev3-r5-r4.json)：用全新 TEMP 验证共享 root 不随工作区或安装位置变化、继承路径被覆盖、错误或缺失 health 身份被拒绝；读取未创建共享目录。MSIX 项仅回放历史路径映射夹具，非新原生观测。
- [包内功能闭包](originals/final-candidate-feature-closure-dev3-r5-r4.json)：15 个嵌入 UI、真实安装模块和两模式计划只读入口通过；Node/Python root 身份一致，账户控制空读零数据库连接、零工作区创建。未调用计划准备/验证，未启动生产服务或原生窗口；生产 worker 仍拒启动。
- [protobuf 派生摘要](originals/final-candidate-protobuf-loader-summary-dev3-r5-r4.json)：私有解释器实际核对 11 类协议、192 个加载文件；不导入 Futu 顶层，socket、数据库、子进程、线程等受监测尝试均为 0。它只验证本地代码来源及最小合成报文，不证明 OpenD/加密、真实账户或生产 transport 兼容。原始 stdout/stderr、invocation、process-result、guard-final 已保留，完整原结果和模块映射留 E，以路径、大小和哈希引用。

构建只执行了[一次全新 TEMP 合成运行](originals/final-candidate-private-execution-dev3-r5-r3.json)，明确保存／运行／只读结果链通过；真实行情、旧研究回放和 provider 请求均为 0。门禁内的合成夹具与这一次构建探针分别记账。

## 用户范围和未验证部分

本包交付离线候选能力：配置与风险检查、模式隔离、未发送意图和有界计划，以及账户共享停止标记。shared stop 不阻止离线资料、意图或计划准备，本模式 local stop 仍独立约束准备；解除账户标记不解除 local stop、不授权、不重发，也不等于撤单或清仓。[文案范围说明](../account-control-wording-20261030/README.md)与[源码控制证据](../broker-account-control-20261030/README.md)分别保留。

按[任务清单 T29/T30](../../astra-backlog.md)，离线候选子项不以完整实际交易系统为交付前置；启用外部执行前仍须补齐生产授权门禁、worker/transport 串联、价格与费用事实等工程，并取得具体账户、资产和额度授权。九项外部权限均为 false；本包未连接券商、读取真实账户或派发订单。

本次没有原生 Windows 窗口验收、包内计划写入/停止恢复真人流程、独立无源码新机验收或新手理解验证。旧包、旧安装、旧业务资料和历史 UNKNOWN 未因本次证据整理改变；没有把本候选写成正式 Release 或全部任务完成。

## 原件与校验

[COPY_PROVENANCE.json](COPY_PROVENANCE.json)记录逐字副本的来源、大小和 SHA-256；其中 protobuf summary 明确是外部派生摘要，未冒充原始探针输出。完整输入映射、manifest、ZIP 条目映射和冷加载模块映射留 E，不复制 runtime、venv、SDK 或业务数据库。[SHA256SUMS](SHA256SUMS)覆盖除自身以外全部文件，`.gitattributes` 的 `* -text` 保留字节。归档过程只读取和复制证据，未追加测试、探针或验包。
