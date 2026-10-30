# 原终端产品交付任务清单

依据：用户 2026-10-29《Astra 持续执行任务书》第二版（30 项任务、三阶段）。本清单保留全部目标；工程、包验证、原生操作与真人理解分别结案。状态：TODO、DOING、DONE、BLOCKED_ENV、BLOCKED_AUTH、BLOCKED_HUMAN、BLOCKED_DEP。

## 当前基线与产品路线（T01 / T02）

- 权威交付目录：`C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易`；分支 `codex/p0-m32-research-integration-20261022`。开始时干净，HEAD / PR #26 均为 `db443e6ed2c758a858217a592bf7e074ec8affe6`，Draft / Open / 未合并。
- GitHub run 143 / `40794460886` 已实时核对为 success。该结果仅对应上述提交；后续源码与候选另验。
- 原 Documents 源码保留：35 项已跟踪改动、568 个未跟踪文件（`git status --porcelain --untracked-files=all`）。不在该目录实施整改。
- 实际 dev5 程序目录：`C:\Users\Administrator\Downloads\哈基米试用 dev5-f778020-r1`。当前 manifest 为 `0.6.0.dev5`，bundle `ab2e49cdc8e468385dd7b64dc30f2665aa7591a52b8d6022833c02983b7569a8`，SHA256 `c993523546b6c84e7a8be4a00636594f6fe8734ffa18dafc62e6e15125199b03`，与原验收一致。本轮开始未发现运行中的该 Electron 程序。
- 旧 dev5 数据：`%LOCALAPPDATA%\HakimiTradeTrial\workspaces\ab2e49cdc8e468385dd7`；原终端数据：`Documents\哈基米v2交易\outputs\python_quant_bot\runtime`。两者均保留，新候选使用独立明确工作区；旧结果读取/选择与新写入分开。
- 日常主入口固定为原 Electron `main.js` → 原 `exchange_terminal.server` → 同窗 `/quant/`。新候选名称为“哈基米交易”，首个整合包版本计划 `0.7.0.dev1`；旧 CLI / dev5 身份保持原样。
- 原九策略保留 `terminal.causal-long-only-signals-*` 与 `signal-close-next-open-ohlc-conservative-v3` 身份；冻结核心保留其版本、策略键和工作区。名称相同不转换公式、不混排。先接入任务/结果/导入/教学/复盘与退出，再接首次股票/更新/比较；执行演练在同一应用内独立页面和权限。
- 历史 UNKNOWN、暂停的 T3、旧包、冻结组件和历史回执不重跑、不替换。离线恢复只使用新合成案例。模型/外部券商/真实资金仍须沿用单独授权。

## 阶段 A：一个可安装、可完成研究并重开的程序

### 用户补充优先级（2026-10-29）

先让人方便使用：选股票 → 看推荐策略与理由 → 核对账户、资金和风险 → 预览并明确确认订单。因子与参数调试服务于这一主流程，默认展示实际因子值、触发条件、数据截止时间和不下单原因，详细诊断按需展开。策略推荐必须绑定真实数据和规则版本；规则适配、已触发信号、历史表现分别说明，缺少样本不能自动补成收益排名或买入信号。

后续工作顺序据此调整：完成各候选对应的原生保存/运行/重开验证；并行接入日常股票数据、因子解释与简化的执行主流程，再补持续模拟与券商候选。现有手工回执/对账表单作为高级诊断保留。推荐选择和订单提交是两个明确动作；外部模拟账户与真实资金步骤继续遵循 T29/T30 的具体授权要求。

