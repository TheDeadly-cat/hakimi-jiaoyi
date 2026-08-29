# ADR 0435: Anti-replay registry application port migration v1

- Status: accepted research-only architecture and provenance migration; activation remains forbidden
- Date: 2026-08-24
- Predecessors: ADR 0432, ADR 0433, and ADR 0434

## Context

`anti_replay_registry_identity_preregistration_v1` was the smallest remaining one-consumer application dependency on the mixed interfaces package. Its implementation hash is also a provenance root for organization intake, signer source-trust, verification envelope, and source-baseline provider-conformance artifacts.

Migrating only the import would reduce one dependency edge while leaving several implementation pins stale. This ADR therefore treats the change as one topology-ordered provenance closure.

## Decision

1. Preserve the exact anti-replay V1 contract bytes as `exchange_terminal.application.ports.anti_replay_registry_v1`.
2. Replace the legacy interfaces module with an object-identity shim pinned to the canonical hash.
3. Migrate the sole application consumer to the canonical port.
4. Recompute implementation pins in dependency order H1 identity -> H2 intake -> H3 signer, then update verification and source-baseline plan closures.
5. Keep anti-replay V2 and all legacy tests on the shim until separately migrated; their imported V1 objects must remain identical to canonical objects.
6. Preserve schemas, namespace, strict consumption-key binding, and all execution locks.

## Fingerprints

- Canonical anti-replay V1 SHA256: `5eed523c3665e687c6d2f202afcea5cc93bcdee3ef4ee942a7d4f76364f380a0`.
- Legacy compatibility shim SHA256: `6c0f019a6ecbb44d902c30a94417ba1c050d24a2b043cb554df96155dfc8250f`.
- H1 identity preregistration SHA256: `d21e6864245ccb054329160ca49b2c5b725d6b86c262f0f0728c018b8c5d035f`.
- H2 organization identity intake SHA256: `3d9ce854b1e3f9bc29ce654d189be3c975796d9a4f5a7c7e72ade715f816ef56`.
- H3 signer source-trust preregistration SHA256: `12565b61f7984e87821f5abb86edd005436b5214f527549a93c011cb158cd51c`.
- Verification envelope SHA256: `c51984b8e15d7847a46d9d452ab099ca954bd11cadccad1d510fdc2539f9c05d`.
- Source-baseline provider-conformance plan SHA256: `57a4ca1e3c4b7bd9145dd1e86820671f85f99f1548097e1522827b46a1ea1c31`.
- Updated verification contract SHA256: `f586a20c17f076f4612bc5974733937703d6b0c5213932eda609757b78c76a70`.
- Updated ADR0434 monotonic migration contract SHA256: `878ad63c76b8452e03f8033a340c6678ae43b1f967cc0bad3ac295bb73bf29c0`.
- Updated audit-v2 current-tree contract SHA256: `b4e582008e34bccb64fd4cd9e66e56ace50536ed563d8a0bbe189b5a822b2d64`.
- ADR0435 migration/provenance contract SHA256: `c1d2388f400409711bec81aa67f3788a844e73df4a1c3ee6422a092c16c357c1`.

## Cross-runtime provenance closure

The Python H1-H6 change reaches an 18-node explicit source closure across the signed-artifact aggregator, key-possession and gap projections, source-baseline cards/adapters/registrations, and strategy presentation consumer registrations. The initial implementation-hash closure converged after 12 propagation rounds. A second topology-ordered pass closes document seals that embed those implementation hashes. Protected host assets remain excluded.

- Signed-artifact aggregation candidate SHA256: `5a1df11be56fcb641d1d04dc0397a94bd22a8c08ea632cd0cf4eb5d9c9754a0f`.
- Key-possession candidate SHA256: `aab58710d8cc2bf81f66e2daf8f562e1310ab591542a328b00c23ebdc102bdaf`.
- Gap projection v1/v2 SHA256: `021a4618caf5968057b13dd744918bf059d2a756eb47fe4cc1a55b538de1ca7d` / `ab755cd4579dc5bc7855c54f4625862e9ff3203179303057a23d80f613ab2677`.
- The migration contract pins every final node hash and forbids every superseded root and intermediate hash within the closure.

