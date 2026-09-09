# 本地点时事件示例

这些文件是虚构证券 `SYNTHETIC:COMMON:TEST:2024` 的确定性夹具，**不是实际公告、真实采集回执或获利证据**。所有内容、时间和字段均用于工程验证，不访问示例 URL。

`synthetic_earnings.txt` 保存原文；`synthetic_earnings.metadata.json` 提供完整导入字段；`synthetic_sessions.json` 提供少量测试交易日。真实运行必须替换为已核验来源和真实采集记录，日历应绑定股票数据快照中的已核验日历，不能以这份夹具替代。

## API

```python
from pathlib import Path
from hakimi_research.documents import read_document
from hakimi_research.equity_events import (
    build_equity_event, verify_equity_event, save_equity_event,
    select_event_versions, event_session_eligibility,
)

example = Path("examples/equity_events")
event = build_equity_event(
    (example / "synthetic_earnings.txt").read_bytes(),
    read_document(example / "synthetic_earnings.metadata.json"),
)
verify_equity_event(event)
path = save_equity_event(event, "artifacts/equity-event-ledger")
selected = select_event_versions([event], "2024-11-29T18:07:00Z")
eligibility = event_session_eligibility(
    event, read_document(example / "synthetic_sessions.json")["sessions"], 60,
)
```

历史模式分别声明 60 秒采集延迟和 60 秒处理延迟，得到 `assumed_available_at=2024-11-29T18:07:00Z`。它与夹具中 2026 年的下载、提取时间分别保存，`received_at` 必须为 null。首个完整常规观察日为 12 月 2 日，确认时间为当日 21:01 UTC，最早参考入场为 12 月 3 日开盘。日历足够才返回 `READY`；此状态只表示时序具备条件，既不声称将来行情已收到，也不授权订单。

## 数据约束

- `OBSERVED` 使用真实下载、系统收到、提取完成时间，顺序为 `version_public_at <= retrieved_at <= received_at <= extraction_completed_at`。两个假设延迟必须为 null，信息可用时间命名为 `observed_available_at`。
- `HISTORICAL_RECONSTRUCTION` 必须保留实际下载与提取时间，使用分别大于零的整数延迟。今天下载旧公告不能伪装成历史收到时间。计算使用本版本的公开时间，不能借用第一版时间。
- 公开时钟 `ATTESTED` 表示调用方提供了核验方法和证据说明；程序没有认证其真实性。来源网站始终标记 `DECLARED_UNVERIFIED`，内容摘要只绑定字节。`UNKNOWN` 公布时钟可保存但不能进入点时选择。
- 原始 UTF-8 字节以 base64 和 SHA256 保存，完整文档另有内容摘要。数字用十进制字符串，另列 `scale`、币种、单位、财季和 GAAP 等口径；`value_text` 必须在所引原文中出现并对应同一个数字。证据可为精确引用或 `{start,end,quote}`，偏移量为解码后的 Unicode 字符位置、结束位置不包含在内。
- 程序校验引用和数字绑定，不声称自动理解了币种、量纲、财季或口径。`UNCERTAIN` 必须说明原因，`MISSING` 保留 null；未知一致预期不能填零。v1 不支持历史一致预期字段，相关事实必须标记为缺失，不计算“超预期”。
- `event_kind` 区分财报、指引、重大公司公告、宏观事件和事先公布的财报日程。8-K 是 `source.document_type`，不能作为“财报”的同义词；标记 8-K 财报时需明确 2.02 项。此分类约束本身不认证披露内容。
- `EARNINGS_SCHEDULE` 必须另列 `scheduled_release_at`，其日程版本也受点时选择约束。实际财报的发布时间不会自动变成提前已知的财报日程；日程事件不进入公告后价格确认 API。
- 修订版必须保留相同事件和证券身份，增加版本号并绑定上一版 `event_hash`，公开时间必须前进。读取选择要求提供从第一版开始的连续版本；同版本冲突、断链或倒置时间都会拒绝。未知时钟版可在下一版本补入首发时间，但新版本仍只能按自己的版本公开时间获得资格。
- 保存使用操作系统文件锁及排他创建，重复保存同一文档只返回原路径，不覆盖任何字节。锁文件会保留，进程退出会释放操作系统锁。损坏或冲突的既有条目会阻止追加，不能以重新保存来掩盖。

会话时序由传入日历决定：盘中才可用的事件不能观察当日“完整交易日”，盘后和周末顺延，提前收市使用实际收市时间。确认时间为观察日收市加声明的日线延迟，参考入场开盘必须严格晚于确认；缺少后续会话返回 `NOT_READY`。本模块不处理订单、收益、模型判断或真实数据采购。
