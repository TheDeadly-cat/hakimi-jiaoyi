# 二月历史留出测试与桌面验收

2026-10-26，按用户明确确认另起二月测试。两份正式研究、预定成本与基准、38次策略回调的前缀检查，以及原生窗口关闭重开均完成。四月因窗口内分红停止的记录原样保留，四月真实运行仍为0。本轮提供项目范围的历史留出证据；编码来源输出发生过一次已披露偏差，不能表述为全过程严格盲态。

## 先封存，再首次取价

[协议](research-evidence/independent-holdout-feb-20261026/protocol.json)固定NDAQ、KO：2026-02-02至02-27共19个评分交易日，01-14至01-30共12个预热日。沿用双均线5/10、25%仓位、3%止损、6%止盈、本金10000美元、费率0.0008、滑点0.0005；风险、成交与期末估值规则不变。没有按结果改参数、换区间、删去零成交或挑选成本情形。

| 证据 | 实际身份或时间（UTC） |
|---|---|
| 协议SHA256 | `e43adda930945e3fc8765e1c2a87f2109fa420ff91b09b6fc3e114e493f59b07` |
| 取价前提交 | `3451f2323e4acb2556aaeb382482f83ae681f5ce`，2026-10-26 11:11:22 |
| KO首次请求／取得 | 11:11:55.317670／11:11:55.909582 |
| NDAQ首次请求／取得 | 11:11:55.918646／11:11:56.500549 |
| 准备完成 | 11:11:56.732593，两标的均READY，各1次请求、0重试 |

[资格审计](research-evidence/independent-holdout-feb-20261026/exposure-audit.json)核对522条既存证据哈希，并将四月取价已经覆盖的03-16至10-23列为暴露范围；18组匿名CSV再次核对，重叠资料已归属BTC，未解决的候选重叠为0。此结论限定于审计覆盖的项目材料，不能证明任何人、模型或外部系统从未见过二月行情。

来源准入规则沿用已冻结版本：策略只用原quote OHLCV；窗口内公司行为拒绝；调整收盘价仅用于独立字段诊断，不进入策略特征。每份原件196行，选入31行，排除165行。实际取得原件、时间、逐行映射、哈希和不可变快照保存在本机，Git保留[取得回执](research-evidence/independent-holdout-feb-20261026/acquisition.json)、[准备清单](research-evidence/independent-holdout-feb-20261026/preparation.json)及绑定证据。来源仍为`IMPORTED_UNVERIFIED`。

## 实际结果

下表净收益均已包含相应费用与滑点。1×复用原正式结果；每项成本或基准分别使用独立10000美元本金，不能相加为组合收益。

| 项目 | NDAQ | KO |
|---|---:|---:|
| 1×策略净收益 | +1.446283% | 0% |
| 2×策略净收益 | +1.392534% | 0% |
| 3×策略净收益 | +1.338751% | 0% |
| 1×报告最大回撤 | 0% | 0% |
| 1×手续费 | 4.120999美元 | 0美元 |
| 1×成交／完整买卖 | 2／1 | 0／0 |
| 现金基准 | 0% | 0% |
| 100%买入持有基准 | −9.995616% | +8.590951% |
| 买入持有报告最大回撤 | 18.802850% | 2.809061% |

NDAQ只完成一次买卖；KO的19次信号均为HOLD，没有买卖信号或成交。两个结果均为`INSUFFICIENT_EVIDENCE`，不计算可解释为可靠估计的年化收益或夏普比率。策略25%仓位和基准100%仓位不同，不能据此证明策略优越；本轮报告回撤为0也不代表没有风险。

| 标的 | 任务ID | 正式运行ID |
|---|---|---|
| NDAQ | `1e59c059b27842135ee3d756b9c3dbc4054c7437cc6aa680588210d73e094cd2` | `b226aeeefd78a97cbd0714442bca757d32daa42cf54eeeceaaf60e8336a59959` |
| KO | `e3cd491980a4917d2760699d8a9b19e13c2a8c2e00e316896392c0e7cf5302f1` | `b57a1adc52aef12fd1bc1180f9c78998f8a10cc317a9f365523606356ec75e8c` |

NDAQ报告身份为`eca9aa9b8c39070a81009e72679213580640bed583f189737f794901452110be`，KO为`027096ba20c63d15e05abd3119167914068c7cbaf1374a734567f510fa9f1089`。成本验证身份及所有单元格完整值见[保存包回读](research-evidence/independent-holdout-feb-20261026/cost-and-operation-readback.json)。这份较早回执的重开状态当时为PENDING，保留原记录；最终关闭重开结论见[保全复核](research-evidence/independent-holdout-feb-20261026/final-preservation-review.json)。

## 禁止读取未来数据的实际检查

两份正式报告各执行一次冻结观察器复算，合计38次原注册策略回调。每次输入仅有当时可用前缀，从12行增至30行；未来索引拒绝，底层数值存储不共享全量行情。首步为01-30 21:01Z可用数据对应02-02 14:30Z执行，末步为02-26 21:01Z对应02-27 14:30Z执行。两次复算经济输出均与正式报告逐值相同，正式运行原6份文件各自不变；[逐步证据和完整验证日志](research-evidence/independent-holdout-feb-20261026/prefix-verification-summary.json)已保存。

