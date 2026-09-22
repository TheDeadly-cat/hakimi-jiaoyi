# 受监督股票研究预览与独立 Windows Futu 工具包

这是本机人工监督的候选交付。正式 Release **v0.2.1 保持不变**。
每个 ZIP 都可单独解压；`preview-manifest.json` 的完整 `build_id` 唯一绑定
全部文件、wheel、源码和随包证据。研究 wheel 的开发版本号不是唯一身份；
比较安装时同时比较完整构建 ID、wheel SHA-256 和研究源码摘要。
本包不会自动连接账户、启动采集／监控、注册任务或发送订单。

本轮是 `a64758a3df3ce73d433a2a2d71fac1e1a70dc5db` 基线上保留
`DIRTY` 观察的本机候选。它不是已合并 main `5d092260…` 或其 GitHub CI 制品。
源码与工具实际字节由清单逐项绑定；以后为官方模拟从新 Git 提交导出的工具，
必须使用新身份重新准备，不能把本包／旧数据库的回执重新签成另一构建。

| 独立包 | 内容与边界 |
|---|---|
| `supervised-research-…` | 普通安装的股票／BTC 研究 wheel、精确依赖锁、安装验收与公开历史摘要。另附 `tools/equity_event_diagnostics.py` 作为复用已安装 wheel 的离线研究工具；它不属于 wheel，也不含券商执行功能。 |
| `supervised-windows-futu-…` | `tools/` 内四个相邻执行文件、固定 `futu-api==10.7.6708` 依赖锁、Windows Job 约束及官方模拟说明。它不安装研究 wheel，只支持 Windows；本地 SDK 安装不是券商接口验收。 |

研究环境与 SDK 环境的 numpy／pandas 等版本不同，必须分别安装。
Python 3.14 是本轮受验运行环境；研究包声明的最低 Python 是 3.11，但不据此
声称所有 Python／系统组合都已完成本轮安装验收。SDK 工具包不包含 OpenD、
账户配置、凭据、授权文件、数据库、行情原件或旧环境别名。

## 查看版本、数据、结果与边界

在任意新目录解压任一包，用实际 Python 可执行文件运行：

```powershell
& 'C:\YourPython\python.exe' -I -B .\preview.py status
```

该命令只校验包文件并展示随包历史证据，不安装软件、不读账户数据库、不联网。
它显示源码／构建、原 AMD 样本的数据来源和 A/B 结果、订单试验边界、运行健康
的核验范围及未验收项。原 AMD A/B 均亏损，零买入拦截，不能解释为规则盈利。
原买入持有工程基线评分起点不同，不能直接与 A/B 排名。

`evidence/` 内日期属于原证据；打包时间不刷新证据时间。`CURRENT_STATUS.md`
和可选 `observation-closeout/closeout.json` 是冻结的状态摘要。`status` 不查询当前
调度／进程／账户；`NOT_CHECKED` 不能写成正常，也不能把历史的 `NOT_RUN`
理解成程序没有实现。实际行情与完整轨迹因再分发范围未核准而不随包提供。
已有本机原件须由维护者选择明确路径作为研究输入。
第三版保留 `evidence/futu-preflight-20260920.json` 的最初失败，并另带
`evidence/futu-readonly-followup.json`：修复后两轮账户读取一致、证券核验通过，
但未知期权记录仍阻挡执行，证据时刻处于非正常交易时段，下单数为零。
工具保留零价格观察，不修改执行价格检查；详见 `evidence/futu-resolution-followup.md`。
状态入口区分原失败与后续读取，不重新查询，也不把历史证据当作当前账户许可。
后续真实读取使用的源码身份与最终仅调整输出的工具身份不同，随包分别保留；
`evidence/futu-followup-tests.json` 的54项本地测试绑定最终适配器，不能回签在线回执。
研究包的 `evidence/equity-events/` 另包含固定十事件计划、已准备的官方来源索引、
原 AMD 样本新增同期间／压力成本诊断；它们仍明确标为早期准备证据。
第三版另外带十事件最终摘要：7个接纳窗口、3个因价格差异排除，42份不同报告，
其中一个事件阻挡一次BUY，其余六个没有阻挡；七个窗口A/B均亏损。
两个独立包的状态入口均可显示这些最终结果，完整原件／私有报告均不随包分发。
随包历史文档保持原字节，其中仓库相对链接可在来源仓库查阅；本 README
与状态命令自身可独立使用。

## 新环境安装

为每个包选择仓库与解压目录以外的全新运行目录。以下示例先进入所选包目录；
`runtime-root`、依赖 wheelhouse 和 Python 路径由使用者明确指定，不依赖旧
AppData、PATH 别名、仓库源码或手工 `PYTHONPATH`。无需激活虚拟环境。

```powershell
# 离线：wheelhouse 需包含对应依赖锁的全部 wheel。
& 'C:\YourPython\python.exe' -I -B .\preview.py install --runtime-root 'D:\HakimiPreview\research-001' --wheelhouse 'D:\DependencyWheels\research'

# 或明确允许 pip 下载依赖。只用于安装，不连接行情或账户。
& 'C:\YourPython\python.exe' -I -B .\preview.py install --runtime-root 'D:\HakimiPreview\research-002' --allow-package-downloads

& 'C:\YourPython\python.exe' -I -B .\preview.py status --runtime-root 'D:\HakimiPreview\research-002'
```

