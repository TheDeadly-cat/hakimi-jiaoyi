# dev3 r4：可信包身份与同窗离线计划

本完整原终端候选从干净提交 `a235e8a2f1a303f72b99797105956bcd88cba399` 构建，已包含可信loader、离线计划服务、同窗计划UI、结果定位与本地截止时间显示。源码及隔离行为证据见[离线计划整合记录](../broker-plan-flow-20261030/README.md)；本目录只记录这一个新完整包的冻结检查、构建与验包，不沿用最小fixture或旧包的验收身份。

| 项目 | 实际身份 |
| --- | --- |
| 版本与入口 | `0.7.0.dev3 r4 / HakimiTrade.exe → /quant/` |
| bundle ID | `2a7b2ae2e703c105b64c8d2c90b2e2510486baf1c61ac5278f7df7387b18f227` |
| ZIP SHA256 | `2dd7045c8de3701fb892ed1c8fc5ac3370530b2510b3c5e8263b1d6a375f20c0` |
| manifest SHA256 | `a8cfa662966720fe8d46dbcdd966c08f359dc2af591168f8b8652c96be9d198a` |
| 文件与大小 | 9070程序文件；含manifest为9071 ZIP项；193140432字节 |
| 本机位置 | `Downloads/Hakimi-Astra-Delivery-20261029/HakimiTrade-0.7.0.dev3-candidate-r4` 及同名ZIP |

[完整交付身份](delivery-handoff.json)与[独立回执审查](independent-review.json)记录准确来源。一次冻结门禁全部通过：终端542/542、0跳过/失败/错误（183.825秒）；完整Node22桌面18.943秒；打包15项、candle与runner均通过。canonical测试安装绑定新冻结树，未用parent或旧候选源码代替。准确提交的[CI165](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40971259290)为11/11成功，[原始回执](ci165-completed-summary.json)保留；后续文档/源码提交接受独立CI。

## 三种包内检查分别记账

- **普通依赖探针**：[构建回执](final-candidate-build-result-dev3-r4.json)中的 `probe` 核对16个锁定依赖的安装版本，并本地导入所需运行模块（包含Futu SDK）；没有创建SDK context/client、连接/握手或读取账户行情。服务器模块导入不等于启动监听；此阶段经济运行和监听均为0。
- **身份专用探针**：[独立身份回执](final-candidate-broker-identity-dev3-r4.json)走真实bootstrap验证和initialize，在官方模拟/实盘候选两模式读取同一包身份。此子进程不导入SDK/server；283项SDK文件身份匹配，adapter为空，`runtime_compatibility=NOT_VERIFIED`，九项外部权限均为false。它不能替代普通依赖导入，也不证明SDK/OpenD兼容或账户授权。
- **完整页面与服务只读闭包**：[实际包内记录](final-candidate-feature-closure-dev3-r4.json)包含14个嵌入UI。两模式均通过capabilities、plans、单plan及原request四项服务读取：能力身份匹配、列表/请求列表为空、未记录身份如实返回NOT_RECORDED；数据库连接0、业务工作区创建0，未调用计划prepare/validate、未保存计划或订单。此检查没有启动HTTP服务或原生窗口；真实路由/写入行为的源码TEMP测试另在542项门禁中，不冒充包内原生实走。

构建另执行且仅执行一个全新TEMP中的SYNTHETIC_TEST例，原保存/明确运行/只读结果链通过，[经济探针原回执](final-candidate-private-execution-dev3-r4.json)保留。真实行情、旧研究回放、模型/provider及券商请求均为0。门禁自身的合成测试夹具与这一次构建探针分开解释，不把旧保存研究重跑作新证据。

唯一完整验包核对全部程序文件和ZIP各条目；[包核对回执](final-candidate-package-verification-dev3-r4.json)与[最终接受边界](final-candidate-acceptance-boundary-dev3-r4.json)均PASS。独立审查只核对回执、实际manifest身份及完整条目映射，没有重复probe、经济运行、整包哈希或ZIP解压。安装JS helper中的MSIX检查明确引用历史映射fixture的路径与SHA；[JS回执](final-candidate-installed-js-dev3-r4.json)不把它描述为本次原生观测。

## 用户范围与尚未验证部分

本包包含同窗离线准备能力：核对原候选/未发送意图及预算后明确保存计划，原请求只读找回，独立stop不排在慢准备任务后。PLAN_SAVED不是外部执行许可；停止不是撤单，未知结果不自动重试。九项外部权限仍关闭，实际adapter、wire预算profile、执行journal/worker和派发屏障、真实账户/证券/报价/费用证据及外部授权仍缺。不能直接运行SDK默认路径或将T29/T30升级为完成。

r4尚未启动原生Windows窗口；完整新包中的计划保存、关闭重开及真人流程仍待单独验收。独立无源码/新机环境和新手理解同样未验。用户停止Computer Use的约束仍生效；旧r2窗口按OPEN保留，没有推导FINAL_CLOSED，没有操作其API、端口、QA数据库或旧UNKNOWN/T3。旧r3与`97d0`最小fixture各自保持原身份；本候选未覆盖旧安装或发布正式Release。

## 证据完整性

本目录回执与日志是外部E原件的逐字副本，[来源清单](COPY_PROVENANCE.json)含路径、大小及SHA。`SHA256SUMS.txt`覆盖除自身外全部文件，`.gitattributes`保留原件字节。完整manifest与9071项哈希清单留在E，来源清单和独立review引用其路径/SHA；不复制runtime或业务数据库。外部未发布模板及所有旧证据未改。
