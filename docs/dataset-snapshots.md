# Dataset versions and CSV admission

Version 0.2 creates `research-dataset-snapshot-v2` documents. A stable
`dataset_series_id` names the source/market family; `dataset_id` identifies the
specific raw bytes, normalized candles, metadata and recorded predecessor.
`snapshot_id` seals the complete document. Raw-content revisions therefore get
new dataset and snapshot identities even when normalized values are unchanged.

An optional `--predecessor` supplies an existing snapshot. Import validates that
document and its market, symbol, period and units before recording
`previous_snapshot_id` and `previous_dataset_id`. Compact references avoid
embedding an ever-growing parent chain. Plain loading labels a parent reference
`RECORDED_REFERENCE`; it does not claim to have loaded the parent. Use
`verify_lineage(child, parent)` to independently verify both documents and the
reference offline. Missing parents do not prevent replay of the child's own
complete stored raw input. A reference is not provider authentication.

Version 1 snapshots retain their original reader, dataset names and hashes. They
can be supplied as predecessors for version 2; migration creates a new artifact
without changing the old one. The preserved 0.1.0 wheel generated the small v1
regression fixture under `tests/fixtures`; no old market snapshot or existing
frozen reference was regenerated.

## CSV input

Use `hakimi-research snapshot-import --csv "bars.csv" --metadata "metadata.json"
--output-dir "research data"`. Revisions additionally supply `--predecessor
"research data/datasets/dataset_<previous hash>.json"`.

The UTF-8 CSV must have exactly these columns in this order:

```csv
time,open,high,low,close,volume
2024-01-01T00:00:00Z,100,102,99,101,10
```

Rows must be strictly ascending, unique, hourly UTC bar-open timestamps. Values
must be finite, prices positive, volume nonnegative, and high/low geometry valid.
Every requested hour must exist; errors identify timestamps and row positions.
The metadata must contain exactly the following fields, with real values chosen
by the importer:

```json
{
  "market": "crypto_spot",
  "instrument_type": "SPOT",
  "symbol": "BTC-USDT",
  "timeframe": "1h",
  "source": "Describe the actual export source and its provenance",
  "retrieved_at": "2024-01-02T00:00:00Z",
  "as_of": "2024-01-01T01:00:00Z",
  "volume_unit": "base_currency",
  "quote_unit": "USDT",
  "timezone": "UTC",
  "start": "2024-01-01T00:00:00Z",
  "end_exclusive": "2024-01-01T01:00:00Z",
  "completed_bars_only": true
}
```

`completed_bars_only` is an explicit importer declaration. CSV cannot attest OKX
`confirm` flags or HTTP capture: its evidence is always `IMPORTED_UNVERIFIED`,
its authentication status is `IMPORTER_DECLARATION_NOT_VERIFIED`, and the
quality record states `IMPORTER_DECLARATION_ONLY`. Source labels cannot elevate
that status. Both the exact CSV byte hash and normalized candle hash are stored.
Changes to labels also change the version identity and remain visible.

Applications may instead supply a `csv-ohlcv-capture-v1` JSON document containing
exactly `schema_version`, `raw_base64` and the same `metadata`; `--capture` uses
the same admission rules. Neither CSV nor OKX capture import contacts a provider,
fills missing rows, refreshes a cache, or fabricates substitute data.
