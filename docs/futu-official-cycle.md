# 一次官方模拟订单验收

入口为 `tools/futu_simulation_cycle.py`，复用现有适配器和SQLite状态机，不进入研究wheel或桌面启动流程。当前仅可执行真实只读准备；**尚未获得官方模拟下单授权，未发送订单**。

冻结的首个工程验收提案为：已核对的US模拟账户、`US.AMD`、BUY 1股、限价1.00美元、普通限价DAY/RTH、禁止自动调价或换意图重试。最多一次SDK提交、一次对同一订单的撤销。这个远离当前价格的限价单用于验证订单接入与撤销，不用于盈利研究；供应商可能拒绝，拒绝时保留实际结果，不改价制造成功。若意外成交，保留持仓并停止；本提案不授权额外卖出。

1美元为订单名义金额上限。3美元仅为本地预留参数，不代表真实费用或保证的总费用上限。模拟费用与成交接口不可用，仍须取得实际模拟账单/导出原件并由维护者核对；没有原件时继续标记会计未核实，不能填零。没有真实资金或REAL操作权限。

## 分阶段执行

每次CLI调用都通过已有Windows Job启动一个新进程，180秒执行上限、128KiB输出上限、5秒清理预算。SDK日志及全部账户信息只存私有输出目录。阶段之间不自动续跑、不注册任务、不改变现有观察窗口。发布时先从固定Git提交导出原始字节；准备阶段把四个执行文件的摘要写入数据库，后续代码变化会停止操作。

| 阶段 | 实际行为 | 仍不能证明什么 |
|---|---|---|
| `prepare` | 两轮真实账户读取、证券规则读取；创建新私有数据库并冻结意图，输出待授权提案 | 不生成授权、不领取提交机会 |
| `submit` | 要求单独授权文件；重新读取账户/证券/容量；持久化可能提交，再至多调用一次SDK | 返回未知不代表未提交 |
| `recover` | 新进程打开同一数据库，只查询并处理回调、保留订单身份，尝试对账 | 多次读取不是原子快照；缺失费用不补零 |
| `duplicate-probe` | 在已有持久化尝试后调用既有领取逻辑，必须拒绝重复领取；不创建SDK连接 | 不测试券商去重，也不再次发送订单 |
| `cancel` | 要求同一意图授权文件；只撤销数据库绑定的订单ID，核验返回环境/订单ID并保存原响应 | 撤单响应不是终态 |
| `admit-statement` | 保存维护者提供的实际原件，校验摘要/订单/数量后复用已有账本 | 摘要不认证原件真实性；仍须再次`recover`核对实际余额和持仓 |

`submit`有意忽略同步响应的状态推进并结束进程，用于明确标记的客户端响应丢失演练；真实同步原件仍保留在私有数据库。若回调先到，其原件与订单身份照实保留，不伪称发生了供应商网络故障。下一进程先查询恢复，只有识别到对应订单后才能申请撤销。

每个输出目录必须全新，数据库保持同一物理位置。重复`prepare`不会覆盖已有数据库。跨进程账户权威继续使用已有持久登记；维护者须保证本次验收期间没有其他程序或手工操作同一模拟账户。跨机器独占不由本机锁证明。

初始账户可能已有非AMD持仓，包括较长的期权代码。这些代码和账户原始数量仅作为对账初值保留，不转换为标的股票股数，不新增可交易价格规则或处置权限；未来读取发生数量或现金差异仍会停止。首轮真实准备因原有代码长度限制停止，12次只读请求成功、SDK订单调用为零，原失败回执保留。

示意命令（占位文件均在本机，不提交账号或授权到GitHub）：

```text
python tools/futu_simulation_cycle.py prepare --profile <private-profile.json> --database <cycle.sqlite> --output-dir <new-prepare-dir>
python tools/futu_simulation_cycle.py submit --database <cycle.sqlite> --authorization <approved-private-authorization.json> --output-dir <new-submit-dir>
python tools/futu_simulation_cycle.py recover --database <cycle.sqlite> --output-dir <new-recover-dir>
python tools/futu_simulation_cycle.py duplicate-probe --database <cycle.sqlite> --output-dir <new-duplicate-dir>
python tools/futu_simulation_cycle.py cancel --database <cycle.sqlite> --authorization <approved-private-authorization.json> --output-dir <new-cancel-dir>
```

授权必须由维护者单独批准，再绑定实际账户、此意图与载荷摘要、明确到期时间以及允许的提交/撤单操作。运行时剩余有效期不得超过24小时；查询后和调用SDK前仍会重验。限价、数量、意图和源文件不能在授权后暗改。闭市、账号不符、现金不足或来源变化均停止。

## 完成标准

必须检查真实提交/查询/回调原件、撤销或成交终态、同期实际现金和持仓、独立实际费用/结算原件，以及新进程恢复和重复领取拒绝记录。各阶段回执默认不宣称完整周期通过，SDK调用次数也不等于券商已经接单。最终验收须逐项核对这些原件；本地夹具、绿色CI、一个成功返回或未发生异常均不能替代。
