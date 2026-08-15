# 哈基米交易 v2 Software Plan

哈基米交易 v2 is the second-generation desktop direction for this project.

## Current Software Shape

The app still runs a local Python backend and a browser-based trading terminal, but it now has a desktop launcher:

```text
outputs/Hakimi_Trade_V2_START.bat
```

The launcher runs:

```text
outputs/python_quant_bot/hakimi_trade_desktop.py
```

If `pywebview` is installed, it opens as an embedded desktop window. Otherwise, it starts the local server and opens the default browser.

## Build Target

The PyInstaller build entry is:

```text
outputs/python_quant_bot/build_hakimi_trade_v2.bat
```

If desktop packaging dependencies are missing, run:

```text
outputs/python_quant_bot/install_desktop_dependencies.bat
```

Expected output:

```text
outputs/python_quant_bot/dist/HakimiTradeV2
```

When packaged, runtime state, logs, exports, and local account files are written under the Windows user data directory:

```text
%APPDATA%\HakimiTradeV2\runtime
```

## Product Name

- App name: `哈基米交易`
- Version: `v2`
- Internal version: `2.0.0-alpha`

## Safety Position

- Live trading remains blocked by default.
- AI cannot auto-apply code patches.
- Stocks are research-only until a dedicated broker adapter is added.