| ID | 状态 | 依赖 | 修改提交 / 验证证据 | 阻塞与下一步 |
|---|---|---|---|---|
| T01 | DONE | 无 | 本文实时 Git、PR、包 manifest、目录核对 | 保留两个源码与旧数据，后续只改交付目录 |
| T02 | DONE | T01 | 本文入口、规则身份、工作区与接入顺序 | 按原终端主线实现 |
| T03 | DOING | T02 | dev3 r2 原生完成卡已通过；普通查看结果未定位的问题已复现并修源码，53项定向、1280/480完整页面及18.489秒完整桌面检查通过 | r2 包保留原缺陷；待新候选验证定位修复。仅一次明确研究，无重复运行 |
| T04 | DONE | T02 | stage-a-source-final-r1.log、bounded-dom-qa-r3；79/80/81 阻止、82 就绪、长窗口与真实 runner 对照 | 只读预检查同源；失败先于 started 记录，不产生 UNKNOWN |
| T05 | DONE | T02 | strategy-semantics-audit.md、test_strategy_presentation（含实际 API 路径） | 独立展示层；原 STRATEGIES、公式及指纹文件未改 |
| T06 | DONE | T05 | terminal-parameter-preflight.test.js、bounded-dom-qa-r3 | 新建/修订/带入/回读统一单位；旧缺字段不补默认 |
| T07 | DONE | T03,T06 | bounded-dom-qa-r5；完整渲染真实点击，core-run-posts.json | 单入口；两条路径显示保存版本并明确运行；core 验证 expected_task_id；导航保留草稿 |
| T08 | DONE | T03,T05 | terminal-result-summary.test.js（9 项）、bounded-dom-qa-r3 | 摘要缺值未记录；零成交只引用实际保存证据 |
| T09 | DONE | T06 | T09-ai-binding-20261029；Python 14/14、JS 4/4；DOM 参数变更检查 | 数值行情与规则参数分别表达；费用/风控/来源真实性不扩大为 MATCH |
| T10 | DONE | T02 | r4 原生：同安装/工作区重复启动仍为同一窗口；关闭后无进程/监听；冲突端口只探测且不接管 | 默认退出路径已验证；旧程序未停止 |
| T11 | BLOCKED_ENV | T02 | r4/dev2包内组件、依赖、合成运行及原生启动通过；只读检查确认本机Sandbox未启用且程序不存在 | 包内闭包已验证；仓库实际不可访问的独立环境尚无，不启用系统功能或以本机成功替代 |
| T12 | DONE | T11 | r4 私有解释器16依赖、真实新合成运行、9045资源及9046 ZIP条目通过；中文/全局同名模块隔离定向检查通过 | 本机工程与实际原生范围，不等于干净新机验收 |
| T13 | DONE | T11 | dev3原生同窗选择MSIX物理候选并正确读空列表；读取原MACD13任务/报告、dev5 NDAQ；245保护文件不变 | 任务与结果分开展示，原逻辑警告保留，当前写入工作区不变；不迁移或重跑 |
| T14 | DONE | T03-T13 | a53068b CLEAN r4：208终端、完整桌面、11打包、9046 ZIP及私有真实新合成运行通过；原生可用 | 包身份见 research-evidence/terminal-070dev1-native-20261029；不含后续 B/C 改动 |
| T15 | DONE | T14 | dev1 r4原生保存、运行1次、原图表复盘、关闭重开、重复启动与端口冲突已通过；41数据文件重开不变，9045程序文件不变 | 仅本机MSIX启动隔离区；干净新机/非管理员/独立真人未验证；r1-r3原失败保留 |
| T16 | DONE | T14 | 当前说明指向dev3 r4 / a235e8a，542终端/15包/完整桌面及9070程序文件、9071 ZIP项通过；r4原生未验和r2原生部分已验分别列出 | 旧文档和包保持原身份，后续新候选继续更新 |
| T17 | BLOCKED_HUMAN | T14 | 已备[独立试用任务卡](novice-trial-task-card.md)，尚无未参与开发者的实际记录 | 使用准确候选身份、不示范控件，记录原话和帮助；其他工作继续 |

## 阶段 B：日常继续使用

