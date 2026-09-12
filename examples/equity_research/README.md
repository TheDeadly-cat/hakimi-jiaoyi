# 美股正股日线：合成输入示例

这里的 `TEST` 证券、OHLCV、证券身份和公司行为声明都是**虚构的软件夹具**，不是行情、真实事件、市场样本或收益证据。交易时段形状覆盖 2024-10-21 至 2024-12-03，共 44 个自然日、31 个常规交易日，包含周末、夏令时切换、感恩节休市和提前收市；这份日历仍被标记为合成输入，不能作为外部交易所证据。

`synthetic_daily.csv` 与 `synthetic_daily.manifest.json` 可直接交给 `build_equity_snapshot(csv_bytes, manifest_bytes)`。manifest 传入原始 bytes 时保存原始 JSON 字节；传入 dict 时保存规范 JSON，并用 `CANONICAL_JSON_FROM_OBJECT` 明确区分。股票快照独立使用 `us-equity-daily-snapshot-v1`，不更改已有 BTC 快照格式。

```python
from pathlib import Path
from hakimi_research.equity_dataset import build_equity_snapshot, save_equity_snapshot, load_equity_snapshot

folder = Path("examples/equity_research")
snapshot = build_equity_snapshot(
    (folder / "synthetic_daily.csv").read_bytes(),
    (folder / "synthetic_daily.manifest.json").read_bytes(),
)
saved = save_equity_snapshot(snapshot, "artifacts/equity-example")
assert load_equity_snapshot(saved).document == snapshot.document
```

CSV 必须严格使用 `session_date,open,high,low,close,volume` 六列；每个已声明开市日必须有且只有一行，顺序一致。价格仅接受未复权的正股 USD 价格，成交量单位是股。不填充周末、节假日、盘前、盘后或缺失交易日。索引输出为该日真实 UTC 常规开盘时间，同时独立保存实际收盘时间。高低价范围、有限正价格、非负成交量都经过检查。

导入 manifest 的顶层字段：

| 字段 | 契约 |
|---|---|
| `schema_version` | `us-equity-daily-import-v1` |
| `security` | 稳定 `security_id`、`symbol`、`exchange`（XNYS/XNAS）、`currency=USD`、`instrument_type=COMMON_STOCK` |
| `identity` | `stable_within_coverage`、`valid_from`、`valid_through`、`selection_basis`、`source`；不能把当今 ticker 当作永久证券身份 |
| `calendar` | `America/New_York`、首尾日期、来源及覆盖每个自然日的 `days`；开市日含 `open_utc`、`close_utc`、`early_close`，关闭日含明确原因 |
| `corporate_actions` | 首尾覆盖、`DECLARED_COMPLETE` 或 `UNKNOWN`、来源和 `actions`；空列表本身不建立覆盖 |
| `price_source` | 来源记录；其中 `raw_base64` 必须恰好绑定传入的 CSV 字节 |
| `price_basis` / `volume_unit` | `RAW_UNADJUSTED` / `shares` |
| `bar_timestamp_semantics` | `SESSION_DATE` |
| `completed_bars_only` | 严格为 `true` |
| `as_of` / `retrieved_at` | 有 `Z` 的 UTC 时间；实际抓取时间不得早于快照截止时间 |
| `bar_availability_lag_seconds` | 明确的正整数延迟假设，1 秒至 7 日；只有实际收盘加延迟不晚于 `as_of` 的完整日线可导入 |
| `evidence_kind` | `SYNTHETIC_TEST` 或 `IMPORTED_UNVERIFIED`，不允许自行填写已验证市场来源 |

每个 `source` 保存 `name`、`reference`（HTTPS 或 URN）、`retrieved_at`、非空 `raw_base64`。这些来源原文、声明、CSV、日历和归一化值全部进入快照身份；验证时重新解析原始 CSV 和 manifest，不能只修改汇总字段然后重新盖 hash。

