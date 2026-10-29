# dev3 r2：已有研究入口与订单因子候选

新候选从干净提交 `43c155a0a461edbefeaf98edba5418db560da5d5` 构建，包含完成卡片修复、候选策略查找已有研究、前置订单准备入口及保存参数/历史因子核对。旧 dev3 r1 与此前包完整保留。

| 项目 | 身份 |
| --- | --- |
| 版本与入口 | `0.7.0.dev3 r2 / HakimiTrade.exe` |
| bundle | `be331bd6bae86eb60fc1bc6a379fcb2bbae6e78d92653f01255724ea0fcaec76` |
| ZIP SHA256 | `2e1c0f7785b01299935807b9d854a19a11060fb04fc14a17be401a56efcd69bd` |
| manifest SHA256 | `6deef8cab4dc6102e44f9d3eb2fd7d55afa7b90ed58fb62a6fe9f6517a5d6486` |
| 文件 | 9066 程序文件，含 manifest 共 9067 ZIP 项 |
| 本机位置 | `Downloads/Hakimi-Astra-Delivery-20261029/HakimiTrade-0.7.0.dev3-candidate-r2` 及同名 ZIP |

一次冻结门禁、一次构建及一次完整验包均通过：终端 **464/464、0 跳过**，完整桌面检查、11 项打包检查、图表边界与门禁运行器检查通过。全部程序文件和 ZIP 条目逐项核对；包内解释器、依赖及实际完整 HTML 的 13 个 UI 脚本通过闭包检查。该功能提交的 [run 160](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40948746518) 已完成，11/11 作业成功。

构建仅执行 1 次新的临时 SYNTHETIC_TEST 研究，没有真实行情、旧研究回放、模型或券商请求。构建回执的 `native_app_started=false`、`T03_native_acceptance=NOT_PERFORMED` 如实保留；包内检查不证明原生窗口完成状态。r2 原生使用验收尚待新隔离工作区实走，旧 r1 的逐日模拟证据不能替代。

本目录 `delivery-handoff.json` 与 `ci160-completed-summary.json` 为本机回执逐字副本。完整日志、逐文件清单和构建/验包回执在同一本机交付目录中以 `dev3-r2` 区分。源码中下一步的纯文档更新不改签本包。
