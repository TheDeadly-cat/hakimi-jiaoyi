# 固定运行件与有限观察窗口

状态：准备实现已完成，尚未注册或启用 OS 任务。174 项仓库配套测试通过，其中包含 66 项观察组件检查；这些计数相互包含。原生通知显示和冻结链路故障恢复的既有证据保留各自代码身份，本次仍需实际固定运行件预演。

`tools/observation_bundle.py create` 从已提交且与 HEAD 一致的六个控制脚本复制精确本机字节，写入新的本地目录。它保存 Git 提交、文件 SHA-256、独立巡检计划和原安装环境预检。目录与原冻结部署分离，观察与巡检回执也各用一个子目录。清单含本机绝对路径，不应原样上传 GitHub；摘要用于检测漂移，不是抵御本机管理员的签名。

```powershell
# 使用已确认的实际部署路径和未来 UTC 整点；新目录不可复用。
python -I -B tools/observation_bundle.py create --output $newBundle --runtime-root $runtimeRoot --start $futureUtcHour
& "$newBundle/tools/prepare_observation_task.ps1" -BundleRoot $newBundle
& "$newBundle/tools/prepare_observation_task.ps1" -BundleRoot $newBundle -ValidateDefinitions
```

创建要求开始时间至少晚于当前时间十分钟。最后一个命令仅通过 Windows Schedule.Service 在内存构造任务定义并输出 XML，不注册任务。过期计划必须另建目录和新窗口，不编辑已冻结清单。

| 角色 | 第一次触发 | 重复周期 | OS 执行期限 | 最后允许新运行 |
|---|---|---|---|---|
| HakimiReadOnlyObservation | 开始整点后 60 秒 | 每小时 | 10 分钟 | 开始后 72 小时之前 |
| HakimiObservationWatch | 开始整点后 30 秒 | 每分钟 | 50 秒 | 窗口结束后 10 分钟之前 |

两项任务均使用固定运行件内的 `observation_bundle.py`、绑定清单摘要的命令参数和原安装环境 `pythonw.exe`。使用当前用户 InteractiveToken、Limited、IgnoreNew、WakeToRun 和 StartWhenAvailable。用户需要保持登录且机器可用；关机无法采集或实时本机告警。

观察进程还直接接收声明窗口边界，窗口外拒绝采集。巡检可以在窗口开始前人工预演，只记录尚未应到的状态。窗口结束产生一次“等待验收”事件，绝不自动判为通过；巡检额外十分钟用于最终状态及待发通知。随后这两项试运行停止，旧 heartbeat 不会自动恢复。到期后的持续运行安排需要维护者决定。

每次固定入口先保存启动回执，核对六个脚本和计划，再有界调用子进程并核验其实际保存的结果。进程退出 0 缺少相符回执仍失败。观察子链最多 340 秒加 5 秒清理，巡检子链最多 40 秒加 5 秒清理；内部观察和通知各自保留更早期限。OS 期限是最后一道限制，不替代回执判定。

激活前仍须取得明确的维护者批准，并通过应用暂停旧 heartbeat、核对单一调度权。只有这些步骤已完成后才可从固定运行件调用 `-Apply -SchedulingAuthoritySwitchConfirmed`。脚本先拒绝已有同名任务，再用 TASK_CREATE 创建两项禁用任务，保存注册回执后启用巡检、再启用观察。任何注册、启用或结束回执错误都会尝试禁用本次已创建任务并保留失败记录。仅在核实所有新任务确已禁用后，才能恢复旧 heartbeat。

本次新增测试检查文件与计划漂移、清单绑定、两项期限、窗口外不执行、子链边界失败及退出 0 无有效回执。它们不注册任务，也不代表新 72 小时已经经历或股票采集已上线。
