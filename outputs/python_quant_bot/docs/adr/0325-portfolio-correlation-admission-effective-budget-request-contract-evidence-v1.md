# ADR 0325: Request-contract evidence v1

## Status

Accepted as a synthetic, in-memory, unregistered request-binding candidate and
an adapter `lock-3` revision. No HTTP or trading capability is activated.

## Context

ADR0324 established source-bearing projection provenance, but the request-scope
builder still accepted `request_contract_hash` as a caller-provided 64-hex value.
The adapter separately accepted a request mapping. A caller could therefore
provide a valid-looking scope hash unrelated to the actual projection request.

The current projection request is intentionally narrow and non-sensitive: exact
`schema_version` and exact `projection_id`, with no market source, portfolio,
position, strategy, secret, or user input fields.

## Decision

Add request-contract evidence with contract hash:

`cae0e79f6ad2ceec2444574858ab9d542ebb4912c1e7d463b8a426ba15dc165a`

The builder snapshots the supplied JSON mapping once, rejects missing or extra
fields, fixes the proposed `POST` research route, and derives:

- request payload hash
  `03d52bc29aa187160a9a1ff0a67a5f58835a0b48d787da399dbe950f4bbe24f9`
- request-contract hash
  `7423b83ea15bc410a10ec6964dc906c60368a2147a19e16ebeffdf6a8175b5b4`

The adapter is revised to `lock-3` contract hash:

`ff4de40e1323657a1df6213616c9fd2c92e194f7545bee54bfe4108132e1333f`

The prior ADR0324 `lock-2` hash
`dd03303578e6b070b9c5ec6d6891658f63dd453001f30cdb069a9a03ac38a00c`
is lineage only. The revised adapter:

1. Accepts request-contract evidence instead of a second raw request argument.
2. Exact-verifies the evidence before context consumption.
3. Requires the request scope's `request_contract_hash` to equal the value
   derived from the evidence snapshot.
4. Invokes the projection only with that verified snapshot.
5. Carries request payload and contract hashes, not a duplicate request or any
   source document, in adapter evidence.

## Adversarial matrix

| Case | Required result |
| --- | --- |
| Exact request snapshot and matching scope | Known synthetic projection reproduced |
| Missing, extra, wrong-schema, or wrong-ID request field | No evidence candidate |
| Request evidence mutation | Exact verification fails |
| Scope contains unrelated caller hash | Adapter rejects before context consumption |
| Second raw request differs from evidence | Impossible through adapter API |
| Source-bearing semantic verification | Uses evidence snapshot and exact 23 sources |
| HTTP/runtime/paper/live inference | Explicitly false |

## Consequences

The adapter now has one request authority inside the synthetic call chain. This
does not authenticate the caller or prove that a future HTTP parser produced the
snapshot. Real security receipt providers, authenticated request-lifecycle
ownership, internal registration, mount controls, and independent exposure
review remain blockers.

Natural-forward evidence, legacy pack-v5 `UNKNOWN`, pointer-v2, profitability
claims, and paper/live locks remain unchanged.
