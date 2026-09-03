# 哈基米研究 v2 Electron 桌面壳

这是本地、research-only 量化验证平台的 Experimental 桌面包装层。它承载
Exchange Terminal 的行情、数据、策略研究、证据审阅和报告界面，不提供 paper、
live、订单输入或自动参数优化权限。

## 当前能力边界

- Supported：公开市场数据研究、历史回测、确定性 Frozen benchmark、研究报告和策略目录
- Experimental：本地研究终端与桌面窗口体验
- Archived：parameter optimization、paper execution、live execution
- Disabled：order entry

Electron 会 exact 校验 Python `/api/health` 中的 canonical
`product-capability-catalog-v1`。目录缺失、版本漂移或任何执行权限升级都会
fail-closed，不会被解释成可交易状态。

Renderer 中保留的历史 paper/order DOM 选择器仅用于兼容旧只读视图；执行控件已隐藏、
禁用，并在任何网络请求前由 Archived capability guard 阻断。历史快照、账本和执行事件
只能作为研究复盘材料。

## 启动

从项目根目录运行：

```bat
outputs\Hakimi_Trade_V2_Electron_START.bat
```

或在当前目录运行：

```powershell
npm.cmd install
npm.cmd start
```

桌面壳只自动启动本地 Python 研究后端。它不会在启动时自动拉起 FutuOpenD 或其他
账户网关；如只为公开行情研究确需 FutuOpenD，必须由用户从菜单显式启动。

## 自检

```powershell
npm.cmd run check
```

该命令检查 Electron 语法、Python/Node capability catalog parity、renderer Archived
动作墙和既有图表/证据 presentation 合同。通过不代表浏览器验收、真实数据质量、
策略盈利、paper/live 权限或发布就绪。

## 不变量

- UI 阅读顺序保持 `SOURCE -> GAP -> MATURITY -> PERMISSION`
- 研究或 verifier PASS 不产生参数选择、ranking 或交易授权
- `paper_allowed=false`、`live_allowed=false`、order entry Disabled
- deterministic fixture 仍是 synthetic、quality BLOCK
- 旧 single-look、legacy pack-v5 UNKNOWN 和 pointer-v2 no-reissue 不变