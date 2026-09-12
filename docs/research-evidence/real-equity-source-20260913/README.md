# 第一条真实股票来源链：AMD 2024 Q3（部分完成）

这是一只公司、一次财报事件的工程输入验证。已经取得公司公告、提前日程、证券申报原文和纳斯达克日历，并用实际安装包导入财报、核对事件时点。**尚未取得日线价格，尚未执行完整股票快照、经济基线、独立账本和重放；T2 未完成。**

## 样本与原件

[选样记录](selection.json)先于价格检查保存：AMD 普通股，2024-10-01 至 2024-11-20。选择理由是公司财报原文和提前公告可取得，未按该窗口价格收益挑选；这不是历史盲选或预注册的策略有效性样本。T2 价格基线继续使用最初记录的25%仓位买入持有、手续费0.08%和滑点0.05%，其结果不可替代后续A/B对照。

[原件索引](source-index.json)记录六次实际下载的 URL、时间、字节数与 SHA-256。原始 HTML/PDF 保留在本地，未把公开可访问当作公开再分发许可。Nasdaq 历史行情网页只是页面原件，本轮未从它取得价格行。

- [AMD 财报](https://ir.amd.com/news-events/press-releases/detail/1224/amd-reports-third-quarter-2024-financial-results)显示 2024-10-29 16:15 EDT，即20:15 UTC。HTML时间与可见日期一致；这是调用者依据当前公司页面给出的公开时点声明，不是当年收到日志或历史不可变网页认证。
- [提前日程](https://ir.amd.com/news-events/press-releases/detail/1223/amd-to-report-fiscal-third-quarter-2024-financial-results)发表于2024-10-16 09:00 EDT，宣布10月29日盘后发布，另列17:00 EDT电话会。没有精确财报发布时间，不能用电话会时间或事后实际16:15替代。现有事件v1要求精确日程时间，该日程暂未导入；后续需明确的日期/盘后精度。
- [同期8-K](https://ir.amd.com/financial-information/sec-filings/content/0000002488-24-000161/amd-20241029.htm)支持 AMD 普通股与同期财报的关联。[公司FAQ](https://ir.amd.com/contacts-faq/faq)给出CUSIP及历史拆股信息；当前FAQ不能独自证明整个历史窗口不存在所有公司行为，经济接纳继续等待复核。
- [Nasdaq 2024日历](https://www.nasdaqtrader.com/content/technicalsupport/2024tradingcalendar.pdf)已实际渲染核对图例、10月和11月：所选51个自然日含37个常规交易日，没有窗口内的全日休市或提前收盘标记。该PDF副本元数据显示制作于2024-11-25，按回溯日历使用，不声称10月已经下载此版本；突发停牌/证券状态仍须供应商核对。

## 实际安装与事件结果

从 [CI 34708556328](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/34708556328) 下载Windows验收件，核对清单及wheel摘要，再在仓库外创建独立环境、以离线依赖仓库普通安装；`pip check`通过。wheel为 `526caec974eb8499b646e9a3c409ab5e248d309a602c728bd66cfd275d00fafa`，源码为 `c8a70bf903dc361ee9adf92280b698995595109809a5dab4c76be442be1e2078`。构建checkout为 `96011a6feed229614226b45dccde1218840e2bef`，受审head为 `0e306d7dda60a077af5ddbbf632a45dea7f4f2ac`，没有重标为本地73b682c构建或合并提交。

实际调用 `python -X utf8 -I -B -m hakimi_research.equity_cli event-import` 导入原始财报HTML；随后在禁网进程验证原件绑定、事件seal、可用前排除及可用时纳入。首次控制台回执的非ASCII路径存在解码问题，保留该回执；显式UTF-8重试幂等返回同一事件，之后核验使用路径可读回的UTF-8回执。

事件hash为 `a6aa5413907e290dc87fced108ebbf6c24a572f92aaa10d72a557cc858869f1d`。实际下载时间是2026-09-12 17:25:04.339787 UTC，提取时间是17:44:50.553779 UTC；历史 `received_at=null`。收集60秒加处理60秒是明确假设，故假定可用时间为2024-10-29 20:17 UTC。

[时点核对结果](event-calendar-verification.json)使用真实来源转录的日历与60秒日线延迟：完整观察日为10月30日，确认时间20:01 UTC，随后最早参考开盘为10月31日13:30 UTC。它验证的是日历资格，尚未绑定价格快照，也没有产生经济成交或策略收益。

营收和GAAP稀释EPS的原文数字及字符位置已保留在本地事件中，状态均为 `UNCERTAIN`，等待人工核准单位、倍数、财季和会计口径；一致预期为 `MISSING`。本轮AI核对不记为人工金标准或方向判断授权。

## 后续执行约束

[冻结的A/B方案](event-risk-filter-plan-v1.json)先于价格检查保存。A使用固定5/10均线及共同成本、风险和退出；B仅增加当时已知财报日程的新增买入过滤，阻止在预告财报日开盘新增风险，保留已有持仓的原退出规则，不顺延被拒绝的旧意图。实际日历已确认10月17日之前有12个预热交易日，满足现有均线入口的 `slow_window + 2` 要求。

方案尚未执行。必须先完成价格/公司行为接纳、事件日程精度、版本化决策输入、共享日历覆盖和防前视验证。所有不变、亏损、排除或无交易结果保留，不把37根日线当成37个独立事件。C/D在A/B及字段人工核准后再决定，当前 `NOT_RUN`。

行情适配候选为富途/moomoo。官方文档说明 [API行情权限与App权限不同](https://openapi.futunn.com/futu-api-doc/intro/authority.html)，[历史日线](https://openapi.futunn.com/futu-api-doc/quote/request-history-kline.html)需显式使用不复权及常规时段口径，[交易日历](https://openapi.futunn.com/futu-api-doc/en/quote/request-trading-days.html)不排除临时停市，[复权因子](https://openapi.futunn.com/futu-api-doc/quote/get-rehab.html)也不自动等于完整证券生命周期覆盖。地区、API可用性、原始价格许可与公司行为接纳仍待实际核对；本记录不连接账户、提交模拟订单或激活新调度。
