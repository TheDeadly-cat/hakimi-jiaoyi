# Legacy paper execution archive

This directory preserves the retired continuous `TradingEngine`, the former
`PaperBroker` execution module snapshot, and their dedicated selector and
reservation tests. They are historical review material only and are outside the
importable product source.

Archived SHA-256 values:

- `execution_with_paper_broker.py`: `f1399e616f761475e4a17a6908c7732088e2e1e28519d43c3c9f58e14962d14e`
- `engine.py`: `a896c07c1037ebac4dc745a0a1aeb0a986149f078343930342d2f53572ec2d2a`
- `tests/test_quant_bot_engine_decision_reservation_v1.py`: `aa221d62e7e881a48987a2870309a9a55e61c3832d4676b69aff7776b2d047fb`
- `tests/test_quant_bot_broker_selector_fail_closed_v1.py`: `fa45a162cd307dcc0b86846359b38e55e1f6bbeeeca3c8a62e13e6b111ef6010`

Formal source retains only a deterministic in-memory
`ResearchExecutionSimulator` used by BacktestEngine. It is not a paper account,
broker, order service, or paper/live authority.

## ADR0522 Exchange Terminal paper account archive

The legacy Exchange Terminal `PaperAccount` and paper strategy clock were moved
out of formal product source after the server switched to the immutable archived
runtime facade. These files are historical review material only and are not an
importable package.

Archived SHA-256 values:

- `exchange_terminal_services/paper_account.py`: `656ca2609543e220188b2d13ba641d01a497ac0db7b4a0ba05a8dc7a5d02a428`
- `exchange_terminal_services/paper_strategy_clock.py`: `b0b4be66f4003fc7476ff1f3ace0cc6bc38af54b19fd404087e3deb9433bc24b`
- `tests/test_paper_strategy_clock.py`: `cd61c974a6a768d06465d6ed0e781c59a48671fdc8a26045a1cd1603d3e64fb1`
- `tests/test_core_services_before_paper_account_archive.py`: `e3e5963b79a04af9be7c2e644fc2f4f1650a7e3395520d46d0f2a2f1098e8c74`

The shared test snapshot preserves the exact pre-archive context. Formal tests
remove only the nine methods that instantiated or validated the retired account.
`PaperExecutor`, `PaperLedger`, portfolio paper persistence, and execution
rehearsal remain outside this slice pending their own consumer-first audit.

## ADR0523 Exchange Terminal paper persistence archive

The legacy Exchange Terminal SQLite paper ledger, portfolio paper account, and
portfolio paper activation modules were moved byte-for-byte out of formal source.
They are non-importable historical review material and do not represent a
supported persistence or execution capability.

Archived SHA-256 values:

- `exchange_terminal_services/paper_ledger.py`: `b3380975818f4ab0f190f978cbed528e45903aca1c77168ac6510dd6362752a1`
- `exchange_terminal_services/portfolio_paper_account.py`: `75bfdaa68b1407d1085a7867e4ed0c5383125bafce569d173e245e2c2a84fd06`
- `exchange_terminal_services/portfolio_paper_activation.py`: `ec13b2ae1c5a9362bf810e9eb4917a14ed88117ef292e57907cc2566ac72f1fa`
- `tests/test_portfolio_paper_account.py`: `5b2eb1952b990bf9524833a058995298b66e383363f1365fafcc1597636c870a`
- `tests/test_core_services_before_paper_persistence_archive.py`: `3a1fd3c4cbb3d838c76b6a56baa4fdad967f49937453d75bf9bb7ffedb53feb3`
- `tests/test_runtime_sqlite_read_only_before_paper_persistence_archive.py`: `2513b88af119786580d7f376eb0386a3174e45fbd8874e543e00d4429fa1fc57`

Formal runtime read-only tests retain coverage for eight supported non-paper
ledgers. `PaperExecutor`, the paper order contract, and portfolio execution
rehearsal remain formal source pending a separate research-simulator migration.

## ADR0524 research execution rehearsal migration

The historical paper_executor.py, paper_order_contract.py, their dedicated
identity test, and pre-migration consumer snapshots are retained here as
byte-identical evidence. Current formal consumers use the versioned,
pure-in-memory src/hakimi_research/research_execution_rehearsal.py boundary.
The legacy paper_signal and paper_order_transition names survive only as the
explicit paper-lifecycle-v1 replay wire schema. This archive grants no paper,
live, or order-entry authority.
