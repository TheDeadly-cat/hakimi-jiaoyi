# ADR 0306: Admission-budget binding in-memory delivery v1

## Status

Accepted as an isolated, host-unbound, cross-runtime delivery contract.

## Context

ADR 0305 binds correlation admission v2 to effective-budget v3 over one shared
source snapshot. Its Python document is not yet a safe browser input. A
frontend consumer must not parse arbitrary Python-shaped JSON, infer authority
from a local PASS, or receive positions, symbols, strategy identifiers, source
documents, or cluster exposure rows.

The existing static-presentation delivery contract is locked to the older
portfolio-correlation admission rail v1. Generalizing it would change an
already fingerprinted predecessor and blur consumer boundaries.

## Decision

Add a narrow in-memory delivery envelope for ADR 0305.

The Python producer:

- exact-verifies the ADR 0305 binding against all source documents and proposal
  inputs;
- requires an exact input snapshot and all eleven ADR 0305 source hashes;
- projects a presentation payload containing only status, first blocking tier,
  checks, tiers, blockers, twelve hashes, negative facts, and locked
  permissions;
- binds the payload hash into envelope provenance;
- returns a canonical UNKNOWN envelope for malformed, drifting, or
  source-unknown bindings.

The JavaScript adapter:

- verifies exact key sets and strict canonical hashes;
- verifies payload, envelope, source, check, tier, blocker, fact, permission,
  transport, consumer, provenance, and authority semantics;
- rejects correctly resealed permission or decision promotions;
- extracts only a deep-frozen payload from a known exact envelope;
- emits a frozen extraction receipt;
- treats a canonical UNKNOWN envelope as valid provenance with no payload.

## Consumer contract

The UMD/CommonJS global is
HakimiPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryV1.

The public functions are:

- verifyPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1
- verifyPortfolioCorrelationAdmissionEffectiveBudgetInMemoryDeliveryEnvelopeV1
- extractPortfolioCorrelationAdmissionEffectiveBudgetPresentationPayloadV1
- buildPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1
- verifyPortfolioCorrelationAdmissionEffectiveBudgetPayloadExtractionReceiptV1

The host script, stylesheet, slot, and payload-source provider remain null.

## Payload boundary

The payload contains:

- binding, report-universe, preregistration, matrix, complete-link audit/gate,
  strata registration/gate, admission, budget, strategy-identity, and proposal
  hashes;
- the seven ADR 0305 tiers;
- exact checks and safe blocker tokens;
- current, paper, live, render, DOM, and browser permissions fixed false.

The payload does not contain positions, proposed symbols, strategy or variant
identifiers, raw symbol lists, source documents, selection cells, or cluster
exposure rows.

## Non-goals

- No host asset registration.
- No script or stylesheet link.
- No UI mount or render call.
- No endpoint, route, network, storage, cache, database, or runtime file.
- No browser or service launch.
- No scheduler, writer, current, paper, live, or order path.
- No backtest, blind test, or profitability claim.
- No change to the natural-forward evidence chain.
- No pack-v5 compatibility promotion.
- No pointer-v2 field, hash, or publication change.

## Activation boundary

A future adapter-registration contract may pin the Python producer, JavaScript
adapter, both tests, strict-canonical dependency, and this ADR. That separate
registration still cannot mount or render a frontend consumer.
