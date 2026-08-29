# ADR 0147: Report20 to report21 temporal-stability builder v1

## Status

Accepted as a non-persistent, non-current research builder on 2026-08-22.

## Context

Report21 is the final numbered extension in the current correlation chain. It
already had a strict consumer, protocol-v10 candidate registration, candidate
report binding, migration projection, and unmounted lockboard. It had no
production builder. Tests manually assembled 22 root fields and five fields per
identity from report20 and an unversioned external temporal binding.

Synthetic fixtures prove both required outcomes: high-sample evidence produces
report21 PASS, while low-effective-sample evidence preserves report20 BLOCK and
also produces temporal-gate BLOCK. A builder must not consume the later
protocol-v10 candidate binding or manufacture temporal PASS.

## Decision

- Add a deterministic in-memory report20-to-report21 builder.
- Require one exact versioned temporal input per report20 identity. The input
  carries the existing consumer binding fields plus a schema version.
- Independently verify report20 using the external base, report19 and report20
  hashes plus registry and stability bindings.
- Rebuild every temporal gate from the supplied uncertainty audit, correlation
  matrix and selection cells, then require its hash to equal the caller-supplied
  expected temporal gate hash.
- Preserve report20 and temporal BLOCK monotonically, retain report20 entry
  order, seal report21, and invoke the existing consumer before return.
- Raise `ValueError` for malformed, mismatched, unverifiable, or unbound inputs.

## Boundary

The protocol-v10 candidate registration and report21 candidate binding remain
downstream evidence. This builder does not create or consume them, does not
assert formal persistence or external authenticity, and does not activate the
lockboard, writer, current, pointer, paper, or live paths.

Neither the temporal input nor the downstream candidate binding carries a
declaration timestamp or external time anchor for the expected gate hash.
Equality is verified; preregistration and timing authority are not.

## Acceptance criteria

- Strict equality with the existing hand-built high-sample PASS and low-sample
  inherited/temporal BLOCK fixtures.
- Exact identity, inherited hashes, registry/stability bindings, temporal input,
  expected gate hash, and native JSON type enforcement.
- Input immutability and native false writer/current/paper/live fields.
- Zero references from existing activation entrypoints.

No backtest, market task, service, database, browser, scheduler, writer, or
trading task is part of this decision.

## Validation

- Affected report20-builder, report21-consumer, and report21-builder contracts:
  `19/19 PASS` with exact class discovery.
- In-memory compilation: `2/2 PASS`; `ResourceWarning`: `0`.
- The builder output is strictly equal to the existing hand-built high-sample
  PASS and low-effective-sample inherited/temporal BLOCK fixtures.
- Independent public-API matrix: `30` attacked candidates, `30` rejected,
  `0` accepted. It covers report20 and all inherited hash/binding boundaries,
  temporal input drift, thirteen coherently resealed root aliases, a nested
  temporal-gate reseal with synchronized expected hash, and a resealed
  BLOCK-to-PASS decision upgrade.
- Inputs were unchanged. File and socket access were denied during valid builder
  calls; external I/O attempts were `0`. Four explicit activation entrypoints
  contain zero references.
- Builder SHA-256:
  `D41D2A0D2F17F1678A5D4825FABCE53C6A47E4553C69568E5E996C7C79B1EACB`.
  Builder-test SHA-256:
  `DCA99789AC957EEA65456A616761730C94CE093AE190589A2B20CE6063FA0403`.
  Existing report21-consumer SHA-256 remains
  `CE1AD95680B36A861C62DE72A30B26D44F49BC1C7200478E953841B3D93677BA`.

Report16 evidence through report21 now has a complete in-memory builder chain.
This does not provide a report writer, delivery envelope, current activation,
formal persistence, external authenticity, profitability evidence, or trading
authority. Frozen gate `report_integration_status=NOT_IMPLEMENTED` fields remain
correct for the absent formal integration layer.
