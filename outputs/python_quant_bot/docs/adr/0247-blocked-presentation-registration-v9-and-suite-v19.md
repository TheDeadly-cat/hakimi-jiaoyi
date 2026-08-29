# ADR 0247: Blocked presentation registration v9 and suite v19

## Status

Accepted as a blocked static registration successor and source-level UI suite.

## Context

ADR0246 adds a versioned presentation-v2 successor without modifying the v1
assets frozen by registration-v8. The six v2 decision, production, and
verification assets are not yet bound into the single Python presentation
registration chain.

Trusting only a registration-v8 document hash would skip its deep predecessor
inputs. Registration-v9 must execute the public v8 verifier with the exact v7
chain and v8 manifest before accepting the v2 asset manifest.

## Decision

Add registration-v9 as the exact successor of registration-v8. It requires:

1. one exact registration-v8 document;
2. the complete v7 predecessor inputs required to replay v8;
3. the exact frozen seven-asset v8 manifest;
4. the exact six-asset presentation-v2 manifest;
5. exact v2 SOURCE to GAP to MATURITY to PERMISSION order;
6. the two observed-local versus six unverified identity-ledger split;
7. reuse of the frozen v1 stylesheet;
8. fixture-v2 status UNMOUNTED;
9. all route, mount, browser, current, runtime, writer, paper, and live
   authority remaining false.

The v2 manifest contains projection-v2, card-v2, fixture-v2, Node tests, Python
cross-runtime tests, and ADR0246. Registration-v9 records source hashes only and
does not execute the assets.

Add suite-v19 to statically verify:

- v2 identifiers remain absent from app.js and index.html;
- stage order, ledger wording, and permissions remain neutral;
- fixture-v2 remains unmounted and reuses the v1 stylesheet;
- the frozen v1 and shared stylesheet hashes remain unchanged;
- no READY or profitability wording is introduced.

## Adversarial matrix

- exact v8 replay and six exact v2 pins build one blocked v9 document;
- CLEAR, TAIL_BLOCK, and EXACT_UNKNOWN remain distinct and blocked;
- missing, extra, or substituted v2 pins fail closed;
- v8 predecessor substitution fails closed;
- resealed v9 authority promotion fails exact reconstruction;
- public verifier PASS means exact reconstruction of a blocked, unmounted
  registration only;
- suite-v19 cannot establish browser rendering, route binding, or mount status.

## Consumer-first order

1. exact blocked registration-v8;
2. exact ADR0246 presentation-v2 assets;
3. blocked registration-v9 and suite-v19;
4. independently governed signer-role and external-source evidence;
5. per-schema payload semantic validators;
6. process-authenticated cross-runtime receipt;
7. organization-identity decision contract;
8. explicit browser visual review;
9. separate route, mount, current, and activation decision.

## Consequences

- The project retains one versioned Python presentation registration chain.
- Existing registration-v8, suite-v18, v1/v2 assets, styles.css, app, index,
  current, pointer-v2, and natural-forward artifacts remain unchanged.
- Static suite PASS is source evidence, not browser visual evidence.
- No credential, endpoint, runtime asset, database, cache, log, service,
  browser, scheduler, market task, backtest, blind test, paper order, or live
  order is used.
- Registration-v9 is not source legitimacy, signer identity, organization
  identity, adapter conformance, profitability, current, runtime, route, mount,
  writer, paper, or live authority.
