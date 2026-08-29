# ADR 0440: Witness-ownership application ports migration V1

- Status: Accepted
- Date: 2026-08-25
- Scope: research-only architecture boundary; no runtime activation

## Context

Five application modules imported three pure witness-ownership protocols from `exchange_terminal.interfaces`: the state store, revocation-snapshot publication provider, and isolated-storage harness driver. The state-store protocol also reached the legacy anti-replay compatibility path. This left package-level reverse dependencies invisible to the earlier explicit-submodule-only migration check.

## Decision

1. Establish three versioned canonical application ports and retain all old modules as object-identity compatibility shims.
2. Bind the canonical state store directly to `exchange_terminal.application.ports.anti_replay_registry_v2`.
3. Migrate all five application consumers before retaining the shims.
4. Re-seal the complete 12-node witness-ownership provenance graph and predecessor migration contracts.
5. Extend the migration contract to count both package-level and explicit-submodule interface imports.
6. Keep the HTTP projection candidate deferred to its independent resolver, context-seal, cross-binding, candidate, and adapter design.

## Architecture result contract

- Application modules: `93`.
- Interfaces modules: `33`.
- Application to interfaces edges: `1`.
- Interfaces to application edges: `22`.
- The only remaining application-to-interfaces edge is the deferred HTTP projection candidate.
- Module cycles: none.
- Architecture status: `BLOCKED_PARTIAL_LAYERING`.

## Canonical fingerprints

- State store: `36a43ef91efcc472664c5b4bdc8519046532eb5a2d7c36fe398e9ac6262f72e8`.
- Publication provider: `433404433d04a7c5733084a253eaf1394433618e13eaf51fff2914c86e9617dd`.
- Storage-harness driver: `d4500c42991d7f5a6529782a7d234cb12012c2995215df772383005f873f7e69`.
- State-store shim: `3fbdd877dc7f41786e9b1c4539803b2cd39ea7db4f1732b180b2aaa6a5664029`.
- Publication-provider shim: `03e50abcc00dd899845f28210da7bcc1b29d02ac2898ddc765379fe52c6e2f0d`.
- Storage-harness shim: `7e77abedfa9380e6fc3360ed0374b2200e544d95305c25f4effdf37bcff43b9e`.
- Migration contract: `4419bf991fa27824816e04849602fc9c53311dab43c7c72a08601a5c096bc555`.

## Re-sealed closure

- `exchange_terminal/application/witness_ownership_state_service.py`: `4b3c711e614416ce78bb62bd9cc28dce077f3b6e99fb20891be295557d40178c`
- `exchange_terminal/application/witness_ownership_state_provider_preregistration_v1.py`: `081cf9dfae66918f6e5e1cf4fd8f9d7e7c438aff01e1b465726a86d8aee47b2d`
- `exchange_terminal/application/witness_ownership_state_signed_receipt_v1.py`: `d0236dafac1f5c81170e97b1e58b4459c0b673814205242deb9adeada12d072d`
- `exchange_terminal/application/witness_ownership_key_revocation_snapshot_publication_consumer_v1.py`: `b94371a927983588aecd678ba40ee5ca4c2d5e9678ea8f5f6c4420808dd77d13`
- `exchange_terminal/application/witness_ownership_state_provider_identity_source_adapter_preregistration_v1.py`: `d087684a6a7e64bd2acf6e213144083ad30e5b88bf091f9f56edb942465f4374`
- `exchange_terminal/application/witness_ownership_key_revocation_snapshot_storage_adapter_preregistration_v1.py`: `04afd17f55c4a287852f727aadf771772d6770e0f1f9db8ebd98040bb95bb52f`
- `exchange_terminal/application/witness_ownership_key_revocation_snapshot_storage_evidence_quorum_v1.py`: `7111362ca0c1fa914bf6ea65a358347e6889e2f63184a520f5cdf0cdc37665a3`
- `exchange_terminal/application/witness_ownership_snapshot_storage_observer_identity_admission_v1.py`: `a285225bc97cc61a5405d7472e0439295b04ca1442e0a9bcf8039a3e0c648578`
- `exchange_terminal/application/witness_ownership_key_revocation_snapshot_isolated_storage_harness_v1.py`: `a0212ece7ffe67b9f2dc5515e3effbbdebc8e5512dd1e9b32eadaae41ef80811`
- `exchange_terminal/application/witness_ownership_snapshot_storage_harness_evidence_lineage_binding_v1.py`: `4c47934b9945626b1665c6e61f873123a45ddc935064e2084897ece7eb48d639`
- `exchange_terminal/application/witness_ownership_snapshot_storage_persistence_admission_decision_v1.py`: `eb366b03855fc37b11fa77615aee90c4ef3a1e1ec38357f2bf152ba4409f2467`
- `exchange_terminal/application/witness_ownership_state_provider_conformance_plan_v1.py`: `410a2d54f0677bf1e382341afbeac95ecb980fcd3370bc7344d7d923aaa05f0e`
- `tests/test_exchange_terminal_layer_dependency_audit_v2.py`: `054c9acc0fff60ba5ce44790eee387daa3fd8d1cc6186141194bbdd77139849a`
- `tests/test_challenge_consumption_provider_genesis_replay_reservation_application_port_migration_v1.py`: `8538a5c7a4bae82a43b10b16dbef237de64b23686bdeb140bb3cd81cde902cbe`
- `tests/test_anti_replay_registry_v2_application_port_migration_v1.py`: `47c845945c468ee4954afdafba1cec91fb0e5afca3260731740f24a8f45a7471`
- `tests/test_challenge_consumption_provider_application_port_migration_v1.py`: `84272c4b2c43c3a971e6c57515098bf9971362c85a7d7f6e9250d2d758f807c3`
- `tests/test_replay_cursor_provider_application_port_migration_v1.py`: `5002059dc35694a92ec2bed3cbf332e091caae4e2d381b48ddcca4b9b290681f`

## Consumer-first activation order

1. Create canonical ports without mounting providers or storage.
2. Bind state-store composition to canonical anti-replay V2.
3. Switch all five application consumers.
4. Retain legacy imports only as identity shims.
5. Validate behavior, identity, full provenance, architecture counts, and the sole deferred HTTP edge.
6. Do not switch `current`, issue a pointer, or activate paper/live authority.

## Safety and non-authority

This migration performs no storage I/O, provider invocation, registry mutation, service startup, scheduler action, backtest, paper order, or live order. Synthetic contract success does not prove external identity, durability, linearizability, market validity, profitability, or trading authorization. The natural-forward single-look chain and pointer-v2 contract remain unchanged.

## Acceptance matrix

Acceptance requires targeted `py_compile`, witness-ownership state-store/publication/storage lineage contracts, ADR0436 through ADR0440 migration contracts, the layer dependency audit, and protected frontend/canonical fingerprint checks.
