# 原终端 0.7.0.dev1 r4：本机原生流程

2026-10-29，使用干净源码 `a53068b4c98668cb8257183c48765ab5ca330fcc` 的独立 `HakimiTrade.exe`，已在本机 Windows 窗口完成保存、运行、原图表复盘、正常退出、重开读取、重复启动和端口冲突检查。

## 交付身份

- 候选目录名：`HakimiTrade-0.7.0.dev1-candidate-r4`，ZIP 同名。
- Bundle：`3c59dcaeff6e7cad5843d05b11ed1e9538e1f5ef18b0ba518e389ba47e920c6c`。
- ZIP SHA256：`de1a7bab60059b6b4310bde0c7c00354a392e5cceedc04cb47def684944f383a`，192926042 字节。
- Manifest SHA256：`bfaec3795c49b60d95ca204bfb085f0f73e2ff39fe249286bc70c3eff97812d2`。
- [对应源码 CI run 148](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40820254226) 成功，11/11 作业。包构建使用上述干净源码；CI、包内探测和本机窗口操作各自保留证据。

## 实际用户行为

1. 从已有虚构双均线示例复制新任务 `r4 原生流程验证 20261029`。页面保留完整名称并显示“版本 1 已保存”；保存未计算。
2. 明确点击一次“运行这次回测”，请求绑定刚保存的任务版本。后台成功且页面显示“回测已完成，结果已保存”。
3. 打开原行情图表复盘：22 根封存日线、2 条已记录成交、TEST 虚构证券；图表标明冻结非实时，不重新计算历史结果。
4. 正常关闭，确认程序进程及本机 8765 监听均退出。重开同一入口，从结果列表读取同一份报告。
5. 重开和读取之后，41 个数据/操作文件逐字不变，无新增文件、回测或任务版本。此前 r3 的 25 个文件同样不变，两个 UNKNOWN 操作原样保留。
6. 重复打开同一 EXE，仍为原有同一个窗口。单独使用自建本机端口占用样例，程序显示冲突、未接入该服务；样例只收到一次 GET 健康探测，仍保持运行，未收到退出请求。随后正常关闭提示页并结束自建样例，确认候选进程和监听均不存在。
7. 实际操作后 9045 个清单内程序文件均无变化或缺失，唯一清单外文件为预期的 `terminal-manifest.json`，其哈希与构建证据一致。

新报告的底层运行编号为 `7b519a1de8dab29944f420135feb02d4cecf90b37cc1b89d4502a65d571381f0`，界面读取引用为 `d1a6ce8b508c26e457d655b0`；两者属于同一报告。示例收益 -1.03%、费用 3.92 USD 只证明合成流程能完成，不是股票或策略有效性证据。

## 范围

此次通过 Codex 的 Windows MSIX 启动环境操作，数据位于该启动环境映射的独立 `HakimiTradeTerminal` 工作区；不是原 Documents 数据或日常安装的数据迁移验收。原数据、旧 dev5 安装、失败 r1–r3、历史 UNKNOWN/T3 和历史 CI 均保留。

未实施干净新机、非管理员或独立新手试用；未开展真实券商、资金或付费模型操作。记录的是本任务未发起相关外部动作，不是全机抓包证明。r4 不包含后续正在整合的公开日线页面、策略候选因子解释和执行演练新界面。

完整原始凭据保存在本机 `Downloads/Hakimi-Astra-Delivery-20261029`，包括 `native-r4-before-new-task-r1.json`、`native-r4-before-close-r1.json`、`native-r4-replay-ui-r1.json`、`native-r4-reopened-result-ui-r1.json`、`native-r4-reopen-duplicate-r1.json`、`native-r4-occupied-port-r1.json`、`native-r4-program-files-after-r1.json` 与 `native-r4-conflict-window-closed-r1.json`。中间观察 `native-r4-acceptance-final-state-r1.json` 记录冲突提示页尚未关闭时的进程；最终关闭凭据单独追加，不改写中间事实。
