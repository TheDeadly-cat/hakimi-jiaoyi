# 固定策略多窗口研究与完整流程测量

本轮先冻结 `multiwindow-plan-20260905.json`，再采集或查看结果。其规范 JSON SHA-256 为 `925206d29125388574c641f14cbec16e9842b1c4f6abaaee6a3ce12cabb2dfab`。原计划文件不因结果而改写；需要改变假设时应另存计划并解释原因。

计划覆盖 BTC-USDT 现货 1h 的 2023-01-01 至 2026-09-01，右端不含；最初72小时只作上下文，评分从2023-01-04开始。2023–2024为开发历史，2025至2026年7月为按时间分开的历史验证期，2026年8月为已经查看过的观察期。历史验证没有被声称为盲测或独立确认。

16个不重叠评分窗口包含14个季度以及独立的2026年7月、8月。每个窗口重置10,000 USDT和空仓，以相同72小时以上的上下文比较 Cash、100%买入持有、25%买入持有、Dual MA 20/60、RSI14，再分别运行1/2/3倍费用和滑点，共240个单元。参数、风险和窗口边界完整保存在计划中。缺失或质量不合格的窗口保留全部15个不可用单元，不通过缩短区间或删除亏损结果弥补。

25%买入持有匹配两项策略请求的起始配置，实际成交时间、手续费后仓位和后续敞口可能不同。报告同时给出请求配置、首次实际成交占初始资金比例、首次评分收盘敞口、实际收盘市值/净值按区间秒数加权的平均敞口，以及持仓收盘时段占比。最后两项是离散 OHLC 观测；同一小时入场又退出可能显示零收盘敞口，不应当作零盘中风险。

每一笔规范报告保留原数据、规约和源码身份。摘要列出收益、回撤、费用、相对于记录参考价的滑点成本、成交与完整交易数、亏损窗口、低于25%买入持有的窗口、无成交窗口，以及最大一个/三个正收益窗口占全部正收益的比例。正收益集中度分母不抵消亏损；没有正收益时记录不可计算。窗口每次重置资金，独立窗口损益之和不能当作连续执行业绩。季度与单月的长度不同，直接比较时应查看各自评分秒数，不把它们当成同分布独立样本。

使用通过安装验收的 wheel 环境，从仓库外运行以下工具。工具只是调用唯一 `ExperimentRunner` 的审计侧车，不另建执行引擎，也不连接账户。命令入口默认安装 Python socket 审计钩子禁止联网；数据采集在独立步骤完成。

```powershell
& $acceptedPython -B C:\path\to\tools\run_multiwindow_study.py run `
  --plan C:\path\to\docs\studies\multiwindow-plan-20260905.json `
  --snapshot-directory C:\research\multiwindow-captures `
  --output-dir C:\research\multiwindow-results
```

输入目录仅递归读取 `dataset_*.json`。也可重复传入 `--snapshot`。每个窗口选用完整覆盖窗口和72小时上下文的最小已验证快照；不会修改或拼接输入。全部运行记录在每个单元结束后立即以不可覆盖方式保存；摘要、Markdown和运行索引在全部单元结束后产生。JSON摘要不包含本机绝对路径，运行索引保留本地路径供操作员重放。

```powershell
& $secondAcceptedPython -B C:\path\to\tools\run_multiwindow_study.py replay `
  --run C:\research\multiwindow-results\multiwindow_run_<hash>.json `
  --output-dir C:\research\multiwindow-replay
```

原单元失败或不可用时，重放摘要明确保留未运行状态。结果、源码和环境都一致才标记已验证。来源版本变化需要跨版本分析，不能篡改旧报告或靠收益碰巧相同宣称同版本重放成功。

完整流程测量分别记录模块导入、快照读取和验证、规约读取、研究执行、报告序列化、规范保存、已保存报告校验、规范重放以及重放回执保存。规范执行和保存自身仍会重复检查，测量没有跳过任何保护步骤。

```powershell
& $acceptedPython -B C:\path\to\tools\profile_research_pipeline.py `
  --snapshot C:\research\dataset_<hash>.json --spec C:\research\spec_<hash>.json `
  --output-dir C:\research\profiles
# 另一次执行增加 --hotspots，记录 cProfile 热点及其测量开销。
```

冷导入测量每次使用新进程；应重复无插桩命令获得多个样本，再单独使用 `--hotspots` 定位热点。累积调用耗时存在嵌套，不应相加。报告绑定实际源码、环境、快照、规约和精确重放结果，不公开用户名、机器名或输入绝对路径。不进行未经测量的优化；若后续决定优化，应对完整订单、成交、信号和净值结果逐项保持一致，并另外覆盖浮点临界阈值。
