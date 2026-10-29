# 旧空工作区的 Windows 物理视图

dev2 原生读取时，一个只有身份标记的旧试用工作区出现 `history_path_outside_workspace`：目录解析到普通 AppData，而标记文件解析到同一用户的 MSIX LocalCache。原 Documents MACD13 与 dev5 NDAQ 结果读取正常，原件没有丢失或迁移。

本次源码只把经核验的物理根追加为一个独立只读候选。历史读取器的允许列表默认空；服务器仅从当前已选定的物理研究工作区推导同一数据容器，而且要求完整标准路径 `Packages/<family>/LocalCache/Local/HakimiTradeTerminal/workspaces/<name>/runtime/research-workspace`。这说明当前数据位于哪个容器，不宣称 Python 进程获得了操作系统包身份认证。

追加时继续核验同一容器内 `HakimiTradeTrial/workspaces/<20位ID>` 的精确文件映射、原标记 schema、完整 bundle ID 与目录名前缀。不会扫描 Packages、接受浏览器路径、拼接两个目录或放宽 `_safe`/重解析点拒绝。普通工作区及非标准布局沿用原发现逻辑；原逻辑视图警告仍保留，界面新增可独立选择的物理只读位置。

验证：12 项定向映射/容器测试与原 10 项历史读取测试通过；最终完整终端门禁 419/419、无跳过（`t13-msix-full-terminal-r1.log`）。首轮测试入口漏设项目根而未能导入，失败日志保留，修正测试启动路径后通过。开发解释器和 dev2 包内解释器分别只读运行当前源码，均从已选定数据容器找到该真实物理候选，确认原任务/结果为空。四个旧工作区 188 个文件及物理标记的哈希、大小、修改时间全都不变；旧 `_safe` 和 `_no_links` 函数逐字未改。

本机证据位于 `Downloads/Hakimi-Astra-Delivery-20261029/t13-msix-parent-20261030`，包括 `real-parent-python-r1.json` 与 `real-private-python-r1.json`。原独立草稿证据保留在 `t13-msix-physical-draft-20261030`。没有启动原生应用或生产服务、没有网络请求/研究运行，安装包未修改；待后续冻结包再验证同窗选择。
