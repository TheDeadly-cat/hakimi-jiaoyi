# 实际 pinned protobuf：55 项离线事实投影检查

首次执行结果为 **PASS_ACTUAL_PINNED_PROTOBUF_SYNTHETIC_RESPONSE_FACTS**：7 个 action、55 个检查；runner 记录的子进程段耗时 **1.108 秒**、exit0、stderr空。这里只读核对现成回执与脚本，没有重新运行探针或扫描整个包。该 55 检查仍是独立探针，不等于 709 项完整门禁或 SDK/OpenD/实盘验收；root 随后已独立完成 709/709、15 包装、4 runner PASS，具体原件见 E/broker-response-worker-integrated-20261030-r1/summary.json。

## 实际使用与未证明的内容

解释器来自未修改的 `a235e8a2 / 0.7.0.dev3 candidate-r4`，真实启动参数为 `-I -S -B -X utf8`。锁定 wheel SHA256：`a3bc7609fc7b60c0ca3cd2971bc8b81819338d3c88ad25d1bd3f647d781554b5`；原包 manifest SHA256：`a8cfa662966720fe8d46dbcdd966c08f359dc2af591168f8b8652c96be9d198a`。

探针对锁定包内 **真实 protobuf Request/Response 类**使用明确的 `hakimi_probe_pb` 命名空间，经逐文件核验的 source loader 执行原 pb2 字节，没有导入 `futu` 顶层包或 context。7 个动作是 submit、cancel、observe、accounts、funds、positions、fees。账户、会话 ID、证券、成交、金额、费用和时间均为人为 **synthetic bytes**；ACTION 是显式自封合成回执，**没有 journal 数据库来源、真实订单或外部认证**。本探针使用预置虚构会话身份，不宣称完成真实握手链。

当前 parent 基线为 `6581c5926d5283a0b3916041b2292dcc1b1031d5`，调用回执明确记录其未提交改动和具体源码 hash；包内 runtime 与新的 parent facts 源码分别绑定，不把覆盖加载的 source 当作已安装服务。完整 original frame 与每个案例见 `run/response-cases.json`。

55 检查覆盖匹配响应、API error 不当明确拒单、错账户/环境/市场/订单、缺失或重复行、缺字段与真实 0 的区别、缺必填 retType、错 serial，以及过期后只读保留事实。终态 status 不自动证明费用最终或精确经济事实；`facts_authenticated=false`、`production_transport_available=false`、九权限 false。

## Guard 与身份核对

- `guard-final.json` 的 55 completed_checks 与 `probe-result.json` 完全相同，exception=null。
- socket、database、subprocess、thread、futu_import 尝试均 **0**；hostname读取、SDK context、数据库连接和business run也均 **0**。
- `futu` 顶层 import 被显式 finder 拒绝；socket/DNS、SQLite、subprocess、线程启动有拒绝钩子；只允许新输出目录写入。没有放宽真实连接权限。
- `source_hashes_unchanged=true`、`manifest_unchanged=true`；实际核验加载文件/容器及 parent source清单 **205** 项在两个回执中一致。这里没有重新验证这些 205 文件，只核对原始结果一致性。
- 调用回执另记前置私有 runtime 核验 7962 项；此为原 runner 的前置范围，不能把上述 1.108 秒称为整包扫描总时间。
- 最终 child/runner 当前 SHA 与 invocation 的期望 SHA 一致。`RESULT/ACK` 来源投影仍非外部经济认证、权限授予或真实发单成功。

## run 目录全部原文件 SHA256

以下 7 文件均为原执行产物，本交接没有修改它们：

| 原文件 | bytes | SHA256 |
| --- | ---: | --- |
| `guard-final.json` | 49700 | `486b72c288391870e0bedec2d8d5e61f1a75aac9c19e7006869e6db5c0f9af69` |
| `invocation.json` | 9573 | `4eeffa7f751b165173d89ba3902199d1f1ac93147e2135d12964827dbdb4da62` |
| `probe-result.json` | 54836 | `ee431711cab29500a03c4d2384a5131f05e88cf1c49b1e7b646116d945cbb4dd` |
| `response-cases.json` | 173004 | `65e88e6fdbb5235c28fad5f90781077b7b7ff30893c49a775bd19bc754c12203` |
| `runner-result.json` | 697 | `4906b20f305ebce02044dd16e8b1c7b0f3085d552b64742282db65fe6ac21835` |
| `stderr.log` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `stdout.log` | 186 | `3a5476b38b9c2db3f13fb683ddf5a0c60eeb4d0e86c1810e0dba5a1eb6f603a1` |

脚本原件（同样未改）：

- `probe-child.py`：`aa9cd1a4d6d534fb5a5ba1936d845d8f54b7c0aa418253eaea5c217daa14b2d8`
- `run-probe.py`：`7071d6bdf3f548f0d92ffcd9968c86d8c2fb3736d67bb719955aa69d5cfca09f`
- `static-schema.py`：`b94847230b1c98bfc50e79db886c032ebfc415e995d6954f287c06aee417623a`

## 完整检查名称

- `matched-trade_submit`
- `api-error-not-rejection-trade_submit`
- `matched-trade_cancel`
- `api-error-not-rejection-trade_cancel`
- `matched-trade_observe`
- `api-error-not-rejection-trade_observe`
- `matched-trade_accounts`
- `api-error-not-rejection-trade_accounts`
- `matched-trade_funds`
- `api-error-not-rejection-trade_funds`
- `matched-trade_positions`
- `api-error-not-rejection-trade_positions`
- `matched-trade_fees`
- `api-error-not-rejection-trade_fees`
- `wrong-trdEnv-trade_submit`
- `wrong-accID-trade_submit`
- `wrong-trdMarket-trade_submit`
- `wrong-trdEnv-trade_cancel`
- `wrong-accID-trade_cancel`
- `wrong-trdMarket-trade_cancel`
- `wrong-trdEnv-trade_observe`
- `wrong-accID-trade_observe`
- `wrong-trdMarket-trade_observe`
- `wrong-trdEnv-trade_funds`
- `wrong-accID-trade_funds`
- `wrong-trdMarket-trade_funds`
- `wrong-trdEnv-trade_positions`
- `wrong-accID-trade_positions`
- `wrong-trdMarket-trade_positions`
- `wrong-trdEnv-trade_fees`
- `wrong-accID-trade_fees`
- `wrong-trdMarket-trade_fees`
- `wrong-account-environment`
- `target-account-not-found`
- `empty-trade_observe`
- `duplicate-trade_observe`
- `empty-trade_positions`
- `duplicate-trade_positions`
- `empty-trade_accounts`
- `duplicate-trade_accounts`
- `empty-trade_fees`
- `duplicate-trade_fees`
- `wrong-order-trade_cancel`
- `wrong-order-trade_observe`
- `wrong-order-trade_fees`
- `available-funds-absent`
- `available-funds-explicit-zero`
- `fee-amount-absent`
- `fee-amount-explicit-zero`
- `fill-fields-absent`
- `terminal-status-not-final-economics`
- `missing-s2c`
- `missing-required-retType`
- `wrong-response-serial`
- `late-read-keeps-expired-fact`

这些记录只证明固定 protobuf 的离线边界和源码合同；没有新候选构建、安装、旧数据读取、原生窗口、真实行情、模型或券商操作。原始 JSON/log 保持原字节；root 负责后续统一门禁结论与仓库发布。