| ID | 状态 | 依赖 | 修改提交 / 验证证据 | 阻塞与下一步 |
|---|---|---|---|---|
| T18 | DOING | T02,T11 | 同窗日线页/桥接/因子解释已入dev2；原生明确检查TSLA一次，原件保留且正确阻断缺公司行为覆盖 | 真实证券完整保存链未通过；新增独立补证适配，不改旧BLOCKED |
| T19 | DOING | T18 | 无变化/新增/修订/异常与保存新输入已接UI；UNCHANGED不写新版本，原件保留；完整DOM导入选入草稿通过 | 现可在修订任务中选择新输入；T22本地模拟已验，真实来源日常更新链仍待完整资料 |
| T20 | DONE | T08 | 真实保存结果验证、只读比较路由与原/核心展示；条件缺失不算差值，不同成本/模型只并排；定向与完整DOM通过 | 此为源码离线范围，新包随T23验收 |
| T21 | DOING | T18 | SPLIT纯适配10项；独立补证模块16项及原日线41项通过，保留原件/证券/窗口/分页/三个时间，缺可信来源reader仍阻断 | 补证未接UI或真实reader，实际来源与计算链尚未整合；股息仍未支持 |
| T22 | DONE | T19,T24 | dev3 r1原生创建、seed、一步、暂停、关闭重开、核对、恢复通过；账本8events/5requests，未多STEP，现金/持仓/日期不变；完整终端464及桌面通过 | 本地虚构历史整股模型范围；真实日常来源更新归T18/T19/T23，不冒充市场表现或券商成交 |
| T23 | DOING | T18-T22 | dev3 r4 / a235e8a已构建验包，包含结果定位、就地因子和同窗离线计划；此前r2原生完成卡、报告、图表、因子、订单预览和首次关闭通过，重开报告/账户可读 | 用户停止桌面操作，r2原生计划选择及最终关闭待继续；r4原生未验，真实股票完整链仍待来源 |

## 阶段 C：同一主程序中的执行准备

| ID | 状态 | 依赖 | 修改提交 / 验证证据 | 阻塞与下一步 |
|---|---|---|---|---|
| T24 | DONE | 稳定研究合同 | 已连接真实保存结果解析、版本/证券/账户绑定；14项原/核心实际整合检查与结果转演练DOM通过 | 离线合同已完成；真实券商版本由T29/T30另授权 |
| T25 | DONE | T24 | 离线core/service合同与控制层通过；dev2原生仅一次明确submit，ACCEPTED不冒充成交，0fills | 部分/全部/撤销/未知为离线验证，原生接受/重开范围另列；券商另验 |
| T26 | DONE | T24,T25 | 资金预留/owner持仓/时效/证券绑定检查通过；dev2原生BUY1@100预留101，可用9899，现金10000 | 前端预览只粗估，提交时服务端再次校验；外部权限关闭 |
| T27 | DONE | T25,T26 | 合成中断/幂等/晚到成交合同通过；dev2正常关闭重开原订单和57文件不变，要求对账后恢复 | 本地范围；本次未执行原生成交/撤销/对账恢复，旧UNKNOWN/T3保留 |
| T28 | DONE | T20,T25 | 已连可信报告/账户/计划只读路由，一次账本快照；六类说明、累计费用与未知项，原/核心真实新TEMP保存整链通过；完整门禁371、桌面通过 | 当前手工演练缺逐笔因果对应，收益差及贡献保持未知；界面主区显示版本N，原ID在详情 |
| T29 | DOING | T25-T28 | 新源码已接同窗账户共享停止/找回/明确恢复、host固定root与health身份、真实journal factory及两层短控制屏障；最小锁定protobuf loader独立实际私有进程11协议/164文件通过；完整756终端、20.127秒desktop、15包/4runner通过 | 当前r4未含后续源码，r5准备中；仍缺生产授权与每次派发gate、实际worker/transport串联、精确经济事实/价格规则、OpenD/加密兼容，外部步骤另授权 |
| T30 | DOING | T29 | 全局账户停止按provider/mode/account跨workspace共享，旧local stop保持AND约束；明确resume不续旧revision、不重发旧请求；实际服务/handler/journal整合11项与双浏览器实际临时控制服务通过；9权限false | 新共享控制与factory不是生产派发实现，PackageWorkerSpec仍拒启动；EXTERNAL_RECORD拒test profile；REAL实际codec/资金许可未提供，真实资金另需账户资产额度授权 |