实际计算计数为2次原生正式运行、8次成本/基准计算、2次观察器验证复算，共12次。工作台新增8条成功操作：2次导入、2次建任务、2次运行、2次成本验证。1×没有额外计算，重开只读记录没有增加计算。观察器复算是验证计算，不冒充额外产品运行。

该检查证明此次固定实现的回调可见数据边界及结果一致性；不是阻止恶意Python自行访问文件或网络的操作系统隔离。其单独输出的`blind_holdout_proven=false`保留，项目资格与取价前封存由独立证据支持。

## 原生桌面与保全

沿用已验收`0.6.0.dev3`、CLEAN构建`4338490f26dec70c79778cd5d1a85a2aaa3474d5`，源码内容`4019649982caff0bcb1e5fa23b6b5aafc848ffd2d27bb42a0ae402193f16a537`，wheel为`4dc7627fbc64bd551d7cf700cf55077961667dc4e8440172d80251c52d4f1fa4`。本轮没有改产品源码、构建或重新安装。

导入与建任务使用现有工作台API；正式“运行研究”和“验证基准与成本”均分别在原生桌面点击一次成功。先核对版本、工作区和冻结参数，再读两份结果、成本矩阵及样本诊断。NDAQ成本按钮一次元素定位失败未派发操作，随后新截图坐标点击成功；未因输入失败重复计算。原生操作由操作者记录，保存包复核只验证落盘身份，不冒充独立桌面回放。

关闭窗口5637570后，原11个进程（PID加出生时间）与65344监听均退出。从同一个`desktop/Start-Workbench.cmd`重开为窗口1837662、监听60724，重新打开NDAQ二月报告及两份已存成本包；窗口现保留在KO成本详情。关闭重开前后512份工作区文件及路径集合完全一致。旧四月508份、dev3工作区366份、八月工作区440份，以及新工作区内原440份副本逐份保全；这些范围有重叠，不相加为去重总量。四月根目录额外出现1个增量审计导入旧辅助脚本时自动生成的Python缓存，原508份均未改，但整个根目录集合不能称完全一致。缓存保留，路径与哈希写入最终保全回执。原Documents工作区的未提交状态也单独核对。

| 截图 | 验证内容 |
|---|---|
| [01](research-evidence/independent-holdout-feb-20261026/images/01-version-workspace.jpg)、[02](research-evidence/independent-holdout-feb-20261026/images/02-frozen-parameters.jpg) | 实际运行身份、新工作区和冻结参数 |
| [03](research-evidence/independent-holdout-feb-20261026/images/03-ko-result.jpg)、[04](research-evidence/independent-holdout-feb-20261026/images/04-ko-costs.jpg) | KO零成交结果和成本基准 |
| [05](research-evidence/independent-holdout-feb-20261026/images/05-ndaq-result.jpg)、[06](research-evidence/independent-holdout-feb-20261026/images/06-ndaq-costs.jpg) | NDAQ二月结果和成本基准 |
| [07](research-evidence/independent-holdout-feb-20261026/images/07-reopened-ndaq-result.jpg)、[08](research-evidence/independent-holdout-feb-20261026/images/08-reopened-ko-costs.jpg) | 同入口重开后的结果和成本读取 |

本机完整证据根目录：`C:\Users\Administrator\.codex\worktrees\insights-github-20261022\m32-independent-holdout-feb-20261026`。Git中为有界回执、逐步核对及8张实际截图，所有副本与本机原件哈希一致；[交付清单](research-evidence/independent-holdout-feb-20261026/verification-summary.json)说明完整原件的位置。两份正式研究、快照与成本包继续保存在该目录下的`workspace`。

## 必须保留的限制与历史状态

封存后的一次来源绑定核查误将`raw_base64`字段输出到工具结果（结果被截断）。协议要求来源质量核查不得在执行前向开发者暴露候选价格，这次编码原件显示属于该约束的执行偏差，不能称协议全项通过。后续将编码原件解码为不透明字节核对哈希，未解析其中的价格或检查候选收益，未据此改参数、日期和程序；仍不能声称编码原件从未显示或全过程严格盲态。[原偏差记录](research-evidence/independent-holdout-feb-20261026/metadata-review-note.json)与哈希保留，最终汇总明确引用。较早前缀汇总的“without decoding”简写只描述误输出本身，不代表整个核查从未解码；这里补充完整限定，原回执不覆盖。此偏差不改变封存早于取价的时间证据，也不代替逐日输入隔离检查。

参数来自十月旧任务，评分月份在此前；事后取得的来源不证明历史当时已取得同样字节。本轮是项目审计范围的固定历史留出，不是时间顺序样本外预测、自然前瞻、严格双盲或统计独立性证明。时间序列评估与训练/测试隔离的概念边界可参见[TimeSeriesSplit官方说明](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html)及[避免数据泄漏](https://scikit-learn.org/stable/common_pitfalls.html)。

四月因NDAQ预热首日分红STOPPED、真实运行0的原件保持；八月旧回放不改签为本轮结果。原十月基线之后的自然前瞻及二月报告“另一个后续区间”仍为NOT_RUN，未选后续区间不影响本轮二月运行已完成的事实。程序原54项定向检查及旧11项CI有独立身份；本轮没有为文档交付重跑整套本机测试。新提交的CI由PR #26按精确HEAD单独核对；PR继续为草稿，未合并或发布Release。
