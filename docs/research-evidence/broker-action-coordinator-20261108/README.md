# U12：单个操作的持久化执行协调器

这批工程把已有的共享账户账本、双停止屏障、受限传输和响应事实核验接成同一条执行路径，并在受控子进程内验证。默认入口仍拒绝派发；当前能够执行的依赖装配只接受明确的 `SYNTHETIC_TEST` 主机根和离线协议，不能用于外部账户。

这是 U12 的一个独立工程里程碑。T29、T30 和 U12 继续为 DOING，真实券商执行仍缺后续工程及单独明确授权。r6 程序包不包含本批源码。

## 变更及边界

- `terminal_broker_action_coordinator.py`：可信后端先绑定操作 ID、固定帧、原券商订单身份及有范围的许可。每个新 ACTION 确认持久化且不是重放后，才允许构造连接或写入。提交首先使用已有 journal 认领原意图与资金。
- 相同 ID 核对完整原始绑定后只读返回。CLAIM/ACTION 的提交回复丢失、已有认领但没有动作、写入或结束状态未知，都不会接着发送或自动重启。
- 每次实际非阻塞 connect/send 与本地及跨工作区账户停止屏障处于同一进程；每次短写重新核对许可范围、有效期、控制修订、帧哈希和偏移。响应等待和原帧落盘不占用停止屏障。
- 先保存实际发送数量为 UNKNOWN，再用原 UNKNOWN 证据引用写入严格核验的 typed ACK。收到响应不等于成交；撤单 ACK 不等于终态，不据此释放本金或费用预留。
- 原始帧、操作结果和最终回执共享硬字节上限；普通证据不能占用最终回执的预留空间。写入执行 flush/fsync，入账前重新核对磁盘原件。证据失效不能靠内存副本变成 ACK。
- `terminal_broker_worker_entrypoint.py`：有界 READY/INPUT/EVIDENCE/STOP/RESULT 协议。输入只能选择已绑定操作 ID，不能传入账户、帧、路径或授权。普通启动实际返回 DENIED；现有 `PackageWorkerSpec` 生产启动拒绝保持不变。

生产启动器、可信生产授权及研究资格、实际 socket、行情/证券/费用前置事实、完整核算和持仓归属证据、OpenD 兼容及 REAL/加密支持仍待实现。本批没有通过修改权限标记跳过这些缺口。受控子进程的测试 bootstrap 绑定已安装 canonical 包路径；它不构成生产包 bootstrap 验收。

## 验证

| 范围 | 结果 | 证据 |
|---|---|---|
| 新协调器用例 | 18 项；真实 SQLite、原服务配置、双停止屏障、受限传输及响应核验 | 纳入下方完整门禁；覆盖 ACK/取消、丢提交回复、过期及停止后只读、短写停止、原件变化、预算 |
| 新子进程用例 | 7/7，12.656 秒，0 跳过 | [定向原日志](worker-targeted-r2.log) |
| 完整终端门禁 | **848/848 PASS，0 跳过、错误或失败**；进程用时 184.416 秒 | [完整原日志](terminal-full-r2.log)、[身份与时间摘要](terminal-full-r2.json) |
| 代码及测试身份 | 六个输入在两次完整门禁前后保持相同字节 | [SHA256 输入清单](inputs-before-full-r1.json) |
| 测试环境修正 | 当前独立工作树的 editable 包绑定正确；隔离检查 2/2 | [环境说明](isolated-environment-r2.json)、[隔离检查](isolation-targeted-r2.log) |

完整门禁基线为 e9e46fc 上的 823 项，加本批 25 项，合计 848 项。定向与完整用例有重叠，不能相加为独立验证数量。

子进程验证实际覆盖：两个进程争用同一操作 ID 时只有一次连接；ACTION 提交回复丢失时没有连接工厂调用；第二个 worker 只读原 ID，账本字节和实际 IO 次数不增加；实际合成短写 10 字节后 worker 卡住，由独立 watchdog 结束，原 ACTION 保持未决且资金预留不释放，账户停止仍可发布。所有连接均为禁止真实网络的合成 WireConnection，protobuf-shaped 测试对象不代表实际 SDK/OpenD 兼容。

## 保留的失败与校准

1. 首轮子进程 bootstrap 在 `-I/-S` 下没有 canonical 包路径，启动报 `ModuleNotFoundError`。[原始 stderr](initial-child-import-failure.log) 保留。只修测试 bootstrap 的明确路径绑定，未更改隔离标志或生产准入。
2. 首次完整门禁为 847 PASS、1 FAIL：复用环境仍 editable 绑定原父工作树 P/src，旧隔离测试要求本次 W/src。[原日志](terminal-full-r1.log) 和[摘要](terminal-full-r1.json) 保留。随后创建新的测试环境，只读复用本地依赖，无网络安装 W；所有源码输入未变化，最终完整 848 项通过。
3. 测试环境首次安装因缺 setuptools 失败；原安装日志保留在本机外部证据目录，后续只补已存在的本地依赖搜索路径。协调器定向首轮唯一失败是把正确的零金额 `0.00000000` 误要求为字符串 `0`；修正为 Decimal 数值断言，未调整生产账本。

本批没有 SDK 上下文、OpenD、真实账户、真实网络请求、真实订单或模型调用。没有重放历史 UNKNOWN/T3。原父目录 P 与 r6 构建源 F 均保留干净 e9e46fc；本批验证与材料冻结时，源码位于独立 `codex/broker-action-coordinator-20261108` 分支，尚未提交、推送、打包或启用；后续提交与整合身份以 Git 历史为准。

完整文件与状态见[验证摘要](verification-summary.json)。本目录的字节清单见[SHA256SUMS](SHA256SUMS.txt)。