## Document-seal closure

The ADR0281 preregistration seal changed when its pinned registration-v9 implementation changed. Its current consumers form an acyclic seal chain, so each document and the implementation that embeds it must be advanced in producer-first order.

- ADR0281 consumer preregistration hash: `42b4c9830844c455b05c4952a7010655534048f73cf78f9f7ab574bebbddca5d`.
- Registration-v1 consumer registration hash: `217e4b759b993f3f513b989b79c380f7e192c799872e3f6959116171cc83d036`.
- Style preregistration hash: `c8a882d9960d3c37f86d398304f827cf92bb741a229f33eed6abb96f4b8dccb5`.
- Registration-v2 consumer registration hash: `ab663f22c980f850b8440b8844909930d7a1a72f27245b26826c45c2000e7c64`.
- Application load-descriptor hash: `a842fe43de8b8c2b7bdd2c2978dfb4d09f03ca49aa8555d2ab3edcbe7cdbd7b2`.
- In-memory delivery-adapter registration hash: `db9981006de952321e72973fe2c7e981e5d3b23450e2b2437613c5d2573e6e3f`.
- Neutral card and style implementation SHA256: `88a1ac27eaefd554e82129a5b2883d14af365965559d1d0e84db8dc32b1d9a5a` / `ff06b47a7832a46a7092f5dba4b64401e56b0e6f7562420d2a505bf79bda6ff0`.
- Registration-v1/v2 implementation SHA256: `948aaa77ea86658732226d2ed4d4c585a625ba409b946ef1f79fac58f0a883fe` / `160e680e2ad94e281ee4bbe5c22e610c24837c6ec382b93a40408eb15d2d772a`.
- Load descriptor and Python/JavaScript delivery adapter SHA256: `9bcd1f37f8c0ef85ddcfffed65dd1104b7317567e69972ad1469cf55886e7ae5` / `b6251351e821a455fa781c55d12a41db2ce03e576cbfca6dc78c4a4b767a0ee7` / `46679b99d3c9c93529d6917960d4dbebc6caffe4b9053826f061cdd7877ab8ed`.
- Delivery-adapter registration SHA256: `64013da2f26d49ec1f0ee17b8abee5b061e0f9007c448bc02e0fa18766be46e8`.

The migration contract now rebuilds the Python document producers in memory, pins the JavaScript style producer under its existing Node contract, and rejects all superseded file and document hashes inside the 18-node closure. These seals establish exact synthetic contract continuity only. They do not establish market validity, profitability, publication permission, paper authority, or live trading authority.
## Current dependency result

- Direct application-to-interfaces imports reduce from 7 to 6.
- Recursive inventory becomes domain=2, application=86, infrastructure=1, interfaces=33.
- Audit-v2 cross-layer edges become application->domain=2, application->interfaces=12, interfaces->application=17.
- Module cycles remain absent.
- Architecture remains `BLOCKED_PARTIAL_LAYERING / LAYER_ROLE_SEPARATION_REQUIRED`.

ADR0434 preserves its historical exact-seven snapshot. Its current contract now enforces a non-regression ceiling of at most seven, while ADR0435 pins the exact current count at six. ADR0435 also adds a direct file-hash provenance closure test so future migrations cannot satisfy constants while pointing tests at compatibility shims.

## Safety and evidence boundary

This migration performs no registry call, compare-and-consume action, network access, runtime mutation, service startup, market-data access, backtest, scheduler action, paper order, live order, or publication. The canonical port remains a type and validation contract only.

The natural-forward evidence chain, legacy pack-v5 public reads, and pointer-v2 remain unchanged. Static architecture and synthetic contracts are not strategy performance, profitability, release permission, paper authority, or live trading authority.