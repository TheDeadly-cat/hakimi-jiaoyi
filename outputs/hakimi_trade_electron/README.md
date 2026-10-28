# 哈基米交易 v2 Electron 桌面壳

这是原程序的 Electron 源码入口；当前整合候选保留行情、策略分析、量化任务、旧结果与记录导出。
本次源码整合不改变已安装的 dev5 试用包；`tools/build_windows_trial.py` 打包的是另一条
`trial-main.js` / `workbench_server` 入口，不能用旧包验收代替本入口的验证。
正式入口是安装后的 `hakimi-research snapshot-import / research / replay / report-show`。
桌面仍承载旧终端及其 `signal-close-next-open-ohlc-conservative-v3` 核心；
其结果不能冒充正式 `ExperimentRunner` 报告或与其混合比较。

桌面启动的旧运行层强制 `HAKIMI_RUNTIME_READ_ONLY=1`，不自动启动 FutuOpenD，
移除了 Futu 管理菜单。量化工作区单独使用 `HAKIMI_QUANT_READ_ONLY`：桌面默认为 `0`，
允许明确保存新任务和运行研究；直接运行 Python 时默认跟随旧运行层的只读状态。
旧任务/结果仍按原身份读取，只有明确运行操作才计算，paper/live/order 仍封存。
已有后台必须通过严格健康检查且 `local_only` 与桌面模式一致；不匹配时保留原进程并拒绝复用。
9 个原策略允许新研究；趋势回调、波动挤压突破禁止新研究，网格、马丁、反马丁仍锁定。
下列历史功能清单用于识别原界面，已归档功能以当前能力目录为准，不构成正式发布验收声明。

只读导出默认写入用户下载目录 `Hakimi-Exports`，可用 `HAKIMI_EXPORT_DIR` 指定原数据目录之外的位置。
CSV 及请求去重记录都留在导出目录；读取原订单、事件和账户时不会创建源数据库的 WAL/SHM。
已有 AI 配置可由明确的 `HAKIMI_LOAD_LOCAL_AI_ENV=1` 读取忽略文件 `.env.local`；
在旧运行层只读时还需 `HAKIMI_LOAD_LOCAL_AI_ENV_IN_READ_ONLY=1`（桌面显式设置）。
白名单同时支持 DeepSeek 和 OpenAI，已有进程配置优先；`HAKIMI_AI_ENV_FILE` 可指定已有配置文件。
本地模式、测试模式或显式跳过配置均不读取文件。不要提交或打印密钥；加载配置不会调用模型。
`HAKIMI_LOCAL_ONLY=1` 时页面与后台共同阻止外部模型分析。

产品能力由 `src/hakimi_research/capability_definition.py` 定义，生成
`src/hakimi_research/contracts/product-capabilities.json` 投影供 Electron 读取。
Electron 对 `product-capability-catalog-v2` 和永久 research-only 权限做独立、
严格、失败关闭的校验；目录缺失或任何 paper/live/order 权限升级都不会被视为健康。

- 自动检查 `http://127.0.0.1:8765/api/health`
- 如果后台未启动，自动拉起 `outputs/python_quant_bot/exchange_terminal/server.py`
- 后台就绪后加载 `http://127.0.0.1:8765/`
- 不自动启动本机 `FutuOpenD.exe`
- 只允许一个哈基米交易窗口运行
- 记住窗口大小、位置和最大化状态
- 托盘常驻，可快速显示窗口、回到交易台、打开富途配置、重启后台
- 顶部桌面控制台提供模拟/观察/实盘锁模式、行情源切换、手动刷新和富途入口
- 命令面板支持市场、模块和动作分组，可快速跳转
- 新增软件标题栏、工作区导航和策略指挥条，便于把交易台、策略、订单和账户作为桌面软件工作区使用
- 策略作战室 v2 增加策略画像、交易锚点、禁交易条件和执行解释日志，用于解释为什么买、为什么不买、为什么卖
- 策略参数模板提供保守/标准/进攻配置，一键同步杠杆、仓位、止盈止损、移动止盈止损和委托模型
- 回测寻优支持当前标的，BTC 优先读取本地日线库，股票优先读取富途日线，并输出均衡最优、低回撤、高收益和分段表现
- v2 控制中心新增数据可靠性体检；策略市场新增机器人档案，用于查看数据源状态、策略可启动性和机器人执行优先级
- 数据可靠性中心新增通用历史缓存队列，缓存文件位于 `outputs/python_quant_bot/runtime/market_history_cache.sqlite`，用于补全 ETH/DOGE/永续合约日线
- BTC 日线源现在优先读取 `outputs/python_quant_bot/runtime/jiaoyiguowangshuju`，`Z:\jiaoyiguowangshuju` 仅作为备用来源。
- 股票观察新增富途增强面板，读取 FutuOpenD 的市场快照、扩展时段、盘口深度、逐笔成交、资金流和资金分布；实盘交易仍保持硬锁。
- 历史补全队列现在会记录 OKX history、OKX candles 和备用 K 线源的尝试结果，便于定位网络或数据源问题。
- v2 交易区改成更接近富途式工作台：主图缩小一档，右侧加宽并新增波动/资金/资讯/AI 作战栏；图表右上角工具按行情、指标、画线、AI/回放分类弹出。
- 行情图形采用中文交易习惯：红涨绿跌；系统在线/异常状态仍保留原有状态色，避免混淆。

## 启动

从项目根目录双击：

```bat
outputs\Hakimi_Trade_V2_Electron_START.bat
```

或在当前目录运行：

```powershell
npm.cmd install
npm.cmd start
```

## 自检

仅未打包的开发构建允许用调试端口跑自动检查；监听限定为 loopback，
不设置通配来源。发布构建忽略该变量并移除相关调试开关，也关闭开发者工具：

```powershell
$env:HAKIMI_DEBUG_PORT="9333"
npm.cmd start
```

另开一个命令窗口运行：

```powershell
npm.cmd run smoke
```

自检会确认桌面窗口已加载交易台、顶部控制台存在、实盘锁仍有效、命令面板可打开，并检查基础状态文本。

## 设计边界

当前版本负责桌面包装、启动管理和窗口体验。交易逻辑、富途接入、OKX 行情、策略和风控仍在 Python 后台中。

真实交易与 paper 执行持续阻断；默认只读。
导航只允许当前本机 HTTP origin 和固定 boot 文件；外链只允许无凭据的 HTTPS。
新窗口在已受保护的当前窗口内处理，不创建不受导航规则约束的子窗口。
管理路由清单及退出首发注册表的范围见 `../../docs/research-consumer-boundary.md`。

关闭窗口或退出前，自有后台通过私有 token 协商退出。研究仍忙、响应未知或尚未退出时保留窗口；
只有确认后台正常退出后才结束桌面。附着到其他入口的后台不会被关闭，不按端口结束进程。

## 后续升级

- 加安装包：引入 `electron-builder`
- 加自动更新：拆分 release 通道
- 加本机配置中心：端口、FutuOpenD 路径、主题、启动模块
- 加崩溃恢复：后台异常时自动重启并提示
- 加窗口内原生标题栏：账户状态、Futu/OKX 连接状态、快捷入口
