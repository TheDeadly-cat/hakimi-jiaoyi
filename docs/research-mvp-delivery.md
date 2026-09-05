# 研究 MVP 本地交付记录

已按目标报告及补充的完整任务大纲完成本地 Windows CLI 研究 MVP。
两份 Downloads 附件均已读取，ZIP 中的大纲与独立 Markdown 一致。
此前“未提供附件”的表述不准确：初次检查仅覆盖了目标附件目录，
没有定位 Downloads；补读后增加的要求已纳入当前验收。

## 可使用的产物

- [0.2.0 普通 wheel](../artifacts/releases/0.2.0-final/hakimi_research-0.2.0-py3-none-any.whl)
- [完整描述性研究报告](../artifacts/final-descriptive-study/summary_d098b7ba70c905786fa4f1fcb2c6848ddb436436767523b4c7441985ce139549.md)
- [JSON 研究摘要与全部报告索引](../artifacts/final-descriptive-study/summary_d098b7ba70c905786fa4f1fcb2c6848ddb436436767523b4c7441985ce139549.json)
- [安装验收记录](../artifacts/releases/0.2.0-final/wheel-acceptance.json)
- [第二安装环境重放](../artifacts/final-descriptive-study/independent-replay/study_replay_2a58bbffeaa936677b8dc5ddd3f966ea73146492265b93aa0f06c138e91fc70e.json)
- [独立账本核算](../artifacts/final-descriptive-study/reconciliations/summary_b62fe7022c0afb2357c0a262367b95b623f30bb3ad8cd4f04b0f38aab7fa9a1f.json)
- [摘要及状态切片核验](../artifacts/final-descriptive-study/reconciliations/view_86b4151eaa331fb62354e0fab3679ff33f329ea51cf6d1f3af5d09f0f0171830.json)

源码仍是 cf77 工作区的未提交修改，基线为
`f4bfa8adab07a21b66b341a0b8b2fe1804c537d7`。
最终 wheel SHA-256：
`30dd4e02225cd72242f157f49f36e65504922c75f1fb94ece5f54f8af0168bc7`。
实际打包源码摘要：
`753c2cab0b0b6fd6c41eae3a109342bb5523fd3286bd5e0138265c1163b843e0`，
交付前重新读取当前源码得到相同摘要。构建记录明确保留 DIRTY，未伪造 clean。

## 变更、理由与验收

| 项目 | 用户得到的行为 | 当前证据 |
|---|---|---|
| T0 | 基线、入口、依赖和变更分类可追踪 | [交付审计](research-delivery-audit.md)，437文件分类不冒充业务代码量 |
| T1 | 能力定义由 Python 产生；七组检查独立，总门禁严格检查失败/取消/跳过 | 当前23模块213项合同；历史五类参考及三项消费者检查通过，明确区分旧算法 |
| T2 | 首期亏损计入收益和回撤；成交/完整交易/费用/期末持仓可对账 | [记账语义](accounting.md)；独立Decimal对16份真实报告的66,866项核算通过 |
| T3 | 普通安装后在仓库外运行，产物不写入包目录；保存有原子性和不覆盖语义 | 中文及空格路径、全新环境、69项安装后测试通过；失败0、跳过0 |
| T4 | 原始字节到固定快照，版本修订关联旧版；CSV 来源/单位/完成声明可见 | [快照合同](dataset-snapshots.md)；旧v1和新v2并存，规范化数据哈希相同 |
| T5 | 一套引擎支持8种方法；预热和评分分开，策略初始化明确，Frozen不进入排名 | 因果性/窗口边界/Cash与Buy-and-Hold行为测试；所有正式和开发Frozen路径保持限制 |
| T6 | Git查询失败、实际依赖、构建来源和重放证据各自记录 | 两个普通安装环境均环境VERIFIED、来源BUILD_VERIFIED；16/16重放通过 |
| T7 | 报告只读；导航/调试/管理/进程终止受约束 | [消费者边界](research-consumer-boundary.md)；没有启动GUI或服务验收 |
| T8 | 固定真实快照、全部16个声明单元、同成本基准差、相邻参数和状态切片 | JSON/Markdown齐全；16/16账本通过；摘要另180项核验通过；亏损结果保留 |

各项测试存在范围重叠，不把这些数字相加当成全仓库覆盖率。
数值核算最大误差约`8.49e-12`；这证明记录账本的算术一致性，
不证明市场数据真实性、模拟成交可执行或策略有效。

## 真实研究范围与历史保留

仅显式采集了公开 OKX BTC-USDT 现货1h历史接口，三个响应页共900行，
按固定区间接纳744根完成线，区间外156根明确记录，缺口和重复为0。
数据为2026-08-01至2026-09-01（不含右端）；评分672小时，预热72小时。
来源字段与单位依据[OKX官方接口文档](https://app.okx.com/docs-v5/en/#order-book-trading-market-data-get-candlesticks-history)，
原始响应、请求参数、获取时间和哈希随快照保留。HTTP采集并非密码学来源认证。
当前为本地研究产物；没有评估或执行对外行情再分发。

Cash、Buy-and-Hold、Dual MA、RSI各有三档成本，另有四个相邻参数单元。
一个月的数据和少量完整交易不能支持正式确认结论；不同方法敞口不同。
选择来自任务大纲要求，不是根据合成收益选优。扩展计划前数据已被查看，
因此报告明确描述为开发期描述性研究。

初始3单元、随后16单元及中间wheel均保留。最后因Frozen权限收紧而进行的
16次审计重复，其计算身份16/16不变，来源身份16/16变化；这不是新增参数搜索，
也不是16份新的独立统计证据。第二环境重放对原件逐项核对字节哈希。

原957d工作区仍有36条状态记录，原临时原型仍有62条，均未被本次修改；
已有examples/archive参考未改写。当前源代码和交付物在cf77中。

## 验收决定与限制

本地 Windows CLI MVP 已满足安装、固定快照到报告、记账与重放要求。
这与代码合并验收、策略有效性验收分开。

- PR #1 保持 OPEN/Draft；没有提交、推送、合并、远端工作流派发或分支保护修改。
- 远端旧提交的CI仍是失败状态，不能把本地结果称为远端CI绿色。
- Linux包测试已加入CI矩阵，但本地没有可用Linux运行环境，实际Linux检查为NOT_RUN。
- GUI、旧HTTP服务的发布验收为NOT_RUN/NOT_ACCEPTED，不属于本次CLI首发交付。
- paper/live/order永久禁止；没有连接账户、订单执行、密钥或Futu管理。

合并前由维护者审查当前未提交改动、决定提交/推送并检查对应新SHA的远端门禁。
回滚应按文件和版本进行：旧报告/快照/参考保留，不执行reset、clean或强推。
不得把旧错误公式重新视为当前可用算法；源码迁移和数值语义的对应关系见上方各专项文档。

性能已在正常保护开启时实测5k/20k合成数据，详见
[最终核心性能记录](performance-profile-2026-09-05-v2.json)。并发负载未隔离，
单次测量不能当作跨平台SLO或优化收益证明。
