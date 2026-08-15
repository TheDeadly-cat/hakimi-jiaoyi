# 历史时点标的池与公司行动证据入口

更新时间：2026-08-03

## 目的

该入口只解决研究数据证据的导入、重建和本地索引，不改变 G41 策略语义，也不授予模拟盘或实盘权限。

当前 G41 需要覆盖：

- 研究窗口：`2024-07-05` 至 `2026-07-30`
- 基准：`SPY`
- 研究标的：`AAPL AMD AMZN ASML AVGO GOOGL META MSFT MU NVDA TSLA TSM WDC`
- 公司行动类型：`SPLIT DIVIDEND SUSPENSION DELISTING`

## 工作流

1. 从活动候选生成不完整的需求模板：

```powershell
python run_portfolio_reference_data_intake.py init --output runtime\reference_data\g41_reference_data_intake.json
```

2. 在模板旁放置真实来源文件，填写相对路径、真实 SHA-256、来源类别、发布时间、提取时间和来源 URL。

3. 验证并导入本地证据库：

```powershell
python run_portfolio_reference_data_intake.py import --manifest runtime\reference_data\g41_reference_data_intake.json
```

4. 查看本地索引：

```powershell
python run_portfolio_reference_data_intake.py status
```

SQLite 只保存证据包、标准化记录和来源元数据，不复制原始来源文件。每次导入都必须重新打开原始文件并重算哈希，因此原始文件缺失、路径逃逸、内容变化或重封后的记录替换都会阻断。

## 成员来源文件

成员来源文件必须是 UTF-8 JSON，结构如下：

```json
{
  "schema_version": "point-in-time-membership-source-v1",
  "records": [
    {
      "symbol": "AAPL",
      "effective_from": "2024-07-05",
      "effective_to": ""
    }
  ]
}
```

允许的来源类别只有：

- `EXCHANGE_LISTING_HISTORY`
- `OFFICIAL_INDEX_PROVIDER`
- `LICENSED_POINT_IN_TIME_VENDOR`

每条记录都必须绑定来源文件的真实哈希。发布时间不得晚于生效日，提取时间不得晚于证据包生成时间；重叠区间、标的缺失或研究窗口首尾无成员都会失败关闭。

## 公司行动来源文件

公司行动来源文件必须声明完整覆盖范围，即使某个标的在窗口内没有事件也必须出现在 `covered_symbols`：

```json
{
  "schema_version": "official-corporate-action-source-v1",
  "coverage_start": "2024-07-05",
  "coverage_end": "2026-07-30",
  "covered_symbols": ["AAPL", "SPY"],
  "coverage_types": ["SPLIT", "DIVIDEND", "SUSPENSION", "DELISTING"],
  "records": []
}
```

允许的来源类别只有：

- `OFFICIAL_EXCHANGE_FEED`
- `OFFICIAL_ISSUER_FEED`
- `REGULATORY_MASTER_DATA`

拆股和分红进入公司行动记录；停牌、熔断和退市进入证券生命周期记录。无法标准化的记录、窗口覆盖不足、来源观察时间晚于证据包生成时间或早于覆盖结束时间都会阻断整份来源。

## 安全边界

- 导入成功只表示内容完整性与合同语义通过，状态为 `REFERENCE_EVIDENCE_READY_FOR_MANUAL_REVIEW`。
- 来源身份、许可、存储权、限流和人工复核仍需单独完成。
- 不接受用户编辑 CSV 冒充权威来源。
- 不自动修改 G41 报告，不回填前向样本。
- `paper_authorized=false`，`live_order_allowed=false` 始终保持。
