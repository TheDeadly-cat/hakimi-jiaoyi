# v0.2.1 正式发布与下载验收（2026-09-09）

[GitHub Release v0.2.1](https://github.com/TheDeadly-cat/hakimi-jiaoyi/releases/tag/v0.2.1) 已于北京时间 2026-09-09 01:07:30 正式发布，为非草稿、非预发布版本。维护者在本轮明确授权合并三个 PR，并在 PR #1 合并版本验收后发布 v0.2.1。

## 固定来源

| 身份 | 实际值 |
|---|---|
| PR #1 合并与发布标签提交 | `45850899992361970043f2da70e785210025ae9e` |
| 合并后 CI | [34254213253](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/34254213253)，attempt 1，9 个实际 Job 全部成功 |
| 双平台构建 checkout / reviewed head | 均为上述 PR #1 合并提交，构建观察为 CLEAN |
| 0.2.1 运行源码摘要 | `48f1c48875b774ccf0af732c0b7089a5b7ff1ae3bac1dd68ee357fc40ef6ceb5` |
| Windows wheel SHA-256 | `c3c97c438ef03bcc94a200e829e356ca40a0e3799250bcb52dcddf6039e3dded` |
| Ubuntu wheel SHA-256 | `72b10f7dedfb5116169e0a6fd47155344900a229fd132a8ba7f535da59a7a07a` |

Release 固定在 PR #1 合并版本。PR #3 的运行记录及 PR #2 的 0.2.2 诊断、连续历史、只读视图属于后续主分支开发；主分支继续更新不移动 v0.2.1 标签，也不替换本次资产。

## 实际下载与执行

1. 下载合并后 CI 的 Windows / Ubuntu 两份已验收产物；逐项验证六文件清单、SHA256SUMS、构建和测试身份、36 个运行时文件、版本 0.2.1 与关闭的执行权限。
2. 将每个平台的原始六文件单独封装为 ZIP，创建 Release 草稿并上传；wheel 与元数据不重建、不改写。
3. 从 Release 草稿回下载两份 ZIP，与 Actions 下载件核对 ZIP 及内部所有文件摘要完全一致。下载的 Windows wheel 在全新虚拟环境、仓库外安装，全部 90 个实际测试 ID 与 CI 相同且通过，离线 CLI 研究和重放通过。
4. 补齐验收记录和外层校验和后正式发布。再次从正式 Release 下载全部四项资产，核对原上传件逐字节一致，GitHub 返回的资产摘要与下载字节一致，外层校验和全部通过。
5. 用正式下载的 Windows wheel 在另一全新仓库外虚拟环境再次安装；90 项相同测试、构建来源与依赖核验、禁止外连的 CLI 研究与重放均通过。没有 editable、PYTHONPATH 或系统 site-packages。

Windows 与 Ubuntu 的 90 项安装测试均由实际 CI 执行；本机下载后重新安装仅验证 Windows，不将其表述为本机执行过 Linux 安装。

## 持久证据

- [publication.json](publication.json)：正式发布时刻、固定标签目标、四项资产摘要与大小、Actions / 草稿 / 正式下载的一致性。
- [release-acceptance.json](release-acceptance.json)：发布前的 Release 草稿回下载及 Windows 安装验收；与同名 Release 资产逐字节相同。
- [published-download-verification.json](published-download-verification.json)：正式发布后的独立下载、双平台文件核验和 Windows 安装 / 90 项测试 / 离线研究重放。
- [SHA256SUMS.txt](SHA256SUMS.txt)：本目录三份 JSON 的原字节校验和。

每个平台 ZIP 内均包含确切 wheel、`wheel-acceptance.json`、`source-build-identity.json`、`dependencies.json`、`test-scope.json` 和 `SHA256SUMS.txt`。Release 另附发布前验收记录与外层校验和，脱离临时 Actions 保留期即可下载。

## 证据边界

原研究仍绑定 CI33969915599、checkout `a6771ec89603999d55c6193a4fa7846ec3115d40`、Windows wheel `b93952ddee0d16424292e75e5a3e7b0dfe10ac06d12f1333fa276922d08649fb`。本次运行源码未变，因此没有重跑 240 个研究单元，也没有将旧结果改写为本次 wheel 执行。

72 小时空仓参考观察已完成汇总：144 策略小时中 106 准时、14 迟到、24 缺失、0 失败，仍为 `WINDOW_ELAPSED_REVIEW_REQUIRED`。小时观察继续，软件发布不代表持续准时可靠性已通过。

正式范围为 BTC-USDT 现货 1h 离线研究 CLI；paper/live/order 权限仍关闭。软件交付完成不代表策略盈利、账户执行、GUI 发布或其他市场已验收。
