# 原终端 dev3 r1：干净构建与包内验证

候选已从干净提交 `500d69105ff3f33e95c8d35cbef6da9704ca8c2f` 构建。原终端同窗包含九策略因子说明、本地订单演练、逐日历史模拟、券商候选准备及旧工作区物理位置发现。后续源码变更不自动进入这份包。

| 项目 | 身份 |
| --- | --- |
| 版本 | `0.7.0.dev3`，未签名候选 r1 |
| 入口 | `HakimiTrade-0.7.0.dev3-candidate-r1/HakimiTrade.exe` |
| bundle ID | `c0792eda05fccd08ca7c969b6ab6aacc9f14056b67220657b65232d54c50c7b1` |
| ZIP SHA256 | `885f7e0ed01295954a1614062897b483c17e7d64e75fd883c6de32dbbd49685d` |
| ZIP 大小 | 193093509 字节 |
| manifest SHA256 | `20f9c01fab52a254b4f7fc26da38318ffa2fa4a925db48176fce3f8f30a93458` |
| 程序 / ZIP 清单 | 9066 个程序文件，含 manifest 共 9067 个 ZIP 项 |

本机交付位置为 `Downloads/Hakimi-Astra-Delivery-20261029` 下同名目录及 `.zip`，旧 dev1/dev2/原 Documents 程序和数据均保留。

冻结源终端门禁 **464/464 PASS、0 跳过**；完整桌面检查、11 项打包检查、图表完成日线边界与门禁运行器检查均通过。冻结检查使用独立绑定该源码的 Python 环境及已缓存 Node 22.23.4/Playwright，没有下载依赖或修改全局环境。

完整程序清单和 ZIP 每一项的文件名、数量与字节哈希一致；源文件和组件构建凭据一致。包内私有 Python 的模块均来自候选包，16 个锁定依赖一致；完整 HTML 装配包括新的逐日模拟与券商候选脚本，空工作区读取不创建业务目录。独立首用说明与源模板字节一致。Windows 物理路径与诊断资源检查通过。

构建仅明确执行 **1 次新建 SYNTHETIC_TEST 样例研究**，保存与回读不计算；真实行情研究、旧研究回放、来源/模型/券商请求均为 0。此为包内运行验证，不是原生 GUI 或策略效果验收。

本机凭据：`stage-c-frozen-gates-summary-dev3-r1.json`、`final-candidate-build-invocation-dev3-r1.json`、`final-candidate-build-result-dev3-r1.json`、`final-candidate-package-verification-dev3-r1.json`、`final-candidate-feature-closure-dev3-r1.json`、`final-candidate-acceptance-boundary-dev3-r1.json`、`final-candidate-SHA256SUMS-dev3-r1.txt`。完整验收边界记录当前 `native_app_started=false`、`source_repository_inaccessible_guest_test=false`；后续原生操作必须另存记录，不回写这些构建回执。

真实 TSLA 公司行为补证、独立无源码环境与真人试用仍按各自待完成项记录。券商候选只保存未发送意图，外部权限未开启。PR #26 保持 Draft，未合并或发布 Release。

构建后本机原生逐日模拟、关闭重开、核对恢复与旧结果读取已完成，见[单独原生证据](../terminal-070dev3-native-20261030/README.md)。其中发现的保存卡片反馈问题已在后续源码修复，尚未进入此包；不改写上述构建时回执。