## 验证记录

最新源码 `c20341e` 的 run157 已结束为 failure：9 个独立作业成功，新逐日模拟测试混用 Windows 临时目录短名与物理长名。仅修正测试准备方式后，真实短 TEMP 的 22 项全部通过，原生产路径检查与策略字节未变；[修正、失败保留与首用说明](research-evidence/ci157-fixture-correction-20261030/README.md)。随包说明已独立，11 项打包检查通过。修复提交 `500d691` 的 run158 / 40937072389 已11/11成功，dev3 r1已干净构建并完成本机逐日模拟与旧结果只读验证，详见[构建](research-evidence/terminal-070dev3-build-20261030/README.md)及[原生凭据](research-evidence/terminal-070dev3-native-20261030/README.md)。后续[保存卡片与订单因子源码修复](research-evidence/saved-result-order-factors-20261030/README.md)已通过最终完整Node22桌面检查；这四个文件尚未进入500d包，接受独立新CI。其提交`0cd021a`的run159已11/11成功。后续[已有研究快捷入口](research-evidence/candidate-saved-result-20261030/README.md)现已实现：行情和规则精确匹配后直接打开原结果，多份明确选择，订单入口移到长摘要之前；51项定向、1280/480完整宿主及最终完整Node22桌面检查通过。功能提交`43c155a`的run160已11/11成功，干净[dev3 r2](research-evidence/terminal-070dev3-r2-build-20261030/README.md)已构建并完成冻结464项终端、完整桌面、11项打包及完整验包；r2原生已完成保存卡、候选找回同报告、图表复盘、历史因子与一个账户/计划的订单预览，最终确认未勾选、0提交。普通查看结果的定位缺陷已在后续源码修复；53项定向、1280/480页面与18.489秒完整桌面检查通过。[原生进展及定位修复](research-evidence/native-result-navigation-20261030/README.md)另存。用户使用桌面期间保留窗口，关闭重开及最终保护检查待继续；修后新包原生验证也尚未完成。此前文档提交cdc6adf的run161已11/11成功，不替代新源码提交CI。

本轮外部证据目录：`C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029`。旧整合回执目录和旧 CI 完整保留。本清单不会以单元测试代替包内启动、原生操作或真人验收。相关代码不变时不重复已结案的历史研究。

阶段 A 完整桌面检查：`stage-a-desktop-full-r4.log` 通过。根任务合并后的定向 Python：`stage-a-source-final-r1.log` 29 项通过；`stage-a-python-r1.log` 42 项通过（范围重叠，不相加作为独立总数）。浏览器使用完整 render_quant_html 与模拟后端，1440/1280；它证明界面交互，不代替包内真实计算。旧失败截图/日志均保留。

阶段 A 已提交并推送 `6ca4015b45bf02f765b933bb82725cc730a715c5`。干净冻结树的终端全门禁为 205/205、完整桌面检查和 6 项新打包检查通过。对应 CI run 144 / 40809973324 完整结束为 failure：两项 Windows 8.3 路径问题（健康测试预期与当前工作区排除）已定位；原运行不重跑或取消，修复提交单独接受新 CI。原生 r1 暴露的问题不被上述源码检查覆盖，相关失败包/日志/原 ZIP 均保留。

后续修复将当前工作区与测试预期统一为物理路径，并在窗口创建前清除外部 Crashpad 继承配置，将日志、后台工作目录和限长脱敏启动诊断移到独立数据目录。严格程序文件清单不放宽。`stage-a-r2-desktop-full-r1.log` 完整桌面检查通过；`ci144-focused-correction-tests-r1.log` 15/15 通过。新 r2 包的实际启动与生命周期验证仍待完成，这些源码检查不能证明原生问题已解决。

