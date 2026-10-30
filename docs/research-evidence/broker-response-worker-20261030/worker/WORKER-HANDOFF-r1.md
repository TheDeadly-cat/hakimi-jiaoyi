# 有界 worker supervisor 源码交接

仅新增两个文件；当前22个测试方法。证据按真实阶段保留：focused-r1为首轮19项PASS；targeted-additional-r2为新增3项PASS但包含cleanup后stdin未闭的ResourceWarning；targeted-idle-release-r3只复验修正后的相关1项PASS，明确检查闲置句柄关闭、原UNKNOWN投影不改，ResourceWarning设error。未另跑最终完整22项；根代理统一fullgate将覆盖最终源码。

API：create_output_parent(abs_new_path)独占创建目录并保存dev/ino；make_test_spec要求显式Python与entrypoint SHA256、entrypoint位于新fixture anchor；bind_package_spec绑定manifest声明字节，但所有PackageWorkerSpec launch固定PRODUCTION_ADMISSION_UNAVAILABLE。测试spec永远TEST_FIXTURE_ONLY，9权限false，不是生产准入。

launch(spec, *, output_parent, run_dir, run_id, request_id, limits)返回Handle。run_dir必须是anchor的直接新子目录，逐祖先拒reparse/escape并复核物理身份。固定-I -S -B -u -X utf8，显式executable，shell=False，Windows CREATE_NO_WINDOW；不继承旧Python路径/工作区/用户配置环境。没有全局Python fallback；测试使用当前测试解释器的明确实际路径/hash，仅作TEST_ONLY。

Handle.poll_message(timeout)只返回经schema/原ID/严格序号验证的READY/EVIDENCE/RESULT或None；Handle.reply接INPUT/STOP小信封，记录offered bytes与known/possible write计数；stop直接通知独立watchdog，不排管道队列。finish(timeout)返回最终回执或None；None不是成功/完成/未执行证明，应保留原请求待核对。close只停止当前拥有的子进程并有界等待，不重启/不重发。

watchdog与stdout/stderr读线程、stdin写线程、parent poll分离。墙钟/stop/cleanup单一总期限，超时、partial JSON、错ID、flood、child异常都UNKNOWN。晚到Popen handle仍立即kill；原UNKNOWN不重写。cleanup超时后只释放后来已闲置句柄，不再kill或重发。stdin/stdout/stderr、消息数、嵌套结构、证据总bytes与最终回执预留分别有上限；截断必标不完整。RESULT只协议消息，不表示经济事实或授权；exit0缺RESULT仍UNKNOWN。

边界：这是进程监管，不是OS sandbox、磁盘配额或生产授权。源码身份读取、CreateProcess/Popen与receipt文件IO属于OS操作，不能虚称其可被Python强中断；watchdog独立限制已拥有child和管道等待，finish超时真实返回None。父进程保留原request_id、可能派发范围与原bytes引用；root coordinator仍需实际事实/授权/journal关联。

所有执行只用本次新TEMP的合成Python子进程；没有SDK、OpenD、数据库、真实研究、旧数据或原生GUI。未改其他模块、runner、路由、包，也未commit/push。

最终SHA256：
- outputs\python_quant_bot\exchange_terminal\services\terminal_broker_worker_supervisor.py a0171cad253111d0ff857be935140377e0083376bcbd1084203c7e0c62475837
- outputs\python_quant_bot\tests\test_terminal_broker_worker_supervisor.py 4e343bef18d41a8d3f6270491a296116a8adb520c38ec59a80a315b671636a8b
