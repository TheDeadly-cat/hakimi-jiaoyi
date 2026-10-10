# M3-1 单 symbol 别名修复

用户批准 PR #24 的 `deccb78` 后，转为可审阅状态触发仓库自动审阅。Codex 对该提交指出[单 symbol 别名缺口](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/24#discussion_r4237926677)。PR 未合并；原批准与新受审 head 分别记录，不将原批准套用到代码变更。

[原 dev2 安装复现](dev2-reproduction.json)来自实际已安装的 f2fac8c／wheel 816f93eb81c7…，不是修复后的代码伪造。10,000 USD 账户配置两个证券 ID、同一 TEST symbol、60% 单证券上限，59% 与 39% 两笔都获预留并结算，合计同 symbol 仓位 98%；流水 4。原 292 项没有覆盖这一配置缺口，其范围及候选原件保留。

dev3 在新账户创建和新写入前要求 symbol 唯一，比较时忽略大小写；不改变原证券 ID、定价或历史流水的语义。只读恢复显式允许旧配置，保留原逐 ID 风控判断；旧含别名账户拒绝新写入并显示只读。v2 时钟规则保持，dev1 原字节兼容保持。包内 v2 别名夹具为上述原已安装 dev2 真正生成的 account.json／SQLite 原字节与摘要。

源码针对性检查：共享账户 23 项、包导出 9 项通过，包含新配置及大小写别名在发布前拒绝、两种不同 symbol 的正常结算、原 v2 别名账户读取／写入拒绝／摘要不变。源码检查与普通 wheel 安装检查分别记录。

候选 `0.5.0.dev3`，CLEAN 构建 `554a430c21aaef2f1779b8a3eaa1635ac3c54e40`；wheel SHA-256 `633cff60f43cd498cdd54eadc3d765d092c79d75ec9543075936d9a1807fbcde`；运行源码 SHA-256 `557d53a28eaceaeb8dcd78b21f2d82cfe3d1355899616e150d5aee8950a8cf33`。见[接受回执](wheel-acceptance.json)、[构建身份](source-build-identity.json)、[测试范围](test-scope.json)和[锁定依赖](dependencies.json)。

同一普通 wheel 在全新仓库外 Windows 环境非 editable 安装，**295 项／175.029 秒**，失败／错误／跳过均 0，新增三项包含在 295 中。[共享安装流程 v3](installed-shared-funds.json)包含真实冷命令大小写别名配置拒绝、不同 symbol 正常结算、原 v2 别名账户只读和原字节不变；原时钟、五类规则、两进程资金竞争、COMMIT 前后中断、暂停恢复、迁移、输入／R3／内容边界仍通过。上述 23 项源码及 9 项包导出检查另记，不与安装总数相加。

[构建 CI](ci-build.json)绑定 [38060329025](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/38060329025)，attempt 1 九项成功。完整日志实际 checkout 为 PR 合并预览 `c8e31461cec32f1a63c481e4a1daa0c2d93a826c`，树与 554a430 相同；Windows 安装 295／226.496 秒、Ubuntu 295／46.364 秒、根 MVP 295／274.138 秒，安装源码与候选相同。最终 head 检查在 PR 描述另记，不把预览改称实际 main。

[交付](delivery.json)是新 ZIP `d4372f9d45405ba998f91cc78e044c0353147ef5f34837f63eea6cb08b572a9b`，本机目录 `Hakimi-M3-dev3-SymbolFix-20261010-verified`。[外层启动器首用](delivered-first-use.json)完成新解压、离线安装、共享菜单、退出重开和回执查询，两次退出 0；预留 8,000、可用 2,000、流水 1，读取不改账户字节。首用为代理。[实际原 dev2 TASK_STEP 账户](dev2-task-account-read.json)另由交付 dev3 读取，原两文件摘要不变；它与包内别名夹具是不同证据。

日常说明随功能 PR 更新，269 个代码／构建／测试／支持文件保持接受构建的原字节；原 dev1／dev2 包、回执和失败保留身份。最终 head 的 CI 和单独 main 核准在 PR 分别记录；原 deccb78 的批准不套用于新代码。范围仍为固定输入与离线合成账户；不扩展已结案 M1／M2、Unknown／T3、监控、券商执行、市场研究或正式 Release。
