# DeepSeek Code Worker

DeepSeek Code Worker 是本项目里的辅助开发工位。它的定位是生成草稿，而不是直接修改代码或接管交易系统。

## 分工

- DeepSeek：写基础代码草稿、整理说明、补测试草稿、提出重构计划。
- Codex：审查草稿、判断风险、修 bug、真正应用补丁、做最终验证。
- 交易系统：继续由本地风控和执行层控制，DeepSeek 不拥有下单权限。

## 安全边界

- 不自动应用 DeepSeek 生成的 patch。
- 不保存 API key、secret、password。
- 不允许关闭 `LIVE_TRADING_HARD_BLOCK`。
- 不允许新增真实实盘下单路径。
- 所有 DeepSeek 输出都会进入草稿队列，等待 Codex 审查。

## 本地接口

```text
GET /api/ai/deepseek/code-worker/drafts
GET /api/ai/deepseek/code-worker/run?mode=draft&task=...
GET /api/ai/deepseek/code-worker/archive?id=...
```

`mode` 支持：

- `draft`: 代码草稿
- `explain`: 解释整理
- `refactor_plan`: 重构计划
- `test_draft`: 测试草稿

草稿会保存到：

```text
runtime/deepseek_code_worker_drafts.json
```

这个文件只保存任务、摘要、风险标记、涉及文件、草稿 patch 和备注，不应包含任何密钥。

## 页面入口

交易终端底部的「DeepSeek 开发助手」面板可以提交任务、刷新草稿、归档草稿。

建议任务写法：

```text
给订单系统写一份 IOC/FOK 撮合测试草稿，不要改实盘逻辑。
```

```text
整理 strategy_lab 未来拆分为独立模块的重构计划，只输出文件清单和步骤。
```

```text
为风险硬墙写开发备注，说明为什么不能被 AI 或配置绕过。
```
