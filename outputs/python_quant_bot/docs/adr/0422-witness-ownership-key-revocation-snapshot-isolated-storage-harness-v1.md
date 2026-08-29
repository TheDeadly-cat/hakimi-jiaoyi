# ADR0422: Witness Snapshot Isolated Storage Harness v1

## Status

Accepted as an unmounted, research-only harness contract on 2026-08-24.

## Context

ADR0420 preregisters fourteen storage evidence requirements.  ADR0421 defines
signed 2-of-3 observer coverage for those requirements.  Neither defines how a
future adapter test runner receives scenarios or emits transcript/artifact
hashes without touching project runtime state.

The only harness-like source name found in the repository is backtest-specific.
It is not imported or reused because this boundary must not run historical
market data or inherit backtest semantics.

## Decision

Add a driver Protocol and consumer-first isolated harness with these rules:

1. A canonical plan maps all fourteen ADR0420 requirements in fixed order.
2. Thirteen requirements are driver-executable.  The independent observer
   requirement is observer-handoff-only and cannot produce a driver command.
3. The plan and every command bind the ADR0420 registration, driver identity and
   implementation hash, hashed isolated domain, scenario preregistration, run
   nonce, adapter implementation, and backend kind.
4. The driver is called at most once for each scenario.  There is no retry,
   reissue, rebase, scheduler, or background execution.
5. Driver exceptions, malformed results, and non-PASS outcomes stop execution.
6. Result builders reject claims of mutation outside the isolated domain,
   paper/live operations, or automatic retry/reissue.
7. Transcript and observed-artifact hashes must be unique across scenarios.
8. A complete driver bundle produces only an observer-handoff descriptor.  It
   does not produce or sign ADR0421 observer evidence.
9. The harness accepts no path, connection string, bucket, table, credential,
   key, or secret.
10. Driver execution, isolated-domain confinement, external persistence,
    observer identity, publication authority, paper/live authority, and
    current-chain activation remain unverified or false.

## Adversarial matrix

Pure in-memory fake-driver tests cover deterministic plans, 14-to-13-plus-1
scenario partitioning, observer-only command rejection, exact plan verification,
single calls, handoff construction, permanent locks, stop-on-BLOCK,
stop-on-exception, malformed results, transcript/artifact replay, unsafe mutation
claims, wrong plan hashes, exact bundle verification, authority tampering, run
nonce separation, duplicate semantic hashes, and runtime-locator exclusion.

## Consumer-first activation order

1. Keep the Protocol and harness unmounted with synthetic drivers only.
2. Define a real observer identity admission contract and bind it to ADR0421.
3. Select a backend and isolated test domain only after explicit authorization.
4. Implement one adapter driver and run crash/restart/concurrency scenarios only
   in that isolated domain.
5. Convert independently observed transcript/artifact hashes into ADR0421 signed
   reports.
6. Make a separate persistence admission decision; never activate current by
   implication.

## Consequences

ADR0422 closes the test-harness shape and no-retry orchestration gap.  It proves
no real storage, isolation, durability, atomicity, restart consistency,
profitability, or trading authority.

The natural-forward evidence chain remains unchanged:

`audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`

Legacy pack-v5 public reads remain UNKNOWN/null.  pointer-v2 is unchanged and
is not automatically reissued.
