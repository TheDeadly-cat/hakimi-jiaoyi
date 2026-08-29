# ADR-0006: Canonical JSON Hash 的低层依赖边界

## 状态

已实施行为零变化迁移；旧 Hash 合同与 import 路径保持兼容。

## 问题

canonical_hash 原定义在 strategy_matrix_protocol。strategy-correlation-uncertainty-audit 与 multiplicity audit 只是为了计算 canonical Hash，却必须依赖高层 protocol 模块，形成统计服务到协议层的反向依赖，并增加未来循环 import 风险。

## 决策

把既有函数原样提取到 exchange_terminal/services/canonical_json_hash.py：

- json.dumps 使用 ensure_ascii=True
- key 排序
- separators 为逗号和冒号的紧凑形式
- legacy default=str
- UTF-8 编码后计算 SHA-256

strategy_matrix_protocol 继续 re-export 同一 canonical_hash 函数对象，因此所有旧消费者和外部 import 不需要迁移。uncertainty 与 multiplicity 服务改为直接依赖低层 utility。

## 兼容边界

本 ADR 不定义新 Hash schema，也不改变任何既有 artifact Hash。None、布尔、整数、浮点、Unicode、数组和嵌套对象的 golden digest 必须逐位保持。

legacy default=str 仅为兼容既有合同保留。它不是任意 Python 对象进入正式 artifact 的授权。正式 builder/verifier 仍必须先执行 exact fields、原生类型、有限数值与 authority 检查。若未来需要 strict native-only canonicalization，必须新建版本化 Hash 合同和迁移计划，不能修改本函数语义。

## 验证

- canonical golden 与 identity：3/3 PASS
- matrix protocol：12/12 PASS
- uncertainty audit：9/9 PASS
- multiplicity audit：7/7 PASS
- 合计：31/31 PASS
- 隔离 py_compile：PASS
- matrix protocol、uncertainty 与 multiplicity 在运行时引用同一个低层函数对象
- lean test/syntax 显式登记，dry-run executed 0
- current、paper 与 live 权限未变化

## 日期

2026-08-21