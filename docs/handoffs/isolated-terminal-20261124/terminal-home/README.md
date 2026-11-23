# 原黑金交易台同屏源码交接

这些文件来自 2026 年 11 月 24 日隔离版的原桌面首页。自选、K 线、报价盘口和研究区共享同一个选中标的；研究区包含工具和期限比较、本地情景模拟、保存与重开。

| 文件 | 用途 |
| --- | --- |
| `terminal-market-pane.js`、`terminal-market-chart.css` | 自选标的、历史与主动读取的日线、图表缩放、涨跌口径 |
| `terminal-book-pane.js`、`terminal-book-pane.css` | 报价、最近成交、盘口深度与来源说明 |
| `option-futu-source.js`、`terminal-option-reference.js` | 核对期权报价的标的、到期和资料覆盖，再交给情景比较 |
| `terminal-research-pane.js`、`terminal-research-pane.css` | 在同一页面核对证据、比较工具和期限、操作模拟记录 |
| `terminal-market-desk.js`、`terminal-market-layout.css` | 把四个区域接入原首页，联动选择、记忆自选与调整栏宽 |
| `home-mount.fragment.html` | 展示原首页八个挂载元素以及它们所在的布局区域 |

以上十个 JS/CSS 文件中有九个直接复制。盘口模块原先内嵌两份本地富途报价存档；交接版本以空字典替代这两份数据，保留原来的缺资料状态、用户主动读取接口及渲染逻辑。HTML 片段只摘取本功能挂载点和外层布局关系。归档行情、账户与成交记录、个人偏好、第三方素材需由实际环境提供。

## 接入已有终端时的顺序

1. 保留终端基础样式，随后依次加载 `terminal-market-chart.css`、`terminal-book-pane.css`、`terminal-research-pane.css`、`terminal-market-layout.css`。原入口在用户选择行情页、本地模式开启且未进入冻结回放时，给 body 添加 `terminal-market-mode` 类。
2. 在原页面保留片段中的八个元素。将下列脚本按顺序放在原终端主脚本前：`terminal-market-pane.js`、`terminal-book-pane.js`、`option-futu-source.js`、`terminal-option-reference.js`、`terminal-research-pane.js`、`terminal-market-desk.js`。
3. 在原终端的本地启动流程里，从 `HakimiMarketDesk.initialSymbol()` 取首次标的。如果已有保存的选择会恢复它，否则返回 QQQ。研究回放有自己的入口与初始状态。原页面的控制器完成绑定后调用：

```js
window.HakimiMarketDesk?.mount({
  symbol: state.symbol,
  markets,
  onSelect: symbol => { if (symbol !== state.symbol) selectSymbol(symbol); },
  showMarket: () => setInterfaceView("trade", false)
});
```

4. 原终端更新 `state.symbol` 时接着调用 `window.HakimiMarketDesk?.select(symbol)`。选股行为会同步到图表、报价、期权和研究区。保存及重新打开研究记录依赖原应用同源的记录服务。
5. 行情来源依赖同源的 `/api/local/terminal-markets`、`/api/local/terminal-market`、`/api/studio/futu-history`、`/api/studio/futu-quote` 和 `/api/studio/futu-option-quotes`；研究资料、模拟以及记录读写依赖 `/api/workflow/` 下的接口。组件也可以从本机依法取得的归档读取历史行情或期权信息。期权代码中保留了当前研究版本支持的到期日，扩大范围时需要同时更新并核验源数据覆盖。

本目录是首页模块的源码交接。桌面启动器、完整后端、原终端主脚本和数据目录由隔离安装提供。这里的语法和合成样例核对不能代替合并集成后的桌面试用。
