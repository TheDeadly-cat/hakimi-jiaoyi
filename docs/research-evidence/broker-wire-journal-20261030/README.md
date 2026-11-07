# Broker wire profile、journal 与 scoped transport 离线证据

本批是新的源码合同与离线验证，**尚未进入当前 a235e8a2 / 0.7.0.dev3 candidate-r4 包**。没有新增同窗执行入口、host factory、生产 dispatch gate、经济事实 response verifier、实际 worker、加密传输或 REAL 适配；不是 OpenD、真实账户、真实行情或原生使用验收。九项外部执行权限仍全部为 false。

## 本次完成的检查

根代理唯一一次整合门禁为 [642/642 PASS](integrated/summary.json)，194.03 秒，0 skip/error/failure；[终端完整日志](integrated/terminal.log)。同时 [15 项打包合同](integrated/packaging.log) 4.221 秒、[4 项门禁 runner](integrated/gate_runner.log) 0.411 秒通过。2090 个输入前后摘要一致；[9 个相关文件的身份摘录](integrated/source-identity-summary.json)绑定最终源码。这里没有重新执行任何门禁或探针。

| 范围 | 当前证据与含义 |
| --- | --- |
| 原有终端合同 | 542 项在同一次整合门禁中保留通过。 |
| 纯 wire profile | [24 项原定向证据](profile/targeted-r2.log)，[冻结身份](profile/review-freeze-identity.json)；本次 642 再覆盖当前 24 项。 |
| journal | 当前服务 `cf41a358…` 的 30 项已被本次 642 完整覆盖。原 [29 项日志](journal/targeted-final29-r4.log)属于此前 `0ef50515…`；后续 [opaque ID 2 项](journal/targeted-opaque-r5.log)属于当前源码，原件均保留，不能把分批数字相加当最终套件。 |
| 假连接 / protobuf-shaped codec | 当前 transport 33 + codec 13 = 46 项由本次 642 完整覆盖。[先前共同 44 项](transport/focused-r3.log)和 [UTC 补丁后的 transport 33 项](transport/focused-utc-r1.log)保留原范围；这些是无 SDK 的 fake 合同，不是实际 SDK 兼容证据。 |
| 实际锁定 SDK 字节检查 | [独立 24 检查摘要](private-final/codec-result-summary.json)，真实私有 Python `-I -S -B -X utf8`，3.124 秒。12 个 SDK 原版 `pack_req` action、实际 Request 类解码、两通道从 None 会话经精确 1001 Response 绑定、8 个越界拒绝与 optional source-time 缺失/明确 0 的区别。 |

本次没有 JavaScript、既有 host runtime 或既有 service route 改动，故[没有重复本地 desktop](integrated/environment.json)。后续新提交仍须由其自己的 CI 检查；本文不借用旧 CI 作为本批源码验证。

## 实际 SDK 探针的边界

探针复用未修改 r4 的私有解释器与依赖，显式加入 parent 中已逐字节绑定的源码；parent 当时为 `DIRTY_SOURCE_BYTES_EXPLICITLY_HASHED`，不是新 CLEAN 产品包。distribution 版本是 `10.7.6708`，内部 `VERSION.txt` / `futu.__version__` 是 `10.07.6708`，按原来源分别记录。

[最终 guard](private-final/guard-final.json)中 socket、线程、数据库、子进程与禁止的 SDK constructor 尝试均为 0；本机 `gethostname` 元数据读取 1 次单列且未保存名称。没有创建 SDK context、外连或经济运行；9 权限均 false。[完整调用](private-final/invocation.json)、[runner 结果](private-final/runner-result.json)、[stdout](private-final/stdout.log)、[stderr](private-final/stderr.log)、[虚构请求原 bytes](private-final/request-frames.json)、[最终 child](private-final/pinned-codec-probe-child-r5.py)与[运行器](private-final/run-pinned-codec-probe-r5.py)可审查。

826 个包内导入模块（其中 133 个 Futu 模块）的原完整清单留在 E；摘要保留完整 24 检查及原清单 SHA256，不把它称作本轮全包验收。原始出处、字节长度与 SHA 均在 [COPY_PROVENANCE.json](COPY_PROVENANCE.json)。真实 OpenD、加密协议、账户/资金/费用/tick/来源时钟验证和生产许可链均未验收；`RESPONSE_RECEIVED` 仍是 `economic_acceptance=NOT_INFERRED`，不是 journal ACK 或下单成功。

## 失败原件与修正顺序

1. [private-r1](private-failures/r1/runner-result.json)：SDK 隐藏 pandas 导入异常，只输出 [Missing required package pandas](private-failures/r1/stdout.log)。该轮没有 guard-final 文件，未补造计数。
2. [private-r2](private-failures/r2/guard-final.json)：[真实栈](private-failures/r2/stderr.log)定位 pandas/platform 读取本机 `socket.gethostname`，被过宽的 socket audit 拒绝。原 `socket=1` 是这个被拒的本机元数据读取，不是外连成功；记录未改写。
3. [private-r3](private-failures/r3/guard-final.json)：[真实栈](private-failures/r3/stderr.log)表明将 `Popen` 类替换为函数破坏了 asyncio 的子类声明。进程尝试为 0；最终保留类并拒绝其 `__init__` 与 subprocess audit，没有放行进程。
4. [private-r4](private-final/runner-result.json)：上述明确的测试 guard 修正后一次通过。此前失败日志、回执与所有外部原件保留；没有覆盖或原地重跑。

## 源码交接与发布身份

阅读 [profile 原交接](profile/HANDOFF.md)、[journal 原交接](journal/SERVICE-HANDOFF-r1.md)、[transport/codec 原交接文本](transport/SOURCE-HANDOFF-r2.txt)与[原最终回执](transport/FINAL-HANDOFF-r1.json)。这些历史交接中“尚未完整 30/46 项”或“尚未 probe”的语句是当时状态；本页以随后完成的 642 与独立 SDK 检查说明新增证据，不改写旧回执。两个 transport Markdown 原件按字节存为 `.txt`，其中历史相对链接仍描述其 E 原目录；仓库可点击证据以本 README 为准。

[CI166 原回执](ci166-completed-summary.json)为 `7ee12e44db381ac9a9651e60fa3d5bdd15bca27b` 文档基线的 [run 40974805001 / 11 jobs 成功](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40974805001)，不覆盖这批尚待提交的新 helper。可用包继续是 a235 r4；未新建候选、未安装/启用本批 helper，未触碰旧 UNKNOWN/T3、历史研究、原生窗口或正在使用的旧 QA 数据。

文件完整性见 [SHA256SUMS](SHA256SUMS)。原始副本逐字节复制；两个摘要明确标为 `DERIVED_SUMMARY_NOT_ORIGINAL_RECEIPT`，完整大型原件仅留 E 并用 SHA 绑定。
