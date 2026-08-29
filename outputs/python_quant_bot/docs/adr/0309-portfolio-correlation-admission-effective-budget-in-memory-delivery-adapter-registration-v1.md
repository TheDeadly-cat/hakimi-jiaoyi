# ADR 0309: Admission-budget in-memory delivery adapter registration v1

## Status

Accepted as an unbound, non-executing, dual-runtime adapter registration.

## Context

ADR 0308 pins the ADR 0305 source contract and all ADR 0306-0307 static
assets. Its generic registration correctly remains BLOCKED because a static
asset manifest does not itself register the Python and JavaScript delivery
adapter contracts.

The older static-presentation delivery-adapter registration is locked to the
rail-v1 schemas, files, exports, and predecessor hash. Reusing it would create
false compatibility. Modifying it would invalidate a frozen predecessor.

## Decision

Add a domain-specific, purely descriptive adapter registration.

The registration exact-verifies ADR 0308 and pins:

- ADR 0308 registration hash and asset-manifest hash;
- ADR 0308 wrapper, test, and ADR hashes;
- ADR 0306 Python producer, Python contract, JavaScript adapter, Node contract,
  strict-canonical dependency, and ADR;
- Python builder, verifier, exports, schema, payload schema, and fingerprint;
- JavaScript global, exports, schema set, fingerprint, and relative load order;
- ADR 0307 bridge schema, fingerprint, global, stage order, tier order, neutral
  labels, protected stylesheet, and raw-evidence lock;
- in-memory argument-only transport with no endpoint, route, or host slot.

The registration builder does not import JavaScript, invoke the Python
producer, build an envelope, extract a payload, or call a renderer.

## Registration state

The registration status remains BLOCKED. It proves that exact dual-runtime
adapter assets and contracts are registered, but keeps these blockers:

- app importer preregistration absent;
- HTML script preregistration absent;
- stylesheet-link preregistration absent;
- unmounted render descriptor unreviewed;
- browser visual review not performed;
- route unbound;
- mount slot unbound;
- current admission locked.

Host-plan fields remain null and all runtime authority remains false.

## Adversarial contract

The verifier rejects:

- predecessor registration-hash drift;
- direct adapter asset-hash drift;
- JavaScript relative-load-order drift;
- payload-provider promotion;
- adapter-execution authority promotion;
- extra fields;
- non-native containers and cycles;
- any direct or predecessor source-file hash mismatch.

## Non-goals

- No app importer or payload-source provider.
- No script tag or stylesheet link.
- No endpoint, route, host slot, DOM mount, or render call.
- No Python adapter invocation or JavaScript runtime load.
- No browser or service launch.
- No scheduler, writer, current, paper, live, or order path.
- No backtest, blind test, or profitability claim.
- No change to the natural-forward evidence chain.
- No pack-v5 compatibility promotion.
- No pointer-v2 field, hash, or publication change.

## Next boundary

A future application-load descriptor preregistration may consume the ADR0308
asset registration hash and this adapter-registration hash. It must still keep
all host paths null and cannot load, render, or mount the bridge without a
separate authorized review.
