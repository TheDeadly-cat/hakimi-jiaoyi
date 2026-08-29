# ADR 0441: Read-only projection application-port migration V1

- Status: Accepted
- Date: 2026-08-25
- Scope: synthetic research-only architecture and identity contract; no HTTP mount or runtime activation

## Decision

Move the byte-identical projection to `exchange_terminal.application.ports.portfolio_correlation_admission_effective_budget_readonly_projection_candidate_v1`. Preserve the ADR0318-pinned historical bytes at the legacy HTTP path, and register that legacy module name in `exchange_terminal.interfaces.http` as an alias of the canonical application-port module before ordinary submodule loading. Imports through either path therefore return the same module object, so provider binding, private verification hooks, callable globals, and mock injection cannot drift. The historical path payload is retained only to keep the sealed mount-v1 source pin truthful and is not the imported implementation.

Add a strict canonical callable identity and rebuildable adapter manifest, migrate the adapter, and re-seal ADR0436 through ADR0440. Resolver receipts, context seals, provider binding, and role-order cross-binding remain pinned. The historical mount-v1 source and test hashes remain unchanged; no downstream trusted-context or request-scope contract is reissued.

## Architecture and fingerprints

- Static graph: `CONFORMING_STATIC_GRAPH`; modules `2/95/1/33`; edges application->domain `2`, interfaces->application `23`; application->interfaces `0`; no cycles or bidirectional pairs.
- Canonical implementation `14f1e0f63668e9ddde716d4915d595182ae615be880a9b515542a58ef57ab1cc`; legacy historical payload `14f1e0f63668e9ddde716d4915d595182ae615be880a9b515542a58ef57ab1cc`; package alias registrar `cfc20c1605c2f6edd5acd8fcdc24ee0fca90df82ff7bdd1bbf536b1aeabf81c8`.
- Identity implementation `94001aa9af6cb7f8283ee3ab398b360ee76cb0fc9bf45cc4ff405a5755fba73d`; identity document `aeaa931f01a2aa1f67643ff59b5f2927a418bd6576d6586244dc46abab95781f`.
- Adapter implementation `c8210e1bdd91fb7e34f538054cb7727f3a432beae00da09cb939469e7aa56bcf`; adapter contract `c6e04132f9e773dfdf77fdbd4ef3255d102b6c0000918b6b3631f204f485215b`; prior `ff4de40e1323657a1df6213616c9fd2c92e194f7545bee54bfe4108132e1333f`; migration `acaed5cdf67fa81f49b4081fab852b34bc552c9b58834a2e07e1a188dffa4763`.

## Historical mount-v1 preservation

- `exchange_terminal/services/portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1.py`: `460cc552d650a8615191da4a40c8afac16b6c5700e552bdcdc000a9b5f2b10ae`
- `tests/test_portfolio_correlation_admission_effective_budget_readonly_http_projection_mount_preregistration_v1.py`: `ba5d0dc605f8b9003eed0e48064bfc18017cc34cfdc0833dfe9e02d4f5382241`

## Closure

- `exchange_terminal/interfaces/http/__init__.py`: `cfc20c1605c2f6edd5acd8fcdc24ee0fca90df82ff7bdd1bbf536b1aeabf81c8`
- `exchange_terminal/application/portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1.py`: `c8210e1bdd91fb7e34f538054cb7727f3a432beae00da09cb939469e7aa56bcf`
- `tests/test_portfolio_correlation_admission_effective_budget_readonly_projection_adapter_candidate_v1.py`: `a4f512b85f3108aa38fca014fc5a412a46230cced42a36e3c8f30b75bfeb281e`
- `tests/test_exchange_terminal_layer_dependency_audit_v2.py`: `1c18895e504491e33139c2be7a85be80eac1f92c18eedff2c14a71b23db0cbbc`
- `tests/test_challenge_consumption_provider_genesis_replay_reservation_application_port_migration_v1.py`: `21893372d2b85ddc84e8b9b96608eb583303d0c51efe8e7b82632b4903639742`
- `tests/test_anti_replay_registry_v2_application_port_migration_v1.py`: `6618d47eb17f06fd9be94f683220fa598d2354cd35c8efd6630c2265a4da051c`
- `tests/test_challenge_consumption_provider_application_port_migration_v1.py`: `3ccb73e9822e43d2d81cd009cd7e995f68c6a85c4a15de50148c836cab779692`
- `tests/test_replay_cursor_provider_application_port_migration_v1.py`: `37288834b46d79eb38fe4c729ea231f87784b3271e98479a1776a8ae58181acc`
- `tests/test_witness_ownership_ports_application_port_migration_v1.py`: `3f855a92aac3398591daeabb3fcd65810413e78fc39a36286ec8d3f8167e27b6`

## Safety

Static conformance grants no runtime, HTTP mount, `current`, pointer, writer, paper, live, profitability, maturity, or release authority. The candidate remains `UNREGISTERED_CANDIDATE` and synthetic; the single-look chain and pointer-v2 remain unchanged.