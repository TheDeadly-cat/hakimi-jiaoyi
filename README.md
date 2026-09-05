# Hakimi Jiaoyi

[当前构建、CI、研究证据与验收范围](CURRENT_STATUS.md)

本地、可安装、可重放的研究软件。正式 MVP 聚焦 **BTC-USDT 现货 / 1h / 现货与现金 / 固定参数 / CLI**。
固定快照经唯一的 `ExperimentRunner` 生成账本、指标和来源报告。
历史模拟不授予 paper、live、账户操作、下单或自动参数选择权限。

## 安装与输出目录

开发环境在仓库根目录安装精确依赖与 editable 包：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --requirement requirements.research.lock
python -m pip install --no-deps --editable .
hakimi-research capabilities
hakimi-research list-strategies
```

普通 wheel 可离开仓库安装运行；安装环境需支持 Python 3.11 以上，当前验证主版本为 Python 3.14：

```powershell
python -m pip install "setuptools>=77" wheel
python -m pip wheel . --no-deps --no-build-isolation --wheel-dir dist
python -m venv ..\hakimi-research-use\hakimi-env
..\hakimi-research-use\hakimi-env\Scripts\python.exe -m pip install .\dist\hakimi_research-0.2.1-py3-none-any.whl
Set-Location ..\hakimi-research-use
.\hakimi-env\Scripts\hakimi-research.exe capabilities
```

严格安装验收使用 `python tools/verify_wheel.py`：新目录构建、新环境非 editable 安装、仓库外运行全部根目录测试，移除 `PYTHONPATH` 并核验实际依赖/构建来源。
可用 `--wheelhouse <本地依赖轮子目录>` 离线验收。详见 [安装与来源证据](docs/research-packaging.md)。

以下示例使用已激活环境中的 `hakimi-research`。Windows `hakimi-research.ps1` 仅包装当前 Python 的模块入口，不修改 `PYTHONPATH`。
未指定 `--output-dir` 时，使用 `HAKIMI_RESEARCH_HOME`；该变量未配置时使用用户目录的 `.hakimi-research`。
快照、报告、重放回执分别写入 `datasets`、`reports`、`replays`。解析默认路径不创建目录，运行数据不写入安装包目录。

## 固定快照到报告

先导入本地采集 JSON，再绑定显式实验规约、运行研究、只读查看和离线重放：

```powershell
hakimi-research snapshot-import --capture .\capture.json --output-dir .\artifacts
hakimi-research research --snapshot .\artifacts\datasets\dataset_<snapshot_id>.json --spec .\experiment.json --output-dir .\artifacts
hakimi-research report-show --report .\artifacts\reports\research_<report_hash>.json
hakimi-research replay --snapshot .\artifacts\datasets\dataset_<snapshot_id>.json --report .\artifacts\reports\research_<report_hash>.json --output-dir .\artifacts
```

尖括号部分需替换为命令打印的完整路径/身份。`backtest` 与 `research` 调用同一个离线 runner，均要求 `--snapshot` 和 `--spec`；旧 `--config` Provider 流程被拒绝。
采集包保存原始响应字节、origin/endpoint、请求参数、获取时间和区间。导入、研究、查看及重放不会联网补数据、调用行情缓存或启动后台服务。

CSV 导入必须有明确来源、产品/周期/单位、UTC 区间和完成状态声明，不能只靠任意配置贴标签：

```powershell
hakimi-research snapshot-import --csv .\candles.csv --metadata .\csv-metadata.json --output-dir .\artifacts
```

修订时可传 `--predecessor <旧快照路径>` 建立版本关系。新数据产生新身份；已有快照和报告不覆盖。相同内容重试幂等，不同内容冲突报错。

## 实验规约

包内模板可在任何目录复制：

```powershell
python -c "from importlib.resources import files; from pathlib import Path; Path('experiment.json').write_bytes(files('hakimi_research').joinpath('resources', 'experiment.example.json').read_bytes())"
```

模板中的全零 `snapshot_id` 必须替换。显式设置：

- `score_start` / `score_end`：UTC `Z` 整点、左闭右开，位于快照区间内。
- 策略和固定参数：窗口决定所需上下文；Dual MA 20/60 至少需要评分前 62 行。预热不持仓、不成交、不收费。
- 初始资金、费率、滑点、风险：均为声明的研究假设；现货 MVP 杠杆固定为 1。
- `end_policy=MARK_TO_MARKET`：按最后评分收盘价计价，不虚构末尾平仓。
- `purpose`：描述性固定参数研究与合成回归明确区分，不将已查看样本改名为正式盲测。

报告区分成交与完整交易次数，显示现金/持仓、已实现/未实现损益、费用、风险请求值与生效值。
首期收益与回撤包含初始资金；短样本、零方差保留不可估计状态。定义见 [记账与风险语义](docs/accounting.md)。

## 显式公开数据采集

采集是独立源码工具，不由研究或重放调用。需要联网时，由用户明确执行固定公开 GET：

```powershell
python tools/collect_btc_snapshot.py --start 2026-08-01T00:00:00Z --end 2026-09-01T00:00:00Z --output-dir .\artifacts
```

仅请求 OKX BTC-USDT 现货 1h 历史蜡烛；不使用交易账户凭据、订单路由、回退缓存或自动重试。
每页请求、返回范围与格式受到检查，完整快照通过后才保存成功产物。
原始字节/哈希证明输入身份，不能单独证明行情事实或策略盈利。[MVP 计划](docs/research-mvp-plan.md) 记录首份描述性研究方案。

## 三类状态

| 维度 | 能说明什么 | 不能自动推导什么 |
| --- | --- | --- |
| 软件 | 安装、计算、重放和恢复是否通过相应验收 | 远端 CI 通过或桌面可发布 |
| 研究 | 来源、质量、样本限制和描述性结果 | 持续盈利、独立确认或参数选择许可 |
| 执行 | 永久 research-only，paper/live/order 关闭 | 软件或研究检查通过不会开启执行权限 |

报告分别保留 `input_integrity`、`environment_verified`、`source_identity`、`replay_verified` 和 `statistical_status`。
跨机器完整报告哈希可能不同，可比计算结果使用独立 `result_hash`。

## 能力与历史兼容

Python 在 [`capability_definition.py`](src/hakimi_research/capability_definition.py) 定义唯一能力目录；`tools/generate_product_capabilities.py` 生成 Node 消费的版本受控 JSON 投影，CI 以 `--check` 严格检查漂移。
[完整能力表](outputs/python_quant_bot/README.md) 包含新增快照导入、重放和只读报告能力；paper/live/optimization 仍 Archived，order entry 仍 Disabled。

Electron 与旧网页终端明确是 **Legacy Preview**，使用不同的旧研究模型，未纳入本次正式 CLI 首发或桌面验收，其结果不能与正式 runner 混用。
旧入口 `run_bot.py` 仅转发现有正式命令，旧 provider stack 已移除。见 [消费者与管理边界](docs/research-consumer-boundary.md)。

历史 [deterministic_experiment](outputs/python_quant_bot/examples/deterministic_experiment) 是合成身份样例。
集成版本的五类参考在独立、固定 commit 的 developer checkout 中重放，保留旧公式与旧哈希；不安装到正式 CLI，也不证明新核心与旧错误公式相同。

## 验证

CI 的当前核心、固定参考、历史参考重放、MVP、Electron、渲染器及 wheel 检查彼此独立。
总门禁只接受每个必要 Job 明确成功；失败、取消、意外跳过和缺失结果均失败。工作流不使用路径过滤。
Windows/Linux wheel matrix 已配置；没有实际运行证据的平台标记 NOT_RUN。远端 required checks 和确切 SHA 的 Actions 状态单独核对。
逐项覆盖及本地证据见 [交付审计](docs/research-delivery-audit.md)。