日历逐日声明闭市，防止根据“有行情的日期”反过来生成预期交易日。程序核对美东 09:30 开盘、16:00 或明确提前收市的 13:00 收盘和夏令时偏移；是否真的是假日、某日是否实际提前收市，仍取决于导入的外部来源证据。源文件 hash 只确认一致性，没有提供数字签名或外部真实性认证。

公司行为事件字段为 `action_id`、`security_id`、`action_type`、`effective_date`、`source_reference`、`details`。它们原样保存；第一版只允许身份稳定、来源声明覆盖完整且窗口内没有公司行为的经济研究。窗口内拆股、分红、停牌、退市以及所有其他行动都得到 `research_admission.allowed=false`。未知覆盖、身份变更和身份覆盖不足同样阻止研究。导入动作保留证据，不等于允许交给引擎计算。合成数据即使 admitted，也只允许软件回归用途。

`bar_availability_lag_seconds` 是建模假设，不是伪造的历史采集日志。用今天下载的旧文件不能证明系统在历史时刻确实已经收到。后续事件研究应把公告首次公开、实际收到、解析完成和对应历史假设分别记录；股票日线观察完成后，还需等待下一交易日参考入场。

这份底座尚不实现公司行为记账、盘中行情、组合、历史股票池、券商接入或订单；所有执行权限保持关闭。

## 完整安装后示例

`example.spec.json` 固定绑定本目录两份原始输入，使用 25% 初始仓位的买入持有软件对照。不得修改规约里的 `snapshot_id` 来掩盖输入变化；本例必须在 `SYNTHETIC_REGRESSION` 用途下运行。

先使用已安装本版本普通 wheel 的 Python 环境。安装与依赖准备是独立步骤；下面的工具不安装包、不联网，也不会设置 `PYTHONPATH`。在仓库目录中可运行：

```powershell
python .\tools\run_equity_example.py `
  --examples-root .\examples `
  --ledger-script .\scripts\reconcile_research_ledger.py `
  --output-dir .\artifacts\equity-example
```

工具依次运行安装包的 `snapshot-import`、`research`、`replay`、`event-import` 和 `event-eligibility`，另外用独立标准库 Decimal 程序核对账本。每个子进程都使用隔离模式并清除 Python 路径覆盖；来源必须是非 editable 安装且构建收据验证通过。它会核对股票快照身份、完整重放、账本、事件首次完整观察日和严格晚于确认的参考入场时钟。任何一步失败均返回非零退出码。

也可以把工具、独立账本脚本和两个示例目录复制到仓库外，保持如下结构；不需要复制任何 `src/` 文件：

```text
copied-example/
  run_equity_example.py
  reconcile_research_ledger.py
  examples/
    equity_research/
      synthetic_daily.csv
      synthetic_daily.manifest.json
      example.spec.json
    equity_events/
      synthetic_earnings.txt
      synthetic_earnings.metadata.json
```

在任意当前目录，使用同一个已经安装 wheel 的 Python：

```powershell
python C:\copied-example\run_equity_example.py `
  --examples-root C:\copied-example\examples `
  --ledger-script C:\copied-example\reconcile_research_ledger.py `
  --output-dir C:\copied-example\results
```

输出目录包含完整快照、研究报告、重放收据、独立账本收据、事件原文条目、事件时钟报告，以及 `equity_example_<摘要>.json`。最后的摘要只保存相对产物路径、内容身份和核对结果，不包含本机绝对路径；完整运行报告可能另有本地机器收据，不应当作公开摘要直接发布。

固定事件示例的可用时间为 2024-11-29 18:07 UTC，观察日为 12 月 2 日，确认时间为当日 21:01 UTC，最早参考入场时间为 12 月 3 日 14:30 UTC。`--event-as-of` 默认是 `2024-11-29T18:08:00Z`，只检查当时可选择的事件版本及其日历推导，不声称未来价格当时已经收到。本例研究结果和事件时钟是两份独立软件检查，尚未把事件内容接成有收益证明的策略。
