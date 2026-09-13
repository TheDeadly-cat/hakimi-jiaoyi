# 固定运行件与有限观察窗口

状态：[授权后的实际调度切换](research-evidence/observation-activation-20260913/README.md)已完成，旧 heartbeat 已暂停，两项 OS 任务已注册并启用。首轮暴露宿主 AppData 路径问题，[修复后的人工恢复重试](research-evidence/observation-activation-20260913/first-cycle-recovery.md)得到两个迟到但可重放的结果，巡检保留首次期限失败，通知显示仍被系统用户状态延后。声明窗口为北京时间 2026-09-13 12:00 至 2026-09-16 12:00，巡检至 12:10；下一自然小时和完整 72 小时仍待验收。[先前预演](research-evidence/observation-control-20260913/README.md)保留历史范围。

`tools/observation_bundle.py create` 从已提交且与 HEAD 一致的六个控制脚本复制精确本机字节，写入新的本地目录。它保存 Git 提交、文件 SHA-256、独立巡检计划和原安装环境预检。目录与原冻结部署分离，观察与巡检回执也各用一个子目录。清单含本机绝对路径，不应原样上传 GitHub；摘要用于检测漂移，不是抵御本机管理员的签名。

```powershell
# 使用已确认的实际部署路径和未来 UTC 整点；新目录不可复用。
python -I -B tools/observation_bundle.py create --output $newBundle --runtime-root $runtimeRoot --start $futureUtcHour
& "$newBundle/tools/prepare_observation_task.ps1" -BundleRoot $newBundle
& "$newBundle/tools/prepare_observation_task.ps1" -BundleRoot $newBundle -ValidateDefinitions
```

创建要求开始时间至少晚于当前时间十分钟。最后一个命令仅通过 Windows Schedule.Service 在内存构造任务定义并输出 XML，不注册任务。过期计划必须另建目录和新窗口，不编辑已冻结清单。

预检还必须逐一打开 `deployment-plans.json` 中的绝对计划引用，核对目录及钉住的内容身份。创建时的进程视图不必然与原生 Task Scheduler 相同，特别是应用管理的 AppData 重定向。实际注册后应在窗口前从 Windows 任务入口调用观察，检查有效保存的 `prewindow_runtime_preflight`；窗口外跳过本身不足以证明路径可达。新的源码入口在窗口前执行这项只读预检，绝不调用采集器；缺失引用、目录外引用、重复或摘要不符均失败。

此修复的14项针对性检查及179项仓库配套检查通过，计数相互包含；新函数已在实际原生 Windows 任务中验证。当前已激活 bundle 保持原六个脚本字节，宿主路径修复后的观察使用原 bundle；源码预检修复没有原位部署到既有72小时窗口。

| 角色 | 第一次触发 | 重复周期 | OS 执行期限 | 最后允许新运行 |
|---|---|---|---|---|
| HakimiReadOnlyObservation | 开始整点后 60 秒 | 每小时 | 10 分钟 | 开始后 72 小时之前 |
| HakimiObservationWatch | 开始整点后 30 秒 | 每分钟 | 50 秒 | 窗口结束后 10 分钟之前 |

两项任务均使用固定运行件内的 `observation_bundle.py`、绑定清单摘要的命令参数和原安装环境 `pythonw.exe`。使用当前用户 InteractiveToken、Limited、IgnoreNew、WakeToRun 和 StartWhenAvailable。用户需要保持登录且机器可用；关机无法采集或实时本机告警。

观察进程还直接接收声明窗口边界，窗口外拒绝采集。巡检可以在窗口开始前人工预演，只记录尚未应到的状态。窗口结束产生一次“等待验收”事件，绝不自动判为通过；巡检额外十分钟用于最终状态及待发通知。随后这两项试运行停止，旧 heartbeat 不会自动恢复。到期后的持续运行安排需要维护者决定。

每次固定入口先保存启动回执，核对六个脚本和计划，再有界调用子进程并核验其实际保存的结果。进程退出 0 缺少相符回执仍失败。观察子链最多 340 秒加 5 秒清理，巡检子链最多 40 秒加 5 秒清理；内部观察和通知各自保留更早期限。OS 期限是最后一道限制，不替代回执判定。

激活流程要求明确的维护者批准，并通过应用暂停旧 heartbeat、核对单一调度权。本次已经完成这些步骤，再从固定运行件调用 `-Apply -SchedulingAuthoritySwitchConfirmed`。脚本先拒绝已有同名任务，再用 TASK_CREATE 创建两项禁用任务，保存注册回执后启用巡检、再启用观察。任何注册、启用或结束回执错误都会尝试禁用本次已创建任务并保留失败记录。仅在核实所有新任务确已禁用后，才能恢复旧 heartbeat。

本次新增测试检查文件与计划漂移、清单绑定、两项期限、窗口外不执行、子链边界失败及退出 0 无有效回执。它们不注册任务，也不代表新 72 小时已经经历或股票采集已上线。
