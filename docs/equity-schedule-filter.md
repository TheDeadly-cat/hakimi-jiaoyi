# 股票财报日程过滤与 A/B 对照

新增离线 `event-context` 和 `event-compare` 入口，事件开始实际影响新增买入。A 保留原股票价格规则，B 使用同一快照、评分区间、资金、费用、滑点、退出与数量模型，只加入事前已知财报日期过滤。两组仍使用原 BacktestEngine 的成交、费用、持仓和保护性退出；没有券商连接或下单能力。

规则沿用已冻结的 [AMD A/B 方案](https://github.com/TheDeadly-cat/hakimi-jiaoyi/blob/4bbb222a82503902fd188cabed4f8ea4836a76fa/docs/research-evidence/real-equity-source-20260913/event-risk-filter-plan-v1.json)。真实 AMD 普通股日线、来源权限和公司行为覆盖尚未接纳，真实 A/B 经济运行仍为 **NOT_RUN**。这里的合成行为检查不替代真实股票结果；C/D 公告字段条件与人工字段金标准也仍未完成。

## 日程和公告内容保持不同含义

原 `equity-event-v1` 文件、摘要和精确时间接口保持可读。新增 `equity-event-v2` 仅用于美国财报日程，保存 `schedule` 对象：

```json
{
  "status": "ANNOUNCED",
  "date": "2024-10-29",
  "time_precision": "AFTER_MARKET_CLOSE",
  "timezone": "America/New_York",
  "evidence": [{"quote": "on Tuesday, Oct. 29, 2024, after the close of market."}],
  "reason": null
}
```

日期精度可为 DATE_ONLY、BEFORE_MARKET_OPEN、AFTER_MARKET_CLOSE 或 EXACT_TIME。前三者要求 `scheduled_release_at=null`，不以电话会议时间代替财报发布时间；最后一种才允许准确时刻。日程字段引用原文，并沿用实际下载/提取时间、历史可用时间假设和不可借用旧时间的版本链。日期与语义仍是来源明确的提取声明，不是程序自动认证。

版本可以显式声明 CANCELLED 或 UNKNOWN，并引用对应原文、保存理由，日期和精确时刻置空。已知 UNKNOWN 版本会阻止新增买入；已知取消可以解除后续新决策的日期限制。未知公告时间的版本不能进入历史时点选择。实际 EARNINGS 公告不能被当成事前日程输入。

## 每次决策及执行时检查

价格信号使用实际收盘加数据可用延迟。引擎在该时点只选择已可用的日程版本，并检查信号对应的下一个实际开盘日期。到开盘时再选择当时可用版本，处理收盘后新增或修订的日程。若命中同一天的财报日，BUY 改为 HOLD；SELL、EXIT 和已有保护性退出继续使用原引擎。

被阻止的意图保留原动作、理由、大小及保护价格参数，并记录所用事件版本、原文摘要、公开/可用时间、字段状态和阻止原因。已取消意图不会因为后来撤销日程而复活，也不会推迟到下一天成交；之后只有价格规则生成的新信号可以再参与判断。Buy-and-Hold 只有一次原始买入决策，拦截后可能整段空仓，这类结果完整保留。

B 仍由价格规则产生买入，日程仅作风险过滤。日程未可用时不会借用未来版本影响过去决策；没有已知日程也不等于已经证明没有事件。若整个输入没有可用历史日程，B 明确拒绝运行，不能用事后实际公告日期补齐。

`event_snapshot_eligibility` 是共享的快照对齐入口，核验证券身份、完整快照及日历左边界。CLI 已改用该入口。旧 `event_session_eligibility` 保留为只接收会话列表的底层接口，不能单独证明日历覆盖完整。

## 离线使用

事件目录应明确仅含目标证券的日程及完整版本链。原文和 metadata 按原 `event-import` 保存后，运行：

```powershell
hakimi-equity-research event-context --event-dir $scheduleLedger --security-id $securityId --output-dir $output
hakimi-equity-research event-compare --snapshot $snapshot --spec $priceOnlySpec --event-context $context --output-dir $output
hakimi-equity-research replay --snapshot $snapshot --report $aReport --output-dir $output
hakimi-equity-research replay --snapshot $snapshot --report $bReport --output-dir $output
```

`event-compare` 接收原 v1 价格规约，自动构造两个 v2 规约，二者仅规则字段不同。输出两份完整报告及对照摘要：收益、回撤、费用、成交/完整往返数量、换手、平均收盘敞口、被拦截意图和无交易状态。公司/事件数量另列，日线和修订版本不当作独立公告样本。A/B 报告都保留全部决策与负结果；成交数和收益差不能被解释为因果意义上的“少赚了多少”。

单组 `research` 也可通过 v2 规约及 `--event-context` 运行；v1 规约不允许静默加载事件。报告保存完整上下文用于独立重放；原文未确认再分发权时，应仅在本地保存这些报告，不原样上传。

## 当前验证

183 项根目录测试通过，其中包含 21 项日程/对照检查；另 22 项旧兼容入口的回测与保护性退出检查通过。范围包含关闭规则后的完整价格结果一致性、未来修订不影响历史决策/经济结果、隔夜可用与延迟跨开盘、提前收市/盘中/周末、撤销不恢复旧意图、真实 Dual MA 新交叉、保护性退出不被过滤，以及已保存 A/B 报告的独立重放。测试均为虚构输入，不是策略盈利证明。

首轮两个测试错误地预期被拦截的 Buy-and-Hold 次日自动重试，实际策略仅决策一次；更正预期并增加 Dual MA 新交叉验证，未改变策略规则。一次旧兼容套件调用使用了错误工作目录，未加载到那两个模块；改在其实际目录运行得到 22 项通过。首次根目录运行的两条 CLI 测试则因父进程 UTF-8 与子进程本机默认编码不同而失败；统一子进程 UTF-8 后 183 项通过，原失败日志保留，没有修改旧 CLI 测试来掩盖问题。

独立 Decimal 账本核对器也接纳 v2 报告，继续核对相同的股票会话、费用、现金和持仓，不依赖策略引擎；3 项对应检查通过。它验证经济记账，事件版本和决策依据仍由事件报告核验及重放检查。

首轮 CI `34722525763` 的源码检查通过，但双平台安装检查均因新测试使用仓库内 `tests.*` 导入而失败；安装后的测试作为独立同级模块发现，不存在该包。已改为同时支持包内与独立发现，未给安装环境补入仓库路径，也未减少测试范围。修复后的安装与当前提交 CI 仍待交付验证；真实股票行情、公司行为、事件增量价值和官方券商模拟仍分别待验收。
