# Host shared broker root handoff r1

Authoritative source: `C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易`

Base HEAD: `4ae90471f83afbdca9ef4e421e064690ede2b01d`; this report covers the current uncommitted host changes only.

## Implemented contract

- `brokerSharedRoot({ localAppData, home, appData, platform = process.platform, programRoot })` resolves and validates an absolute physical root without creating it.
- Windows uses trusted host `localAppData`, falling back to absolute `home/AppData/Local`. Linux/macOS require the host's absolute `appData`. The suffix is always `HakimiTradeTerminal/broker-shared-v1`; workspace, installation and bundle/version never select it.
- Existing reparse/link and program-directory rejection remains. Missing directories are not recursively created by this helper/context; Python must recheck before first write.
- `createContext` returns `brokerSharedRoot` and `brokerSharedRootId`; development startup fixes both in `WORKSPACE_CONTEXT` before launch.
- Both launch paths remove inherited `HAKIMI_BROKER_SHARED_ROOT` keys, including case variants, and supply the fixed host value.
- `brokerSharedRootIdentity(root, platform = process.platform)` is SHA256 of UTF-8 `hakimi-broker-shared-root-v1\0` + platform normcase(physical absolute root) + `\0EXTERNAL_RECORD`. `\0` here means a NUL byte. Windows replaces `/` with `\` and lowercases; Linux/macOS preserve case.
- `matchesBackend` requires exact health `broker_shared_root_id` equality in addition to existing package/mode/workspace checks. Missing, null, changed or malformed expected identity cannot attach. There is no old-health compatibility exception.
- This path/identity binding is not broker/account authentication or external execution authorization. Existing workspace singleton semantics remain unchanged.

## Files changed

- `outputs/hakimi_trade_electron/terminal-package-runtime.js`
- `outputs/hakimi_trade_electron/main.js`
- `outputs/hakimi_trade_electron/terminal-package-runtime.test.js`
- `outputs/hakimi_trade_electron/desktop-lifecycle.test.js`

## Validation and scope

- Node v22.23.4 targeted tests: **47/47 PASS**, 0 skipped: runtime 24, lifecycle 23. See `host-node22-targeted-r1.log`.
- Earlier Node22 runtime-only pass: 24/24, retained as `host-node22-runtime-r1.log`.
- Actual Node22 helper vs Python `os.path.normcase`/hashlib on a new, nonexistent Unicode/space path: PASS; no directory created. See `host-node22-python-identity-r1.log`.
- Node22 syntax checks for all four changed files and `git diff --check`: PASS. See `host-node22-checks-r1.log`.
- Linux/macOS branches and case rules were tested using explicit platform inputs on Windows. This is not an actual Linux/macOS CI run.
- Prior Node24.16.0 results (runtime 23 + lifecycle 22) preceded the health-identity extension. They were tool-output-only; no historical log was fabricated.
- No actual Electron/OpenD/provider/network activity, old business DB/profile access, installation, commit or push was performed. Test child creation is replaced with isolated fixtures.
- Root still owns Python `TrustedBrokerRoot`, service/control routing and health production, plus the final complete desktop/package gate. This handoff does not claim those checks passed.

Exact source/log/handoff SHA256 values are in `host-SHA256-r1.json`.
