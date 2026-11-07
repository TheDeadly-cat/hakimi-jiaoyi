# r7：公开试用候选与验证范围

**r7已于2026-11-08（北京时间）公开预发布。** [Release页面](https://github.com/TheDeadly-cat/hakimi-jiaoyi/releases/tag/v0.7.0.dev3-r7)的发布编号为437755706，标签`v0.7.0.dev3-r7`指向`708ec3f08abdeeae2578726b765483c8c109daa9`，`prerelease=true`、`draft=false`。最新稳定版仍为`v0.2.1`；[PR #26](https://github.com/TheDeadly-cat/hakimi-jiaoyi/pull/26)保留草稿、未合并状态。

| 公开附件 | 字节数 | SHA256 |
|---|---:|---|
| [Windows程序ZIP](https://github.com/TheDeadly-cat/hakimi-jiaoyi/releases/download/v0.7.0.dev3-r7/HakimiTrade-0.7.0.dev3-candidate-r7.zip) | 193,297,558 | `9d136498983732b915366242ddd0c347c0a6af833000ea182f3ea4e58247b45f` |
| [试用资料ZIP](https://github.com/TheDeadly-cat/hakimi-jiaoyi/releases/download/v0.7.0.dev3-r7/HakimiTrade-0.7.0.dev3-r7-trial-materials.zip) | 444,897 | `dcf1c4dd6c2ea8c7052db499662fce0cc6caa5108821968038ba2fc191622deb` |
| [SHA256与大小清单](https://github.com/TheDeadly-cat/hakimi-jiaoyi/releases/download/v0.7.0.dev3-r7/release-SHA256SUMS-r7.txt) | 444 | `e3223aba13d4cb578c4c6fce3630e5de1658e8dcabe4200576697801e0b0cf6e` |

[发布身份](public-release-identity.json)记录一次GitHub只读GET复核：标签、发布标志、稳定版与三个附件摘要均符合原发布回执。发布时三个附件均通过无认证HEAD 200及大小核对；本次文档整理没有重复下载大包。[验证摘要](verification-summary.json)保留相关回执的文件名和SHA，不公开本机绝对路径或聊天审批标识。

## 构建与包内证明

- 源码`708ec3f`对应[CI177 / run42398287158](https://github.com/TheDeadly-cat/hakimi-jiaoyi/actions/runs/42398287158)，11/11作业全部成功。
- Bundle：`9720f8274d460c20662cf9551b15b6ddc9bed5d5ccc4c3cb0312d815d094c0cf`；manifest SHA256：`db2e63e4b02a49d35bcfe612ce28e6a2dc26e1bf9677ffbf015a5d91a372859c`。
- 9,091个程序文件、9,092个ZIP条目与1,058个源码记录逐项核对；包内18个界面模块及实际拼接脚本共19项语法检查通过。
- 构建只执行一个全新临时虚构样例，保存与读回不重复计算。附加验包已完成，但没有新增经济运行；真实行情、历史重放、模型和券商请求均为0。
- 协调器及工作进程入口只通过包内默认拒绝检查和内存STOP-only夹具；没有创建协调器实例、启动真实worker或派发订单。后续本机回环socket工程属于新的源码，未打入r7。

## 使用与尚待完成的验收

程序ZIP解压到新目录后打开`HakimiTrade.exe`。试用资料ZIP含14份冻结文件，说明与填写记录留在程序目录外。任务包括保存本地演练计划、关闭重开找回同一计划及记录是否重复保存，不要求提交订单。资料内保留的预发布草稿和候选身份是发布前快照；当前公开状态以Release页面和本目录身份为准，原14文件没有为发布重新改写。

**r7原生窗口、独立Windows和三名独立新手均尚未实际验收。** 用户已确认另一台Windows可使用普通用户，只复制程序包、不放源码，三名未参与开发者也可安排；环境与人员就绪不代表通过。U02仅“准确候选公开交付”已完成，其他验收与完整目标仍待推进。

[r6本机原生记录](../terminal-070dev3-r6-native-20261108/README.md)保留其原版本身份，不能转记为r7验收。旧r6/r5、原失败回执与历史UNKNOWN保持原状态；此次发布未启用真实交易。

[SHA256SUMS.txt](SHA256SUMS.txt)覆盖本目录其余三个文件。本次只整理文档及公开元数据，没有修改源码、重新测试、运行应用或改变发布资产。
