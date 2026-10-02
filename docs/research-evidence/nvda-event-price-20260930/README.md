# NVIDIA 两事件：渠道时间与行情闭环

2026-09-30（北京时间）。用户选定沿用 FY2024Q1／Q2，改由 Futu 只读取数，并要求先查证精确公开时间。本增量完成时间与价格条件诊断，收益研究尚未运行。

- [可读报告](report/index.html) / [机器结果](report/result.json)
- [渠道时间证据](publication-clock.json)
- [有界取数摘要](collection-summary.json)
- [待人工核准的八次离线对照方案](economic-proposal.json)

## 查明的时点

| 事件 | GlobeNewswire DOM 时间标签 | 纽约当地时间 | 价格确认可用 | 最早模型入场 |
|---|---|---|---|---|
| FY2024Q1 | 2023-05-24T20:20:30Z | 5 月 24 日 16:20:30 | 5 月 25 日 16:01 | 5 月 26 日 09:30 |
| FY2024Q2 | 2023-08-23T20:20:38Z | 8 月 23 日 16:20:38 | 8 月 24 日 16:01 | 8 月 25 日 09:30 |

两份发行渠道页面均署名 NVIDIA：[Q1](https://www.globenewswire.com/news-release/2023/05/24/2675692/0/en/NVIDIA-Announces-Financial-Results-for-First-Quarter-Fiscal-2024.html)、[Q2](https://www.globenewswire.com/news-release/2023/08/23/2730732/0/en/nvidia-announces-financial-results-for-second-quarter-fiscal-2024.html)。页面显示到分钟，DOM 的 `time datetime` 含上表秒数；未将秒数四舍五入为零。当前页面的财季与 GAAP 营收也与已留存 NVIDIA 原件核对。

NVIDIA [Q1 预告](https://investor.nvidia.com/news/press-release-details/2023/NVIDIA-Sets-Conference-Call-for-First-Quarter-Financial-Results/default.aspx)和 [Q2 预告](https://investor.nvidia.com/news/press-release-details/2023/NVIDIA-Sets-Conference-Call-for-Second-Quarter-Financial-Results/default.aspx)均预告约 13:20 太平洋时间发布。它们仅支持预定时段一致，电话会议时间未借作公告时刻。

此处是**渠道发布记录／已公开上界的历史重建**，不是所有渠道最早时间的认证。2023 年页面历史不变性及真实当时接收时点未证明。两次直接下载发行渠道 HTML 超时，随后保存的是浏览器渲染 DOM 观察，不能称为成功下载的 HTTP 原文；两份预告 HTML 下载成功。失败记录与 DOM 观察各自保留。

原第 6 版资料包 `f334413d…` 保留，所有原 `public_at=null` 未回填、未重签。新证据作为独立绑定文件，校验原来源摘要、页面时间、日期、标题与当前营收。渠道时点加 60 秒采集、60 秒处理延迟仍是明确的历史假设；复用既有 `price_confirmation`，没有修改其固定 120 秒规则。

## 实际行情与结果范围

每个事件固定公告前两个交易日、公告日和随后五个交易日，共 8 日。快照分别覆盖 2023-05-22 至 06-01、2023-08-21 至 08-30；窗口在新增价格查询前确定。用户授权使用 Futu，不涉及账户、订单、订阅购买或原始行情再分发。

实际共 6 个业务查询：证券元数据 1、公司行为 1、日线 2、常规时段小时线 2。共 16 根日线、112 根小时线，没有翻页或重复成功查询。

第一次运行在成功取得两份元数据后因本地解析器误要求 `get_rehab` 返回 `code` 列而停止。已按固定 SDK 的真实单证券接口修复并补回归；原失败未覆盖。单独的有界续接只请求尚未执行的四个行情查询，复用原成功回复。两阶段各自有 180 秒进程上限，中间存在排查间隔，**不能说成原一轮 180 秒内全部完成**。两阶段所属进程均正常退出并确认清理。

16 日 OHLC 与常规时段小时线汇总全部一致；16 日成交量均有差异，原因未证实。快照统一采用常规时段小时线汇总 OHLCV，日线仅作交叉核对，未混用两种成交量。公司行为窗口内无供应商报告的事件；身份稳定性和行为完整性仍是有来源的有限导入声明，不是独立认证的历史参考数据。

来源可比 2、行情快照 2、价格信号 2、价格与数值交集 2；人工核准 0、收益运行 0、研究接纳 0、内容干预未计算。旧任务至少 3 个候选的门槛仍未达到，未降低门槛，也没有按价格结果增加样本。两个已见样例只用于工程闭环。

## 复查与使用

本机 26 项新定向检查通过；另有 75 项既有取数、价格协议和来源流程回归通过，共 101 项。新检查使用虚构报价与页面证据，不联网。它们覆盖六次查询上限、续接不重复、错证券／缺失／重复行情、复权事件阻断、成交量差异保留、秒级时间与分钟显示冲突、原时间不回填、首个完整交易日失败后不得改挑后续上涨日。

在仓库根目录使用已安装研究依赖的 Python。以下入口全部离线；不会自动调用取数器：

```powershell
python -B tools/nvda_event_price_diagnostic.py `
  --packet <已有第6版任务目录>/packet.json `
  --clock-evidence-dir artifacts/nvda-price-20260930/time-originals `
  --lineage artifacts/nvda-price-20260930/snapshots-v1/lineage.private.json `
  --output-dir artifacts/nvda-price-20260930/reports
```

入口复验原任务、时间见证、原始行情摘要和快照身份，输出按身份分目录的 `result.json` 与 `index.html`。既有输出不一致时拒绝覆盖，重试可完成中断写入。原始行情、浏览器全文与私有路径只在本机 `artifacts`，GitHub 不具备自行重放私有行情的全部输入；可运行的合成检查与公开摘要范围分开。

本次浏览器核对证明页面可展示两事件、时间含义和待核准方案，不等于非开发者首次使用验收。研究执行、人工字段核准、main 合并、正式发布及部署分别处理。账户、订单、旧 T3／Unknown、客服邮件和新监控仍保持原状态。

## 2026-10-02：有限对照的执行准备

`tools/nvda_economic_study.py` 已准备好接收上述固定方案及具体人工核准回执。**真实 NVIDIA 收益仍未计算，原方案内容与摘要未改变。** 默认入口只复验已有输入并显示准备状态，不调用执行器。

执行复用原 `_SessionEngine`、`ContentSignalAdapter`、风险管理与独立 Decimal 账本；旧 AMD 专用入口及其冻结合同保持原样。共享账本只增加新报告格式标识，未改记账算法。本次内容条件为“实际营收高于已列同财季在先指引”，共同基准为“仅价格规则”；不增加第三组买入持有模拟。

人工回执须绑定原方案、来源包、渠道时间、诊断、两个快照及所核准字段。明确授权后，固定 8 份报告各运行一次、各重放一次并作一次独立账本核对。方案级独占执行记录防止换输出目录后重复运行；中途失败会保留已经开始的次数、报告和停止状态，不自动重试或扩大范围。输入与运行代码变化也会停止执行。

```powershell
# 只读准备；当前返回 PENDING_HUMAN_FIELD_AND_SCOPE_APPROVAL，真实收益运行 0
python -B tools/nvda_economic_study.py `
  --packet <已有第6版任务目录>/packet.json `
  --clock-evidence-dir artifacts/nvda-price-20260930/time-originals `
  --lineage artifacts/nvda-price-20260930/snapshots-v1/lineage.private.json

# 收到针对这两组字段和八次离线范围的人工确认后，绑定准确答复生成回执，
# 才可在上述命令中添加 --approval <核准回执> --execute-approved --output <新的私有结果目录>。
# 当前没有制作真实人工回执，也没有执行此步骤。

# 已有模拟结果的页面写入若中断，只重建页面，不重复模拟或重放
python -B tools/nvda_economic_study.py --report-study <已有结果目录>
```

新增 14 项虚构输入检查及 13 项既有内容执行／账本回归，共 27 项通过。验证覆盖次日开盘、两档成本下两组规则的一致性、内容否决、无信号、亏损、期末持仓、不带核准时阻断、八份报告与八次重放上限、失败停止及页面恢复。用于生命周期检查的授权替身只在临时虚构夹具中存在，不是人工回执。桌面虚构报告的收益率／百分点、费用展开和停止显示已检查；真实首次使用验收仍未完成。

详见 [执行准备回执](execution-preparation-20261002.json)。上一版 101 项定向检查及 PR `4e41f65` 的 CI 属于此前的证据身份，未重签为此次版本。
