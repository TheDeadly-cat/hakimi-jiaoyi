# Shared account control service/route integration handoff r1

Authoritative repository: `C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易`

Base HEAD: `4ae90471f83afbdca9ef4e421e064690ede2b01d`. Only new source file: `outputs/python_quant_bot/tests/test_terminal_broker_account_control_integration.py`.

The new test class composes the existing `BrokerIntegrationTests` request/read helper without inheritance or re-export of its test class; only the new 11 cases are discovered. It uses real `TerminalResearchService`, `QuantWorkspace.handle`, saved candidate configurations, `SharedBrokerRoot`, account control stores, composed barriers and the trusted journal factory. Jobs are an immediate stub that invokes the real service mutation; this does not test durable Jobs scheduling.

Validation: **11/11 PASS**, see `service-route-integration-r2.log`. The earlier 9-case pass remains separately preserved in `service-route-integration-r1.log`. No production defect was observed in these cases.

Covered:

- Same provider/mode/account stop is visible from both workspaces and both dispatch barriers reject; other accounts and modes remain independent.
- Direct stop completes while research, candidate and QuantWorkspace mutexes are held by another thread; it bypasses the changed-source guard and Jobs queue, without resolving research.
- Stop and read request bodies cannot replace root, provider, account_id or record_domain; account identity comes from the original saved configuration.
- Absent host root returns read-only unavailable; stop/resume/journal mutation access is rejected with no files created.
- Both account GET resources require the session token. Stop/resume POSTs reject absent token, absent Origin, incorrect content type and read-only mode. The queued stop action and duplicate JSON fields are rejected.
- Resume requires the latest stop receipt and a new revision; the old account revision remains unusable, with all execution permissions false and no automatic retry/resume.
- Read/repeated receipt/replayed stop preserve bytes and mtimes. Shared resume leaves the existing workspace-local stop bytes and semantics intact.
- Trusted journal factory shares the same path across workspaces for the same account, separates mode/account, accepts no caller-selected root, creates nothing on construction/read, and exposes no raw journal HTTP write action.
- A real journal retains an original quote_connect ACTION; a peer account stop prevents a new trade_submit ACTION without changing journal bytes. Replaying the original request returns the exact old receipt without another action.
- EXTERNAL_RECORD rejects the synthetic test profile and records no claim or event.

Isolation and limits:

All databases live beneath each test's new TEMP directory. A SQLite connect guard rejects any other path. SDK import, socket connect/bind/DNS, urllib and subprocess operations are blocked and checked for zero calls. The wire/profile package declarations and all account facts are synthetic; the journal clock is explicitly replaced with the existing fixture's 2026-10-30 timestamp, not represented as current broker evidence. No listener, GUI, provider call, old DB/profile access, source execution/backtest, installation, commit or push occurred. No runner registration or backend/host source edits were made by this test subtask.

AST parsing and new-file trailing-whitespace check passed (`service-route-checks-r1.log`). Source/log/handoff hashes plus backend source hashes at handoff are in `service-route-SHA256-r1.json`; the parent owns final whole-suite and final source-identity verification.