`2f9018d` 对应 CI run 145 / 40814734329 已结束为 failure：终端门禁 205/206，唯一失败为测试仍期待旧产品标题；测试预期修正为 `8f22e1c`，不是包内程序变更。r2 原生尝试已执行且失败：清单不再污染，包内 Python 已就绪，但 Windows MSIX 物理目录映射与 Node 普通 realpath 解析不一致。失败 r2、诊断、原 ZIP 保留；新修复不得借用源码或导入 PASS 冒充用户流程验收。

物理路径修复使用 Windows 原生解析，先创建本次明确选定的新量化目录再计算单实例标识；显式旧数据读取路径不再改变新量化默认写入位置。`native-workspace-physical-path-focused-r5.log` 40/40 通过，`native-msix-path-readonly-r3.json` 验证了当前机器上的真实逻辑/物理路径差异、同目录匹配和不同目录拒绝。未放宽程序清单或目录边界，未延长 18 秒等待；新 r3 原生验收仍待完成。

后续 r3 原生结果见上述 T14/T15。`739a3c2` 将普通任务显示名与内部目录名分离，含空格/标点名称保留原显示文字，原始 frozen vendor 不变；两项真实临时核心复制/名称检查通过。新 builder 为实际安装的 canonical 与 frozen 字节分别生成原合同构建凭据，冻结原来源与本次封装提交分开；只有真实 verifier 校验才能得到 BUILD_VERIFIED。打包强制在新临时工作区保存任务、明确运行一个 SYNTHETIC_TEST 例并核验保存结果/只读回读；打包经济运行数如实记 1，真实行情、旧回放、来源/券商/模型请求均为 0。开发副本真实私有解释器探测已通过；11 项打包检查通过。此开发证明不替代干净 r4 或原生验收。

CI run 146 的两个短路径夹具预期已由 `d065d2e` 修正。该提交 run 147 / 40818239379 完整结束为 failure：桌面 Node 22.23.4 在测试夹具 fs.cpSync 复制中文路径时以 0xC0000409 退出，其余业务作业成功。独立精确版本与无框架最小案例已复现；仅把该夹具改为按清单逐文件复制，保留中文空格和全部断言。精确 Node 22 原组 54/54、Node 24 单文件 18/18 通过，无跳过；旧 CI 原样保留，修复后新提交接受独立 CI。


### 2026-10-30 后续源码与原生节点

订单预览就地因子核对已通过32项定向、1280/480完整页面和19.576秒完整桌面检查；来源/账户/计划/经济字段失效规则保留，情景切换只影响解释并取消确认勾选。T29新增离线计划合同及保存源码/资料分类投影，默认读取兼容，489项终端及11项包测试通过；尚未接实际服务、独立账本、持久认领、停止派发屏障和适配器，T29/T30仍DOING。

r2首次关闭已验证265旧文件不变、新QA20文件读取不变、1研究/1账户/1计划/0订单/0成交；重开原报告与账户可读，原生计划选择仍未确认。用户停止桌面操作后保留窗口，最终关闭和程序核对待明确恢复；不把FIRST_CLOSED写成最终验收。f8242f3的run162已11/11成功。见[就地核对](research-evidence/order-preview-inline-factor-20261030/README.md)、[离线合同](research-evidence/broker-execution-plan-20261030/README.md)、[原生节点](research-evidence/terminal-070dev3-r2-native-20261030/README.md)。

此前候选提交f752958的[run163](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40960877552)已11/11成功。dev3 r3构建及验包身份见[构建记录](research-evidence/terminal-070dev3-r3-build-20261030/README.md)；原生窗口尚未验收，后续源码不沿用此CI结论。