同一入口在 Futu 独立包内安装 `futu-env`，在研究包内安装 `research-env`。
环境不继承系统包；子进程去除 `PYTHONPATH`／`PYTHONHOME`，使用普通 wheel
安装。安装完成检查依赖及实际安装身份，Futu 检查只读发行包元数据，不导入
SDK，不启动 OpenD。`*-installation.log` 保留每条安装命令和错误；
`*-installation.json` 绑定包身份。安装失败保留现场，使用新运行目录重试，
不要删除记录以伪装首次成功。文件身份校验不是数字签名，仍需信任来源。

## 研究运行、数据路径与恢复

以下命令来自研究环境，离线读取明确指定的输入：

```powershell
& 'D:\HakimiPreview\research-002\research-env\Scripts\python.exe' -I -B -m hakimi_research.equity_cli capabilities
& 'D:\HakimiPreview\research-002\research-env\Scripts\python.exe' -I -B -m hakimi_research.equity_cli research --snapshot 'D:\PrivateResearch\snapshot.json' --spec 'D:\PrivateResearch\spec.json' --output-dir 'D:\HakimiPreview\research-002\reports'
& 'D:\HakimiPreview\research-002\research-env\Scripts\python.exe' -I -B -m hakimi_research.equity_cli replay --snapshot 'D:\PrivateResearch\snapshot.json' --report 'D:\PrivateResearch\report.json' --output-dir 'D:\HakimiPreview\research-002\replays'
& 'D:\HakimiPreview\research-002\research-env\Scripts\python.exe' -I -B .\tools\equity_event_diagnostics.py --help
```

运行配置由 `--spec` 指定，数据由 `--snapshot` 指定；没有隐式账户配置。
优先显式 `--output-dir`。未指定时沿用 `HAKIMI_RESEARCH_HOME` 或
用户主目录下 `.hakimi-research`；解析路径不会创建目录。示例配置作为只读
资源位于已安装包的 `resources/`，不是实际行情。研究 CLI 不使用订单 SQLite。
每条命令结束即退出，无服务需要停用；中断可用 Ctrl+C。报告原子发布且拒绝
覆盖不同内容，失败后保留原件，用同输入重放或全新输出目录诊断；不修改旧报告。

## Windows Futu 工具运行与停止

从 Futu 包运行 `--help` 可离线查看阶段参数：

```powershell
& 'D:\HakimiPreview\futu-001\futu-env\Scripts\python.exe' -I -B .\tools\futu_simulation_cycle.py --help
```

具体操作遵循随包 `futu-official-cycle.md`。工具必须作为相邻四文件整体保留。
每次阶段使用新私有输出目录；数据库通过 `--database` 明确指定且保持同一物理
位置；账户配置通过 `--profile` 指定。SDK 日志由周期工作进程限定到本次输出
目录的 `private-sdk-logs`，无需已有 AppData SDK 环境。安装和状态入口没有执行
周期的功能。账户连接／只读准备须符合操作范围；submit／cancel 仍需单独有效授权，
本 README 及“安装完成”都不能生成授权。

每次阶段进入独立 Windows Job，执行上限 180 秒、输出 128 KiB、清理预算 5 秒。
阶段退出后人工检查 `process.private.json` 的返回码与 `cleanup_confirmed`，
以及 `receipt.private.json`、`phase-start.private.json`、stdout／stderr 日志。
Ctrl+C／异常退出不证明订单未发送；清理不明确时停止操作，不自动重试。
提交可能到达供应商后，只能依同一数据库、同一构建和既有授权政策进行新进程
`recover` 查询。代码摘要、profile 历史窗口或授权已过期时保留停止状态，另行复核；
不得编辑旧 SQLite、重建意图或将数据库复制到新位置绕过登记。
撤单 ACK 不等于终态，没有已绑定订单 ID 不撤单。缺失费用保持未核实。

## 构建、重现与验收范围

维护者先在源码稳定后运行 `tools/verify_wheel.py`，取得仓库外普通安装的
`wheel-acceptance.json`；再运行：

```text
python tools/build_supervised_preview.py --acceptance <new-wheel-acceptance.json> --output <new-delivery-directory>
```

可通过 `--observation-summary` 加入仓库 `docs/research-evidence/` 内已审阅的
公开到期汇总。打包器核对当前研究源码／构建输入与验收 wheel 一致，复用已有
公开导出检查，保持受验 wheel 字节不变。`delivery.json` 列出两个独立 ZIP 的
SHA-256。相同验收 wheel、工具、说明和公开证据产生相同构建 ID 与 ZIP 字节；
重新编译可能改变 wheel 的 ZIP 元数据，须重新验收并保留新身份。

这次受监督预览不承诺 GUI、无人值守、盈利、实盘或完整官方模拟验收。
研究安装／离线合同检查、Windows SDK 元数据检查、Job 行为验证、真实供应商
订单与费用验收必须分别看证据。历史已安装 wheel 的测试不自动证明本包通过，
本地验证也不是新 GitHub CI 或 Release 发布。
