# U12：受控本机 socket 与原后台链连接

本批补上可由可信后台显式注入的非阻塞 IPv4 loopback adapter。测试通过原 ActionCoordinator、SQLite journal、双停止屏障、ScopedTransport、typed response、worker entrypoint 和 supervisor，实际连接测试自身持有的 `127.0.0.1` 动态监听端口。默认 factory、独立 worker 和生产 PackageWorkerSpec 仍拒绝派发；U12 仍为部分完成。

本批验证源码基于 `708ec3f08abdeeae2578726b765483c8c109daa9`。六个输入及 SHA 见 [source-inputs.json](source-inputs.json)。验证时冻结的 r7 包不含本批源码，本批结果不替代 r7 或以后安装包的验收。

## 已确认行为

- 实际 connect/send 前，ACTION 已提交并独立读回，帧长度与哈希一致。adapter 每次只进行一次非阻塞 OS 尝试；短写的后续发送仍经过原 transport 的授权及双停止屏障，没有隐藏重试或重连。
- 真实分片响应能进入合成 typed ACK，同时保留资金占用，不能推断成交或最终费用。EOF、FIN、超时、错误序号及实际额外响应帧保持各自的 UNKNOWN/ACK 边界；完整帧后的 FIN 不抹掉已确认响应。
- 两个真实 worker 在原 ID 尚不存在时同步争同一个 `trade_connect`，由真实 SQLite 决定唯一 ACTION；只出现一次实际 accept，后续按原 ID 读取不再连接或改账。
- 明示注入 9 字节短写和 `after_write` 挂起后，真实 peer 在 worker 存活时收到前缀。原 watchdog 触发 4 秒 wall 期限并回收自有子进程，结果 UNKNOWN、一次启动且不重启；原 ACTION 无虚构 outcome，资金仍占用，再次读取不重发。停止请求在等待期间可发布。
- `ActionCoordinator.close()` 不写业务 journal。最终清理 UNKNOWN 不降级或删除已经持久化的 ACK；本批 close-reply-loss 用例的响应不完整，所以其业务结果本来就是 UNKNOWN。

## 验证与保留记录

| 记录 | 结果 | 说明 |
| --- | --- | --- |
| targeted-final-r1 | 51/51 | 原定向批次，完整保留 |
| additional-three-r1 | 2 通过 / 1 失败 | Windows 进程终止触发 reset，测试 peer 最初只在 FIN 时保存已读前缀 |
| additional-three-r2 | 3/3 | 仅修复 peer 在 reset 时保留已收到前缀并重新抛错，未改变生产逻辑或放宽时限 |
| targeted-final-r2 | 54/54 | 15 socket + 14 integration + 18 coordinator + 7 worker，零跳过，六输入前后一致 |
| fullgate-terminal-r1 | **877/877** | 一次完整 terminal runner，零失败、错误或跳过，260.371 秒，六输入前后一致 |

完整检查使用新建独立 venv；依赖从本地 wheelhouse 离线安装，setuptools 构建支持从本机现有安装只读复制，再实际 editable 安装当前工作树。运行前清空 PYTHONPATH，确认 canonical import 与 editable direct_url 都指向当前源码，pip check 通过，未安装 Futu SDK。见 [fullgate-preflight.json](fullgate-preflight.json) 及安装日志。这是完整 terminal 合同检查，不是已打包运行时或干净机器安装验收；本批未另跑 desktop/research 全套或 CI。

## 限制

短写、would-block、挂起和关闭回复失联均明确使用故障注入；不声称这些故障自然发生。关闭回复失联是在真实 fd 已关闭后抛出测试异常。响应及 protobuf 数据为合成测试依赖，未证明 Futu/OpenD 兼容、认证来源、实时价格/费用事实或真实账户授权。本批新增通信测试的实际网络均限于测试持有的本机监听端口，无 11111 探测、DNS、SDK/OpenD、外部地址、模型或市场请求。`peek` 只能判断当时可见的额外字节，不能保证未来不出现新的数据。

各原始日志、结果 JSON、环境证据及本说明的字节哈希见 [evidence-manifest.json](evidence-manifest.json)。原失败记录未覆盖。完整门禁由 `tools/run_terminal_contracts.py` 执行；父完整检查进程清空 PYTHONPATH，通过当前工作树的真实 editable 安装解析 canonical 包。受控 child 测试 bootstrap 仍显式导入已核对的安装路径，不代表生产包 bootstrap 验收。未跳过用例或重跑掩盖失败。
