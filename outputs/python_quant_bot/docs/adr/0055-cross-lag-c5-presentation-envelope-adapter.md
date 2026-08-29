# ADR 0055: Cross-lag C5 presentation-envelope application adapter

- Status: Accepted and implemented as a pure in-memory C5 adapter; HTTP and mount not authorized
- Date: 2026-08-21
- Scope: Pure in-memory application orchestration only
- Authority: None

## Context

C3 builds and exactly verifies the aggregate
`strategy-correlation-cross-lag-public-summary-v1` document. C4 now provides a
strict-canonical, detached, unmounted consumer for
`strategy-correlation-cross-lag-presentation-envelope-v1`, but no Python
producer exists for that envelope.

The missing boundary is not an HTTP route. It is a pure application-layer
adapter that invokes the official C3 builder and verifier, then translates the
verified result into the exact three-field C4 envelope. Adding this orchestration
inside `services` would duplicate the C3 evidence boundary. Adding it inside
`interfaces` would prematurely create a transport contract. C5 therefore belongs
in `exchange_terminal/application` alongside other pure build/verify envelopes.

## Decision

C5 is implemented in one module:

`exchange_terminal/application/strategy_correlation_cross_lag_presentation_envelope.py`

It exposes exactly two public functions:

- `build_strategy_correlation_cross_lag_presentation_envelope`;
- `verify_strategy_correlation_cross_lag_presentation_envelope`.

The application module imports the C3 builder and verifier from
`exchange_terminal.services.strategy_correlation_cross_lag_public_projection`
and strict comparison primitives from
`exchange_terminal.services.strict_canonical_json_hash`. No service module may
import this application adapter.

C5 performs no domain calculation and creates no new research state. It only
orchestrates an already versioned producer and consumer.

## Versioned constants

Envelope schema:
`strategy-correlation-cross-lag-presentation-envelope-v1`

Adapter static fingerprint:
`20260821-cross-lag-c5-presentation-envelope-adapter-1`

Consumed C3 schema:
`strategy-correlation-cross-lag-public-summary-v1`

Consumed C3 verification schema:
`strategy-correlation-cross-lag-public-summary-v1-verification-v1`

Consumed C3 static fingerprint:
`20260821-cross-lag-public-summary-1`

The adapter fingerprint is a module constant and test fingerprint only. It is
not inserted into the C4 envelope because C4 v1 accepts exactly three fields.

## Exact public signatures

The builder mirrors every C3 public-summary input explicitly. It must not expose
`**kwargs`, positional context bags, mutable defaults, callback hooks, or generic
service handles.

```python
def build_strategy_correlation_cross_lag_presentation_envelope(
    binding_assessment: Any,
    *,
    protocol_registration: Any,
    preregistration_adapter_binding: Any,
    evaluation: Any,
    consumer_receipt: Any,
    strata_protocol_registration: Any,
    registry_assignment_adapter: Any,
    direction_contract: Any,
    source_preregistration: Any,
    strata_registration: Any,
    registry_asset: Any,
    registry_binding_assessment: Any,
    dimension_id: Any,
    selection_cutoff_date: Any,
    first_observation_timestamp: Any,
    aligned_observations: Any,
    expected_binding_assessment_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_preregistration_adapter_binding_hash: Any,
    expected_evaluation_hash: Any,
    expected_consumer_receipt_hash: Any,
    expected_strata_protocol_registration_hash: Any,
    expected_registry_assignment_adapter_hash: Any,
    expected_direction_contract_hash: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
    expected_stratum_assignment_hash: Any,
) -> dict[str, Any] | None:
    ...
```

The verifier accepts the candidate envelope plus the same explicit context:

```python
def verify_strategy_correlation_cross_lag_presentation_envelope(
    document: Any,
    binding_assessment: Any,
    *,
    protocol_registration: Any,
    preregistration_adapter_binding: Any,
    evaluation: Any,
    consumer_receipt: Any,
    strata_protocol_registration: Any,
    registry_assignment_adapter: Any,
    direction_contract: Any,
    source_preregistration: Any,
    strata_registration: Any,
    registry_asset: Any,
    registry_binding_assessment: Any,
    dimension_id: Any,
    selection_cutoff_date: Any,
    first_observation_timestamp: Any,
    aligned_observations: Any,
    expected_binding_assessment_hash: Any,
    expected_protocol_registration_hash: Any,
    expected_preregistration_adapter_binding_hash: Any,
    expected_evaluation_hash: Any,
    expected_consumer_receipt_hash: Any,
    expected_strata_protocol_registration_hash: Any,
    expected_registry_assignment_adapter_hash: Any,
    expected_direction_contract_hash: Any,
    expected_registry_asset_hash: Any,
    expected_classification_source_hash: Any,
    expected_stratum_assignment_hash: Any,
) -> bool:
    ...
```

The explicit signature is intentionally verbose. It prevents new C3 inputs from
silently bypassing C5 review.

## Build sequence

The builder performs this exact sequence:

1. Call `build_strategy_correlation_cross_lag_public_summary` with the complete
   supplied context.
2. Require the result to be a native mapping with the exact C3 schema,
   verification schema, and static fingerprint.
