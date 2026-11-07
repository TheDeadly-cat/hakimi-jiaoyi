# Windows 自带运行时试用包

试用包在新目录中包含完整 Python、精确依赖和 Electron。用户解压整个 ZIP 后双击 `HakimiWorkbench.exe`，不需要运行命令或预装 Python、Node、Electron。它是独立开发试用包，尚不是签名安装器或正式 Release。

数据默认保存在 `%LOCALAPPDATA%\HakimiTradeTrial\workspaces\<包身份前20位>`，独占创建的身份文件绑定完整64位身份；前缀冲突或已有无身份记录时停止，不接管、不覆盖。程序文件保持只读。相同包移动到其他目录后仍使用同一数据目录；不同包身份建立独立空间，不自动迁移旧账户、改写旧结果或替换旧快捷方式。工作台菜单提供复制诊断信息和打开诊断文件夹。

启动前按普通 Windows 260 字符边界检查程序成员路径，以及首用流程的原件、快照、任务、运行、成本验证等已知最深数据布局。过长时显示中文说明并停止，不依靠本机已开启的长路径设置放行。该检查不是对任意外部文件名或全新 Windows 的完整验收。

数据目录同时以原始文件系统的 `realpathSync.native` 核对物理路径；部分启动宿主会把 AppData 映射到自己的私有目录，普通 `realpathSync` 可能看不出新增路径长度。实际路径过长时，在写入身份文件和研究记录前停止，提示从 Windows 文件资源管理器双击试用入口；不迁移、不覆盖旧目录。通过检查后将同一物理路径交给后台，并使用现有页面会话认证只读核对 `/api/state.workspace`，一致才显示窗口。认证失败与目录不一致分别处理，会话令牌不进入日志。旧本机入口未绑定此附加字段时维持原启动方式。

## 构建与来源

Electron 对 `.asar` 提供虚拟目录语义。试用入口使用 Electron 内置 `original-fs` 遍历和计算原始文件哈希，清单仍包含整个 `.asar`，不跳过它。普通 Node 检查不能代替真实 Electron 启动检查。维护者还应执行 `npm run test:trial-electron -- --electron <原始Electron.exe> --bundle <保留的r1程序目录> --output <新证据目录>`：它在真实 browser 进程复现旧校验失败、验证完整文件清单和修改档案后的拒绝，并以无效合成清单验证打包入口；不启动 Python、研究窗口或创建研究记录。该回归使用已保留的 r1 失败包，所有新探针输出独占保存，仍不能代替新包的原生完整流程验收。

维护者使用 `tools/build_windows_trial.py`，输入完整通过的普通 wheel 验收回执、本地 Python/Electron 压缩包、与锁文件一致的依赖 wheelhouse 和全新的输出目录。工具不下载、不全局安装、不启动研究，也不复制已有用户数据。失败输出保留，不能自动覆盖重试。

当前来源锁为 CPython 3.14.6 Windows x64 完整发行 ZIP、Electron 31.7.7 Windows x64 ZIP。版本、官方来源 URL 和精确 SHA256 固定在构建工具中；缓存来源不能只凭文件名认定，必须匹配这些字节。保留各运行时及 wheel 的许可证。Electron 31 仅沿用当前候选环境；对外正式发布前另行评估受支持版本与签名，不把本轮离线试用等同正式发布验收。

`THIRD-PARTY-NOTICES.json` 和同名文本索引列出 Python、Electron、Chromium 及每个依赖包的原始许可文件与哈希。构建不会替项目新增开源许可证或扩大试用授权。

构建复用既有 `release_wheel_bundle.export_bundle` 完整验收门禁。依赖仅接受锁定名称、版本、CPython 3.14 Windows x64 或通用 wheel；核对所有 RECORD 字节。当前支持的轮子没有 `.data/` 布局；出现该布局会停止，不能猜测安装位置。软件包直接放入私有 Python 的 site-packages；本入口只使用模块方式启动，不生成依赖开发电脑路径的 console-script 启动器，也不复制旧 venv。

轮子必须来自 CLEAN 产品构建，当前产品源码和三个构建定义必须与验收记录逐字匹配。桌面壳和打包定义另外绑定当前 Git 提交的实际字节；该限定范围须干净，不能用文档提交冒充原轮子构建。打包结束再次核对这些输入未变。

这个新的自带运行时合同单独使用 `research-windows-trial-v1`。原本机 `research-local-desktop-v1` 的独立 venv 验收要求保持，旧候选目录保持原字节。

Electron 使用[官方预构建分发目录结构](https://www.electronjs.org/docs/latest/tutorial/application-distribution)，把独立入口放入 `resources/app`。Python 使用[官方 Windows 分发机制](https://docs.python.org/3.14/using/windows.html)，附带应用所需依赖；不依赖用户的全局包管理器。

## 启动一致性与诊断

启动先校验完整文件集合、SHA256 和自带 Python 的实际包位置、构建、依赖状态。后端使用 `-I -B -u -X utf8`，忽略当前目录、用户包和 Python 环境变量；打开页面前还核对后端实际宣布的解释器位置、包位置及源码内容身份。当前目录混入同名包不能让已验收安装与实际运行分离。

构建与每次启动还核对 Python 的精确版本、prefix/base_prefix 以及完整模块搜索路径，所有搜索路径都必须位于试用包的私有 Python 目录内。

出现文件变化、依赖不完整、实际身份不符时，程序停止并显示中文下一步。诊断按新文件追加，只包含状态、版本、位置及错误；不加入价格、凭据或用户报告正文。原有数据不被修复、覆盖或自动重新计算。

## 验收边界

夹具测试覆盖压缩包路径、重复名称、轮子 RECORD、验收不完整、运行时漂移、完整目录、实际 Node/Python 启动参数和独立数据目录。构建期间在私有运行时导入 NumPy/Pandas并核对安装身份，不执行策略。

构建成功仍不能替代没有开发环境的独立 Windows 机器验收。此验收须明确使用未安装 Python、Node、Electron 的 Windows x64，测试中文与空格目录、普通用户权限、断网首次启动、内置示例、首次行情、结果解释、关闭重开及诊断复制。宿主上的空 PATH/独立目录探针和 GitHub Windows 临时 runner 只能证明对应的依赖隔离范围，不能标为真实干净 Windows 或三位新手验收。
