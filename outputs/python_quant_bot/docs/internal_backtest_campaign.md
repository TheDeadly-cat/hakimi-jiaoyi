# 内部回测战役

## 定位

内部回测战役用于证明一个已冻结候选能否在封存源码和封存数据上被重复、隔离地复放。它只回答“历史结果能否稳定重现”，不回答“未来是否盈利”，也不产生模拟盘或实盘权限。

## 前置条件

- 活动候选及实现指纹校验为 `PASS`。
- 最新证据归档校验为 `PASS`。
- 内部回测包状态为 `INTERNAL_BACKTEST_EVIDENCE_READY`。
- 战役契约必须在第一次复放前单独落盘，文件已存在时拒绝覆盖。

## 运行

在 `outputs/python_quant_bot` 中执行：

```powershell
python run_internal_backtest_campaign.py --repetitions 3 --timeout-seconds 120
```

默认读取 `runtime/reports/portfolio_forward_backup_status.json` 指向的最新活动候选归档，并在 `runtime/reports` 中创建一份契约和一份报告。也可以通过 `--archive` 指定归档，但归档必须属于当前活动候选。

## 固定约束

- 每次复放使用新的 Python 隔离进程和归档内源码。
- 只读取归档内冻结数据集，不访问实时行情。
- 网络访问和可变数据库访问必须为 0。
- 固定次数必须全部执行，不允许失败后提前停止并挑选成功结果。
- 复放前后归档文件清单、大小和 SHA-256 必须完全一致。
- 所有复放结果必须与归档排练哈希一致，并在不同进程间保持一致。
- 参数搜索、开发试验增量、独立样本增量和前向样本增量均固定为 0。
- `automatic_paper_activation_allowed`、`paper_authorized`、`live_order_allowed` 永远为 `false`。

## 结果解释

`INTERNAL_BACKTEST_CAMPAIGN_PASS` 表示封存结果可复现，结论固定为 `REPRODUCIBILITY_PASS_NOT_PROMOTION_EVIDENCE`。只有自然到来的、候选激活后的前向数据才能增加前向观察与收益期；重复运行历史回测不能替代这一过程。

`INTERNAL_BACKTEST_CAMPAIGN_BLOCK` 表示至少有一项复现、隔离、绑定或归档完整性检查失败。失败报告可以保留用于排障，但不能被改写为通过，也不能触发模拟盘或实盘。
