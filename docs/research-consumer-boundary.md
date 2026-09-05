# Research consumer and management boundary

The research MVP ships the installed CLI and validated JSON reports. `report-show`
is a file reader in the canonical package. It must not import the legacy server,
start a backend, acquire an account, modify a report, or open a Provider.

The Electron application is labelled **Legacy Preview** in its persistent window
title. It still renders the old terminal and the separate
`signal-close-next-open-ohlc-conservative-v3` implementation. These preview results
are not formal ExperimentRunner reports and must not be combined with them.
Desktop packaging and interactive runtime acceptance remain outside this MVP.

## Route inventory and disposition

| Routes | Existing handler | Previous permission checks | Possible side effect | Current disposition |
| --- | --- | --- | --- | --- |
| `/api/ai/deepseek/code-worker/run` | `deepseek_code_worker` | Loopback, POST, local write header, idempotency journal | Provider call, draft and ledger writes | Removed from POST/mutation registry; GET and direct dispatcher return 404 |
| `/api/ai/deepseek/code-worker/archive` | `archive_code_worker_draft` | Same mutation checks | Draft file write | Removed from registry and dispatcher |
| `/api/ai/deepseek/code-worker/drafts` | `read_code_worker_drafts` and `deepseek_status` | Loopback GET | Read draft/config state | Retired from dispatcher with the worker surface |
| `/api/ai/runtime-keys`, `/api/ai/runtime-keys/clear` | `set_runtime_ai_keys`, `clear_runtime_ai_keys` | Loopback POST and allowed Origin when supplied | Runtime credential state | Removed from POST registry; GET/dispatcher return 404 |
| `/api/futu/configure` | `configure_futu_opend_credentials` | Loopback POST and allowed Origin when supplied | Credential/configuration persistence and OpenD management | Removed from POST registry; GET/dispatcher return 404 |
| `/api/futu/verify-code` | `submit_futu_phone_verify_code` | Same POST checks | OpenD verification action | Removed from registry and dispatcher |
| `/api/futu/enable-telnet` | `ensure_futu_telnet_config` | Same POST checks | OpenD configuration | Removed from registry and dispatcher |
| `/api/health` | `build_health_response_from_runtime` | Loopback GET | In-memory status reads | Preserved; shell requires read-only true, mutations false, guardian false and paper unarmed |
| `/api/ai/runtime-keys/status` | `runtime_ai_key_status` | Loopback GET | Credential-presence status reads | Preserved; no key write permission |
| `/api/futu/status` | `futu_status_snapshot` | Loopback GET; trusted Origin for force | Existing OpenD/status observation, which can check local services | Preserved as a legacy status route, outside offline CLI and not invoked in validation |

The server defaults to read-only if the setting is absent, empty or unrecognized.
Existing POST guards reject remaining mutations and the guardian is not started.
An explicit legacy writable flag does not restore the retired routes or grant
paper/live/order authority. The desktop enforces read-only in its child environment
and rejects a pre-existing backend that lacks the read-only health assertions.
This is a narrow inventory of the reviewed management surfaces, not a claim that
every legacy GET has no I/O; the formal offline report consumer avoids that server.

The existing service accepts only loopback bind/client hosts. Origin validation
restricts browser requests to local HTTP origins with explicit ports; state
mutations also require the existing write/idempotency checks. POST body limits
range from 4 KiB to 180,000 bytes by route, before parsing. These are existing
legacy controls, not a newly accepted session-authenticated report-serving API.
The formal CLI has no HTTP session or served report root. Publishing this service
would still require a separately reviewed Host/Origin/session/report-root
contract and interactive acceptance; it is excluded from the CLI-only release.

## Desktop policy and evidence

Untrusted navigation, redirects and popup URLs pass through one policy before an
OS external opener is reached. Only absolute HTTPS links without credentials,
controls or parser-ambiguous backslashes may be opened externally. Internal
navigation requires the exact local HTTP origin or exact bundled boot file.
Popups are denied and valid internal links reuse the protected window.

Packaged builds remove remote-debugging switches even when a debug environment
variable or command-line switch is present. Only an unpackaged developer build
with a valid numeric port can enable debugging, bound to 127.0.0.1 without wildcard
origins. The existing sandbox, context isolation, disabled Node integration and
web security settings remain enabled.

A pre-existing listener that fails the read-only contract is left untouched and
reported for manual resolution. Port/process-name/relative-path stop guesses are
disabled. Shutdown may stop only a still-live direct ChildProcess handle the
shell created, with exit/signal/killed state checked; it never runs taskkill or
looks up an arbitrary port owner's PID. This does not claim cleanup of all
descendants of the legacy PowerShell launcher.

Validation uses pure policy callbacks and AST-isolated copies of the actual HTTP
methods with fake handlers. No Electron app, HTTP listener, Provider, OpenD or
management endpoint is launched. These checks cover the enforcement decisions and
preserved status registrations; they are not packaged-desktop runtime acceptance.
The policy follows [Electron navigation and external-link guidance](https://www.electronjs.org/docs/latest/tutorial/security).
