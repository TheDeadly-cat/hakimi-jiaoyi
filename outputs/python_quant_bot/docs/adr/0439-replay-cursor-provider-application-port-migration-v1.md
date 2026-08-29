# ADR 0439: Replay-cursor provider application-port migration V1

- Status: Accepted
- Date: 2026-08-24
- Scope: research-only architecture boundary; no runtime activation

## Context

The replay-cursor preregistration application module imported its provider contract from `exchange_terminal.interfaces`. The provider module is a pure immutable command/result/protocol boundary, but its location left one avoidable application-to-interfaces submodule edge and made the delivery layer appear authoritative over an application port.

## Decision

1. Preserve the exact provider bytes as `exchange_terminal.application.ports.strategy_correlation_incumbent_snapshot_replay_cursor_provider_v1`.
2. Replace `exchange_terminal.interfaces.strategy_correlation_incumbent_snapshot_replay_cursor_provider` with an explicit object-identity compatibility shim.
3. Migrate the sole application consumer, replay-cursor provider preregistration, to the canonical port before retaining the shim for legacy readers.
4. Re-seal the full static provenance closure instead of accepting stale nested implementation hashes.
5. Keep the HTTP projection candidate and package-level witness-ownership imports outside this ADR because they require separate versioned contracts and consumer migrations.

## Architecture result contract

- Application modules: `90`.
- Interfaces modules: `33`.
- Application to interfaces edges: `6`.
- Interfaces to application edges: `19`.
- Explicit application-to-interfaces submodule imports: exactly `1`, the deferred HTTP projection candidate.
- Module cycles: none.
- Architecture status: `BLOCKED_PARTIAL_LAYERING`.

## Canonical and compatibility fingerprints

- Canonical provider: `210f897078503e2a0e7a95d1f3c3a531d8331fe59b82684fb6f2fc14f01c09c5`.
- Legacy identity shim: `a855a29f27fa4c163037726575c55302b59398d63a5c41970bc99e322da25721`.
- Migration contract: `6c19b04d17eda4c4bb2185eed3bc5b92ebc0f43486c166d6c94f7b0c20872139`.

## Re-sealed closure

