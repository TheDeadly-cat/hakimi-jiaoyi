# ADR 0146: Report19 to report20 cluster-stability builder v1

## Status

Accepted as a non-persistent, non-current research builder on 2026-08-22.

## Context

Report20 already had a strict consumer, protocol, formal-persistence candidate,
and aggregate public projection. It had no production builder. Tests manually
assembled the report20 document after constructing an external stability
binding containing an uncertainty audit, matrix, selection cells, and expected
gate hash.

The existing binding shape was exact but unversioned. A source-chain probe also
showed why the builder must not manufacture PASS: current report17-to-report19
synthetic evidence verifies as a valid cluster-stability BLOCK, while the
independent high-sample fixture produces PASS and the low-effective-sample
fixture produces BLOCK.

## Decision

- Add a deterministic in-memory report19-to-report20 builder.
- Require one exact versioned stability input per report19 identity. The input
  carries the existing consumer binding fields plus a schema version.
- Verify report19 using the external base hash and registry bindings.
- Rebuild every stability gate from the supplied uncertainty audit, correlation
  matrix and selection cells, then require its hash to equal the caller-supplied
  expected gate hash.
- Preserve report19 BLOCK and stability BLOCK monotonically, retain report19
  entry order, seal report20, and invoke the existing consumer before return.
- Raise `ValueError` for malformed, mismatched, unverifiable, or unbound inputs.

## Boundary

This builder does not use the later formal-persistence registry candidate and
does not create uncertainty evidence, expected hashes, external authenticity,
or a PASS result. It adds no writer, persistence, route, UI mount, scheduler,
pointer mutation, paper authority, or live authority.

The expected gate hash proves equality and substitution resistance only. This
contract contains no declaration timestamp, evidence cutoff binding, external
anchor, or immutable receipt, so preregistration and timing authority are not
proven.

## Acceptance criteria

- Strict equality with the existing hand-built PASS and low-sample BLOCK
  fixtures.
- Valid BLOCK from the actual ADR0143-to-ADR0145 synthetic source chain.
- Exact identity, report19 hash, registry binding, stability input, expected gate
  hash, and native JSON type enforcement.
- Input immutability and native false writer/current/paper/live fields.
- Zero references from existing activation entrypoints.

No backtest, market task, service, database, browser, scheduler, writer, or
trading task is part of this decision.

## Validation

- Affected report19-builder, report20-consumer, and report20-builder contracts:
  `18/18 PASS` with exact class discovery.
- In-memory compilation: `2/2 PASS`; `ResourceWarning`: `0`.
- The builder output is strictly equal to the existing hand-built high-sample
  PASS and low-effective-sample BLOCK fixtures.
- The actual ADR0143-to-ADR0145 synthetic chain remains a valid report20 BLOCK;
  no PASS was manufactured to close the chain.
- Independent public-API matrix: `26` attacked candidates, `26` rejected,
  `0` accepted. It covers report19/hash/registry/input drift, twelve coherently
  resealed root aliases, a nested gate reseal with synchronized expected hash,
  and a resealed BLOCK-to-PASS decision upgrade.
- Inputs were unchanged. File and socket access were denied during valid builder
  calls; external I/O attempts were `0`. Four explicit activation entrypoints
  contain zero references.
- Builder SHA-256:
  `D8CFAE2B09285EADD1EBBF216AEC4CC511B9A962DC12B16C2A4E09BCD76558C9`.
  Builder-test SHA-256:
  `EA468CBDB99906E38F2961A2B565F4D562716804F1500A9A60E24CCE3EAC160F`.
  Existing report20-consumer SHA-256 remains
  `1BB2382A941CD8521AB24A62C44A77B5BFD2746A73BFBE134A6BD26BABD91F09`.

The frozen gate field `report_integration_status=NOT_IMPLEMENTED` remains
correct for formal writer/delivery integration. This builder is synthetic
contract functionality only, not external stability evidence or authority.