3. Call `verify_strategy_correlation_cross_lag_public_summary` on that exact
   result with the same complete context.
4. Require the verifier result to be native `True`; `1`, a truthy object, or a
   string is not accepted.
5. Require `public_summary_hash` to be a strict SHA-256 string.
6. Deep-copy the verified summary into a new plain dictionary and construct the
   exact C4 envelope.
7. Return no aliases to mutable caller-owned mappings or lists.

The exact envelope is:

```json
{
  "schema_version": "strategy-correlation-cross-lag-presentation-envelope-v1",
  "summary": {},
  "verification": {
    "schema_version": "strategy-correlation-cross-lag-public-summary-v1-verification-v1",
    "valid": true,
    "supplied_public_summary_hash": "<C3 public_summary_hash>",
    "rebuilt_public_summary_hash": "<C3 public_summary_hash>"
  }
}
```

The envelope has no adapter status, URL, path, timestamp, current marker,
callback, writer, endpoint, route, permission, recommendation, or trading field.

## Four-state preservation

C5 does not collapse C3 public states:

| C3 result | C5 result |
| --- | --- |
| Exact fixed `NOT_SUPPLIED` summary | Valid envelope containing `NOT_SUPPLIED` |
| Exact fixed `UNKNOWN` summary | Valid envelope containing `UNKNOWN` |
| Exact `OBSERVED_PASS` summary | Valid envelope containing `OBSERVED_PASS` |
| Exact `OBSERVED_BLOCK` summary | Valid envelope containing `OBSERVED_BLOCK` |

Missing `binding_assessment` is passed to the official C3 builder and therefore
remains distinct from an invalid supplied assessment. Valid dependence remains
visible as `OBSERVED_BLOCK` and stays first in the blocker list.

If the C3 builder raises, returns a non-mapping, or produces a document that its
official verifier does not exactly accept, C5 returns `None`. It does not invent
or duplicate a C3 `UNKNOWN` document. C4 maps an absent envelope to its fixed
not-supplied presentation. Transport or adapter diagnostics require a separately
versioned future contract rather than reflection of an exception.

## Exact verification

The C5 verifier rebuilds the expected envelope by calling the C5 builder with the
same explicit context, then uses `strict_json_contract_equal(document, expected)`.

This rejects:

- Python boolean/integer aliases;
- tuple/list or mapping-subclass substitutions;
- missing, extra, or reordered contract structure where order is significant;
- changed C3 summary content or public-summary hash;
- changed verification validity or either verification hash;
- added adapter, endpoint, authority, or untrusted metadata;
- a valid envelope paired with another evaluation, receipt, assessment,
  assignment, policy, registry, cutoff, timestamp, or aligned-observation set.

No standalone envelope hash is added. C3 owns the public-summary seal, C5 exact
verification binds the envelope to context, and C4 independently recomputes the
C3 seal before presentation.

## Side-effect and import boundaries

C5 must not import or use:

- `server.py`, `http_contract.py`, Flask, ASGI, WSGI, or route registries;
- filesystem, database, cache, log, environment, socket, HTTP, or subprocess
  APIs;
- clocks, random values, UUIDs, schedulers, timers, callbacks, or writers;
- static frontend modules, DOM concepts, or browser globals;
- paper/live execution, portfolio mutation, pointer, publication, or artifact
  writer services.

It must not modify `services`, `domain`, `infrastructure`, or `interfaces` to add
a duplicate envelope type. The import direction is application -> services only.

## Adversarial acceptance matrix

| Attack or gap | Required result |
| --- | --- |
| Missing assessment with coherent context | Valid `NOT_SUPPLIED` envelope |
| Invalid assessment with coherent context | Valid `UNKNOWN` envelope |
| Valid C3 pass | Exact `OBSERVED_PASS` envelope |
| Valid C3 block | Exact `OBSERVED_BLOCK` envelope, dependence first |
| C3 verifier returns `False`, `1`, string, or object | `None` |
| C3 builder or verifier raises | `None`, no exception escape |
| C3 summary schema/fingerprint/hash drift | `None` |
| Envelope validity changed to `1` or `"true"` | Exact verifier rejects |
| Either verification hash changed | Exact verifier rejects |
| Real nonzero dependent count changed and summary resealed | Exact verifier rejects against original context |
| Valid envelope paired with another C3 context | Exact verifier rejects |
| Extra raw return, symbol, path, URL, callback, or authority field | Exact verifier rejects |
| Caller mutates source mappings after build | Returned envelope remains unchanged |
| Caller mutates returned envelope | Source C3 objects remain unchanged |
| File, database, socket, clock, random, UUID, callback, or writer attempt | Test failure |
| C4 consumes C5 PASS/BLOCK output | Four axes render, detached, all authority false |

At least one independent test must assert a block fixture has a real nonzero
`dependent_test_count` before mutation. It must change that count, reseal the C3
summary, and prove C5 exact verification still rejects it against the original
context.

## Consumer-first activation sequence

1. Accept this ADR while no Python adapter file exists.
2. Implement the pure application adapter and a dedicated Python contract suite.
3. Run targeted `py_compile` and the adapter suite with file, socket, database,
   clock, random, UUID, callback, and writer access denied.