本轮完整候选为[dev3 r4 / a235e8a](research-evidence/terminal-070dev3-r4-build-20261030/README.md)：542项冻结终端、15项打包、完整Node22桌面及9070程序文件/9071 ZIP条目通过；包内14UI、两模式计划只读入口和新临时单次合成运行通过。候选源码的[run165](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40971259290)已11/11成功。新包未启动原生窗口，未执行计划变更/SDK连接；T29/T30的受限协议、跨工作区共享执行账本与有界worker继续实现。

[新协议与共享账本源码证据](research-evidence/broker-wire-journal-20261030/README.md)：冻结2090输入的完整642项门禁已覆盖profile24、journal最终30、transport33和codec13；真实SDK离线探针与fake tests分别记账。原v1、旧包和历史未知记录保留，测试修正前的失败原件未改。当前可交付包仍a235/dev3 r4；上述源码原语的实际服务接线和有界worker继续实现，不把工程缺口归为仅待授权。

[响应与进程源码后续](research-evidence/broker-response-worker-20261030/README.md)：完整709项门禁通过，新增facts27、记账18、worker22，2095输入前后不变；15项打包及4项runner通过。锁定实际protobuf在私有Python内完成7类/55项合成报文检查，205个加载文件核验；不导入futu顶层，0网络/DB/线程/业务运行。完整响应保存在原journal事件链，API错误不当拒单、撤单ACK不当终态；合法迟到成交/费用与已结束或更新余额的账本矛盾时保留原账并停止新风险。PackageWorkerSpec仍不可启动，实际派发/授权/完整经济事实/外部兼容尚未完成。上一源码6581c59的[run167](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40980480080)已11/11成功，新提交CI另核；当前r4包和原生暂停状态保持。

[共享账户控制与包内协议加载](research-evidence/broker-account-control-20261030/README.md)：当前19个源文件均绑定完整756/756门禁、2102不变输入，Node22完整desktop通过；双浏览器实例在新TEMP真实AccountControl上完成停止/恢复/丢回复后查原ID，1440/390布局通过。host不再复用缺失或不同共享根身份的后台；读取控制和构造journal均不创建记录。新增loader24项与实际私有解释器一次验证通过，只核本地代码来源，不升级交易权限。开发期SQLite测试未关闭连接及旧计划测试缺NODE_PATH的原失败另存，配置和fixture修正后由完整门禁覆盖。4ae9047的[run168](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40984635974)已11/11成功；本批新源码CI和r5实际包验证另行记录，旧r4与旧原生状态不改写。

a0356e0的[run169](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40989174236)终态为failure：9项成功，Python contracts及汇总失败。原因是独立抽取health handler的测试未提供新增的BROKER_CONTROL_ROOT；生产server已定义该变量。仅修测试夹具并补绑定/未绑定root的只读检查，6/6通过，前批19项实现/测试文件与原756/desktop门禁仍为相同字节。完整273项本地复测另有一项旧归档LF/CRLF精确字节期望差异，原件及Git设置未改；不称273全部通过，也不重跑历史CI。[失败原件、最小修复与唯一测试输入差异](research-evidence/ci169-health-fixture-20261030/README.md)另存。r5构建尚未开始，将从修正后的新clean提交构建并接受独立新CI。

b554733的[run170](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/40991057033)已11/11成功（远端273及756通过）。r5打包前发现父目录与干净副本6项换行字节差异，故在干净副本重验；其756出现1项临时worker目录清理ERROR，另32项Futu检查因该隔离测试环境缺SDK源码有1skip，构建未启动。仅增强测试资源收尾，生产worker未改，新增确定性迟到launcher/WinError32用例后23/23通过且UNKNOWN回执不变；只向新测试venv安装锁定本地wheel后32/32无skip通过。[原失败、环境修正和测试边界](research-evidence/r5-worker-fixture-20261030/README.md)保留。下一新冻结门禁预计757项，须实际验证；当前r4仍不变，r5尚未生成。