- `exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1.py`: `42e1e2a88839b616ac2ebc9f7851ae8266172ade6b1a5a26320635ec90111212`
- `exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_signed_registration_v1.py`: `c83f9f06cdd60ff28021664699d486e86fc5e4881b45d8899375a7a76c4d4950`
- `exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_signed_source_v1.py`: `154152491e419f4f41d273b83b44be6d51994c58bdfe2c7d4727b48d4c521d94`
- `exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_clock_attestation_binding_v1.py`: `620ed3ec9805cf3c73f87bbc9da5b672cb4ceff65e7e9b0ed8ae7f43be7e0f05`
- `exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_command_binding_v1.py`: `b2cefebf21b415beef5a67127f25efbcfc22d941fa92df4ee9928376c566f513`
- `exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_preregistration_v1.py`: `867dd73a4cbb8219654265f21f3fff70d3031f18f23057fb3b69ebd6afc71bbb`
- `exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_signed_registration_v1.py`: `64cdf02d9249088dd917ae935b3ef17c4c84d412bef1d1dafced58d8601bb73b`
- `exchange_terminal/application/strategy_correlation_incumbent_snapshot_replay_cursor_provider_registration_challenge_consumption_provider_registration_challenge_signed_source_v1.py`: `3eb90909dffe275053048743f7ad5e9567df7fc590b5040d0ebb214fbc16e1ca`
- `exchange_terminal/application/challenge_consumption_provider_registration_handoff_v1.py`: `593eb672b93823f1b6d859577758b6040656b65e000b3736fea33297a0a73ab1`
- `exchange_terminal/application/challenge_consumption_provider_registration_clock_binding_v1.py`: `f57ee0863658e80a751d29884c77672441d82149109e488975e756314b3361b9`
- `exchange_terminal/application/challenge_consumption_provider_bootstrap_topology_v1.py`: `ac39291a0f0e62bb47b42163cbf78ddd712f290ca1061b6ef9784700eb0c7e1d`
- `exchange_terminal/application/challenge_consumption_provider_threshold_genesis_admission_v1.py`: `9dba83afda64034335a37e704d000fb1d083c6f617f6bea4211222e45afc553d`
- `exchange_terminal/application/challenge_consumption_provider_genesis_replay_reservation_preregistration_v1.py`: `dfdedb55e1e0d89e25436d64a9597fbf09c359db63101efe457425698075d15e`
- `exchange_terminal/application/challenge_consumption_provider_genesis_replay_reservation_signed_registration_v1.py`: `d60e69e27cd0c746f82e368420c617e2683cb31fd4a36a701ef366705563471c`
- `exchange_terminal/application/genesis_replay_reservation_provider_registration_challenge_signed_source_v1.py`: `d01e45afd996d4c32e0f4267d649378dfba310902c39f5f0bf67092ee773b8b4`
- `exchange_terminal/application/genesis_replay_reservation_provider_registration_handoff_v1.py`: `e64301444c6e6dede1d6948a5aeaac1326a5c97749d6f8ebe744e4c7f8a3a1c6`
- `exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_binding_v1.py`: `60f01be568b0ef978819c75dbb39146c5b0b06cd2e351f2de2fac9ab3c54b94b`
- `exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_trust_bootstrap_topology_v1.py`: `948ddd4c9889376fd7262cc51fb952aa9230944f51959ede081f10d7426f1bde`
- `exchange_terminal/application/genesis_replay_reservation_provider_registration_clock_trust_threshold_genesis_admission_v1.py`: `693966381aec8b79d03ee13a9f0e6070dbf7657802e93b650cae61eabf2a098f`
- `exchange_terminal/application/genesis_replay_reservation_commitment_semantic_profile_quarantine_v1.py`: `8585f343c43586faf6dd26eabd1a1f8925e2506579ca640f1164c5881a13a1cd`
- `tests/test_exchange_terminal_layer_dependency_audit_v2.py`: `29cea4ba3748ee9c197088b25d0413ffa51afabc589859735a0732590d8a4699`
- `tests/test_strategy_correlation_incumbent_snapshot_replay_cursor_provider_preregistration_v1.py`: `2e23aa9360bbdc00a519254a6a82b08a441eb8cd10a2211f20f78ccd473c9949`
- `tests/test_challenge_consumption_provider_genesis_replay_reservation_application_port_migration_v1.py`: `ccdc63c4606ba777c7686552e602a9270106cddca18b3bb5b6cc2ec36ceab83a`
- `tests/test_anti_replay_registry_v2_application_port_migration_v1.py`: `4d057ab4a4cbcac4d014aa6525d4ac0c226244c825ab04946d27da7ec904adad`
- `tests/test_challenge_consumption_provider_application_port_migration_v1.py`: `4169d683fe1dce0ac258e367f531f4bf2b8e42316963c79c157677fea1b8446f`

## Consumer-first activation order

1. Establish the byte-identical versioned application port without switching runtime authority.
2. Switch preregistration to the canonical port.
3. Retain the old module only as an identity shim.
4. Validate canonical behavior, legacy identity, sealed descendants, architecture counts, and the single deferred explicit submodule edge.
5. Do not switch `current`, issue a pointer, or activate a provider.

## Safety and non-authority

This migration performs no provider registration, registry mutation, cursor advance, runtime mount, storage I/O, service startup, scheduler action, backtest, paper order, or live order. Synthetic contract success does not prove external provider identity, key control, durability, linearizability, profitability, paper authorization, or live authorization. The natural-forward single-look chain and pointer-v2 contract remain unchanged.

## Acceptance matrix

Acceptance requires targeted `py_compile`, the provider/preregistration/registration/challenge/clock/consumption/genesis/quarantine contract chain, ADR0436 through ADR0439 migration contracts, and the layer dependency audit. Protected frontend and strict canonical fingerprints must remain unchanged.
