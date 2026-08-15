# 官方参考数据来源评估

更新时间：2026-08-03

## 结论

G41 可以继续作为“带已知限制的内部研究样本”，但不能仅靠当前 13 只股票补一张上市日期表就宣称消除了幸存者偏差。历史时点标的池必须同时满足：

1. 使用研究当时已经公开或可取得的上市、退市、停牌和公司行动资料。
2. 使用事前定义、可机械重建的选择规则，而不是先看见今天的赢家再回看历史。
3. 覆盖窗口开始日的完整基线，以及窗口内全部新增、删除、代码变化和退市。
4. 保留许可、存储权、限流、提取时间、原始文件哈希和修订记录。

因此，G42 应使用新的数据协议；不得直接修改或补写 G41 研究报告。

## 美股来源

### Nasdaq Daily List

推荐级别：首选，需订阅与审批。

- Nasdaq 官方说明该产品包含新上市、退市、名称与代码变化、现金分红、股票分红和拆股。
- 官方说明历史公司行动可追溯到 1999 年。
- 当前月份文件通过安全 FTP 或网站提供。
- 使用前需要提交数据请求和相关协议；含 CUSIP 的版本还涉及额外许可。

来源：[Nasdaq Daily List 产品说明](https://www.nasdaqtrader.com/trader.aspx/Trader.aspx?id=DailyListPD)

适配目标：

- `EXCHANGE_LISTING_HISTORY`
- `OFFICIAL_EXCHANGE_FEED`
- 上市/退市区间、代码变化、拆股、分红

### NYSE Market Event Feed 与 Corporate Actions

推荐级别：首选，需购买与审批。

- NYSE Market Event Feed 提供实时和历史公司行动 API，可按事件、日期和标的查询。
- Corporate Actions 产品覆盖 NYSE、NYSE American、NYSE Arca 和 NYSE Texas，并包含新上市、停牌、退市、拆股和分红等事件。
- 官方规范提供稳定事件 ID、公告日、除权日、登记日、支付日以及取消/修订字段，适合建立修订账本。

来源：[NYSE Market Event Feed](https://www.nyse.com/market-data/corporate-actions/market-event-feed)、[NYSE Corporate Actions](https://www.nyse.com/market-data/corporate-actions)、[NYSE Client Specification](https://www.nyse.com/publicdocs/nyse/data/NYSE_CorporateActions_Client_Specification.v3.2a.pdf)

适配目标：

- `EXCHANGE_LISTING_HISTORY`
- `OFFICIAL_EXCHANGE_FEED`
- NYSE Group 上市证券、ETF 与 ADR 的历史状态和公司行动

### SEC EDGAR

推荐级别：免费交叉核验，不作为唯一主数据。

- `data.sec.gov` 无需 API key，可提供申报历史、当前/曾用名称、交易所与代码元数据，以及夜间更新的批量文件。
- EDGAR 的核心是公司申报和 XBRL 财务事实，不是覆盖所有交易所事件的证券主数据或公司行动主表。

来源：[SEC EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)

适配目标：

- 发行人身份、CIK、名称变化、公告与财报交叉核验
- 不单独满足 `OFFICIAL_CORPORATE_ACTION_MASTER`

## 港股来源

### HKEX Data Marketplace

推荐级别：首选，需确认具体产品、价格和许可。

- HKEX 将 Data Marketplace 描述为直接来自交易所的历史和参考数据入口。
- `Securities Attribute Daily Files` 提供主板和 GEM 的每日静态证券属性，适合建立每日在市基线。
- 平台支持指定历史区间、订阅、直接下载、SFTP 和云传输；产品页分别列出用途、许可和技术细节。

来源：[HKEX Data Marketplace](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services/HKEX-Data-Marketplace?sc_lang=en)、[用户指南](https://www.hkex.com.hk/Services/Market-Data-Services/Historical-Data-Services/-/media/08660B4BD3874369BAFF9CE983ED98FD.ashx)

适配目标：

- `EXCHANGE_LISTING_HISTORY`
- 每日证券状态、上市/退市区间、代码和属性变化

### HKEXnews 与发行人公告

推荐级别：事件交叉核验，需建立结构化解析和人工复核。

- HKEX 的发行人新闻覆盖重组、分红、股本变化和其他上市公司公告。
- 公告适合证明具体事件，但不能简单等同于完整的全市场零事件覆盖主表。

来源：[HKEX Market Data Services 概览](https://www.hkex.com.hk/Services/Market-Data-Services/Real-Time-Data-Services/Overview?sc_lang=en)

## G42 标的池选择

建议分成两条，不混为一谈：

### 历史内部回测

使用全市场或足够宽的交易所历史基线，再应用只依赖当时可得数据的机械规则，例如：

- 指定交易所和证券类型
- 最低上市时间
- 过去 N 日成交额
- 价格与缺失率门槛
- 排除停牌、退市和无法取得完整公司行动的标的

行业、主题、历史市值或指数成员过滤只有在取得对应的时点化数据后才能加入。

### 当前关注池的前向研究

当前美股科技、半导体、存储与港股电力关注池可在声明日之后做前向观察，但不能把 2026 年声明的名单倒推成 2024 年已知的无偏标的池。

## 决策顺序

1. 内部回测继续使用 G41，并在报告中保留 `survivorship_bias_status=UNCONTROLLED`。
2. 不自动购买数据，也不抓取需要协议的受限文件。
3. 先向 Nasdaq、NYSE 与 HKEX 获取样本、报价、存储权和内部研究许可。
4. 确认实际文件后再实现三个解析适配器，避免按网页说明猜测生产字段。
5. 导入器通过、许可复核通过、选择规则冻结后，再预注册 G42。

任何来源接入都只进入研究和回测数据层，不改变 `paper_authorized=false` 与 `live_order_allowed=false`。
