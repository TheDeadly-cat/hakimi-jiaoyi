# Deterministic Research Example

This package is a source-controlled, local-only identity fixture for the active
historical-backtest CLI.

- `dataset.csv` is synthetic and contains no market observations.
- `config.json` uses only the CSV provider and disables cache use.
- `expected_result.json` records input hashes, row count, and permanent authority
  locks. It deliberately contains no performance metric.
- `verify.py` checks the package without starting a service, accessing a network,
  or running a backtest.

Run the identity check from the project root:

```powershell
python -B examples/deterministic_experiment/verify.py
```

A passing identity check proves only that these example inputs match their
source-controlled expectation. It is not strategy evidence, a profitability
claim, ranking permission, paper authority, live authority, or order authority.