4. Feed real synthetic C5 envelopes into the existing C4 Node consumer and prove
   all four states, redaction, detached DOM, and authority locks.
5. Register only the adapter tests and syntax in lean list/dry-run; execute zero
   lean checks.
6. Synchronize ADR 0055 and the three baseline documents with current hashes and
   evidence.
7. If a loopback HTTP projection is still needed, design a separate C6 transport
   ADR. Do not add a route as part of C5.
8. If a public mount is still needed, design and review it separately after C6.

No step automatically activates the next one. A pure envelope, passing tests, or
an HTTP design does not authorize mounting, current-pointer changes, paper
trading, or live trading.

## C5 implementation acceptance

C5 is complete only when current-tree evidence proves all of the following:

- the single application module and dedicated test file exist;
- its two public signatures explicitly mirror all 26 C3 keyword-only inputs;
- all four C3 states build and exactly verify through C5;
- mismatched context and real nonzero resealed tamper tests fail closed;
- C3 builder/verifier exceptions and native-bool aliases fail closed;
- no mutable alias escapes;
- denied I/O and mutation probes report zero calls;
- real synthetic C5 PASS/BLOCK envelopes pass the existing C4 consumer tests;
- `server.py`, HTTP contracts, routes, static entries, and mounted files retain
  their pre-C5 fingerprints;
- lean list/dry-run plans the new checks and executes zero;
- implementation evidence and limitations are synchronized to ADR 0055 and all
  three baseline documents.

## Consequences

C5 will close the producer/consumer gap without creating a transport or public
surface. The cost is a long explicit signature and a separate future HTTP review,
both of which make context drift and accidental activation visible.

C5 is implemented as a pure in-memory application adapter. C4 remains unmounted,
C3 v1 continues to expose `CROSS_LAG_C4_PRESENTATION_NOT_IMPLEMENTED`, and the
natural-forward chain, pointer-v2, paper lock, and permanent live lock remain
unchanged.

## Implementation closure (2026-08-21)

The accepted design is implemented in exactly two new files:

- `exchange_terminal/application/strategy_correlation_cross_lag_presentation_envelope.py`;
- `tests/test_strategy_correlation_cross_lag_presentation_envelope.py`.

The adapter exposes explicit build/verify signatures that mirror the C3 builder's
26 keyword-only inputs. It calls the official C3 builder, requires the official
C3 verifier to return native `True`, requires a strict SHA-256 public-summary
hash, deep-copies the verified summary, and emits the exact three-field C4
envelope. Exact verification rebuilds the envelope from the same context and uses
`strict_json_contract_equal`.

Targeted current-worktree evidence:

- adapter and test `py_compile`: PASS;
- C5 contract suite: 19/19 OK;
- all four C3 states preserve exact C5 envelopes and exact verification;
- independent C5-to-C4 Python/Node probe: PASS, BLOCK, NOT_SUPPLIED, and UNKNOWN
  preserved; real `dependent_test_count=1`; tamper result `UNKNOWN`; Python
  denied-I/O calls 0; Node forbidden API calls 0; detached true; mounted false;
- services reverse references to the C5 adapter: 0;
- server, HTTP, and frontend boundary references to C5/C4 activation: 0;
- lean list/dry-run: check_count 10, planned 10, completed 0, executed 0,
  reused 0, C5 contract registered, C5 syntax registered, both containing checks
  `DRY_RUN`, runtime mutations false, paper authorization false, and live order
  permission false.

Implementation fingerprints:

- adapter: `B6AED0002A0153C8CCA9F48080D1822B95FC99DEA9DBDB7310966179A2300CA7`;
- tests: `251BC1580DC38B38AAF151B9A6657097CD53BC10DA275CF6316609D5519A8AF1`;
- lean runner: `A8841B3225BC2DAF45E183FBFFB8ED5ECA3370FB0A5E41B01A49B7F52FBBBCA9`.

Boundary fingerprints remained unchanged:

- `exchange_terminal/server.py`:
  `3D93569E4A6874342CD60BCADE636FA99EAB30CA2E95A0863E1ABB5540EB7864`;
- `exchange_terminal/services/http_contract.py`:
  `526DFB623C067C46FA640E3AC6637D3DBD0B0B6F5BFD7BC359F4B001A0670C6B`;
- `exchange_terminal/static/app.js`:
  `9BF55162AFF8D7A233804557C91605C801B92F515B2835978C05E2D1F3EF9210`;
- `exchange_terminal/static/index.html`:
  `3528181954AD34F5E283CD07B7160E5F1BA1C9A5B3B14ED3E03D989697048ED9`;
- `exchange_terminal/static/styles.css`:
  `6946CC9E5542C694F7E6B9D2719ACD8B7993ACCDD47EAAFAEC6E08AB4052A910`.

No server import, HTTP contract, endpoint, route, callback, writer, pointer,
stylesheet link, frontend import, or mount was added. C5 remains an internal
producer for synthetic and future separately reviewed consumers. Its existence,
tests, envelopes, or lean registration create no formal, current, profitability,
paper, or live authority.
