# ADR-0001: 统一主产品能力边界与 legacy CLI 隔离（研究模式）

## 状态

已实施（窄切片；legacy engine 仍未成为主产品能力）

## 背景

当前仓库中同时存在多套入口与运行链路（`exchange_terminal`、Electron、`run_bot.py`、旧 Node 交易台、Python WebView）。方案 B 目标是优先收敛为可交付的研究基线，不新增交易功能，不启用实盘。

## 决策

1. **主产品边界**
    - 本阶段仅将 `outputs/python_quant_bot/exchange_terminal` 与 `outputs/hakimi_trade_electron` 作为主产品组合。
    - Electron 被视为正式桌面入口；`hakimi_trade_desktop.py`、Node 旧原型与其它 demo 仅作为历史/调试路径，不作为默认运行目标。

2. **能力模式**
    - 当前版本固定为 `research_only` 模式。
    - `research_only = true` 时，`paper` 与 `live` 均禁止，统一由后端返回能力合同字段与 Electron 校验入口一致。

3. **能力字段统一**
    - 在 `/api/health` 中返回 `runtime_build.capability` 与 `capability`：
        - `product_mode: research_only`
        - `research_only: true`
        - `paper_allowed: false`
        - `live_allowed: false`
        - `schema_version: capability-v1`
    - Electron 健康判定器必须以该字段为准，不再读取后端内部实现字段的历史歧义路径。

4. **legacy CLI 隔离**
    - `run_bot.py` 内的 `paper` / `optimize` 永久禁用，环境变量不能重新开启。
    - legacy CLI 可以保留查询/回测能力用于兼容，但禁止其成为默认 paper 交易路径。

5. **写入与幂等**
    - `/api/paper/*` 在研究模式下返回 `CAPABILITY_DISABLED`（保留只读快照 API 可用）。
    - `exchange_terminal` 的 JSON 写入改为原子化 + 备份恢复（`write_json` / `read_json`）。
    - 旧 `quant_bot` 的 `TradingEngine` 已出现“同一根 K 线唯一决策”整理，但完成 K 线证明、执行后持久化失败与异常重试语义仍未闭合；因此它保持 legacy、未授权，不能成为主产品 paper 路径。

6. **本机边界**
    - 服务器仅允许本机回环访问与端口动态匹配的 Origin；非本机来源直接拒绝。

## 影响

- Electron 与后端健康状态口径统一，不再出现“后端纸面授权但 Electron 判为 UNSAFE”的冲突。
- 旧 CLI 无法进入 paper/optimize 高风险路径，环境变量不能绕过。
- 研究链路可在重复请求场景更稳定，不会因重复同根 K 线导致重复决策。

## 未决项（后续 PR）

- 将方案 B 中的“数据 provenance 合同（`MarketDataEnvelope + source_manifest`）”从声明推进到 exchange_terminal 的统一市场数据返回结构；当前 dataclass 尚未接线，不能宣称已覆盖行情调用链。
- server 路由拆分与 `run_bot.py` 与 Electron 的逐步归档/退场计划。
- legacy engine 若未来需要继续保留，必须先封闭 completed-candle、执行与持久化原子性及失败重试合同；未经新 ADR 不激活。

## 日期

2026-08-21
