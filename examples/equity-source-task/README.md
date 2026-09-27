# 虚构资料操作示例

`prior.html`、`actual.html` 和清单完全用于格式与离线流程演示，不代表已取得的真实 NVIDIA 原件、人工核准、市场观察或收益研究。

在已具备研究依赖的仓库环境运行：

```powershell
python -B tools/equity_source_task.py run --manifest examples/equity-source-task/manifest.synthetic.json
```

查看命令返回的报告目录中的 `index.html`。更换资料只需复制并编辑清单，不需改 Python 源码；详见[操作说明](../../docs/equity-source-task.md)。另有独立的[NVIDIA 两财季真实原件验收](../../docs/research-evidence/equity-source-task-20260927/README.md)，不能把本例的虚构数据当作该验收证据。
