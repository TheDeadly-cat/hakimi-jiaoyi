# T5：本机通知投递与实际显示回执

Windows已报告显示一次“演练：哈基米研究观察”通知，编号 `7cc48ffe`，时间为 `2026-09-12T20:17:28.5965564Z`。它绑定前一轮隔离副本的实际恢复回执。重复调用没有再次启动通知程序，投递尝试仍为一次，已有文件摘要不变。[native-drill.json](native-drill.json)保存内容、原生回执、源码身份与去重核对结果。

这次证据是操作系统发出的 `BalloonTipShown` 显示事件，而非仅调用接口成功或进程退出0；Microsoft将该事件定义为通知已在屏幕显示。未发生点击事件，通知关闭也没有被当作用户已看见。用户是否实际看到已另行询问，当前仍待回复。[Microsoft显示事件说明](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.notifyicon.balloontipshown?view=windowsdesktop-10.0)

## 实现及边界

`tools/observation_notify.py`读取一对绑定且摘要正确的启动器v2回执，核对启动器、冻结包装器、计划身份和禁单状态。只使用已知健康分类构造固定中文提示，不把回执里的任意异常文本、文件路径或外部指令放进通知。默认仅预览；显式`--send`才投递，`--drill`使标题与正文明确标为隔离演练。它不运行采集器、修改原观察结果或注册调度。

发送器先以不覆盖方式保存通知内容和尝试开始记录，然后调用有限Windows助手。通过同一outbox的OS锁排除并发，已显示或结果未知的尝试不会自动重发；进程中断留下开始而无结束记录时，后续返回`DELIVERY_UNKNOWN_PRIOR_ATTEMPT`。只有助手明确尚未提交的用户状态阻止情况，才允许至少间隔5分钟、至多3次的后续调用重试；工具自己不常驻或安排重试。这个去重范围是同一份冻结通知内容与同一权威outbox，不是跨复制目录的全局恰好一次保证。

`tools/show_observation_notification.ps1`使用临时任务栏通知图标，按系统通知状态处理静默、锁屏或演示等情况，不修改系统通知设置。发送、系统显示、点击和关闭分别记录真实UTC时间，结束时释放临时图标；助手最多保留20秒消息循环，外层执行上限25秒、清理3秒、输出合计16 KiB。Windows控制实际显示时长，代码传入的显示期限不被当作显示或用户阅读证据。[Microsoft通知区域规则](https://learn.microsoft.com/en-us/windows/win32/shell/notification-area)、[显示时长说明](https://learn.microsoft.com/en-us/dotnet/api/system.windows.forms.notifyicon.showballoontip?view=windowsdesktop-10.0)

本次实际投递使用归档发送器字节`4f863283ad9145e232ed780334ae0611b0624b8026d7a8860efd532f331ec37b`；后续加入事件先后顺序校验，并在新尝试中记录发送器摘要。Windows助手字节未变。最终候选对原通知只做去重核对，没有重新投递、修改原件或把旧显示证据改签给新代码。

## 验证与使用

14项针对性检查通过，覆盖来源/权限绑定、预览无副作用、未知正文不外泄、未显示不确认、并发去重、真实子进程`os._exit(73)`后的不确定状态、有限重试、篡改outbox、错误关联及错误时间顺序。148项仓库配套检查通过，包含这14项。CI里的通知结果均使用明确替身，原生Windows显示单独以本轮真实回执证明。

先运行预览并核对内容，再在已选定的本机渠道范围内投递：

```powershell
python -I -B tools/observation_notify.py --receipt '<chosen-ended.json>' --outbox-root '<outbox-directory>' --drill
python -I -B tools/observation_notify.py --receipt '<chosen-ended.json>' --outbox-root '<outbox-directory>' --drill --send
```

输入应是原启动器的`ended.json`且同目录保留`started.json`；不能输入公开投影代替原件。回执所用启动器摘要默认应与工具目录中的启动器相符，重放审查其他已核对的原件时可显式提供其摘要。示例中的路径占位符须替换为自己的原件与独立outbox。

## 未完成事项

后续：[独立回执巡检](../observation-watch-20260913/README.md)已实现无启动、无结束与恢复核对，并完成CLI及到Windows显示的完整链路演练；尚未注册成OS任务。原JSON保留本次投递增量的证据快照，不改写其历史状态。

这一增量是投递部件，独立巡检功能已由后续模块补齐。新计划与运行件固定、OS接入、维护者批准下的单一调度权切换以及新的72小时实际观察仍須继续完成。当前没有注册新任务、改变原heartbeat或修改交易权限。单台机器断电期间无法靠自身实时显示通知；本机渠道的可用边界必须保留。
