# ADR 0011: Schema17 complete-link consumer before writer

Status: Consumer implemented; writer and current activation unavailable

## Context

ADR 0010 introduced a verified complete-link v2 gate but deliberately did not add it to the schema16 writer. A migration must not trust a fabricated PASS receipt or silently reinterpret an existing schema16 report.

## Decision

Add `strategy-research-complete-link-extension-v1` as a consumer-only contract targeting future report schema17 and protocol-v6.

The verifier requires an expected SHA-256 for a schema16 report that the caller has independently verified. It then rebuilds every embedded v2 gate from preregistration, correlation matrix, selection cells, and identity. It rejects v1 substitution, nested resealing, base-hash drift, duplicate or unordered identities, extra authority aliases, and non-exact fields.

The module intentionally exposes no writer or builder. A contract-valid extension may carry a `BLOCK` decision as negative evidence. Verifier PASS never implies strategy admission.

## Activation order

1. Existing schema16 verification must pass independently.
2. Pass the verified schema16 report hash to the extension consumer.
3. Add protocol-v6 registration and a sole schema17 writer only after migration tests exist.
4. Keep current, paper, and live authority false until a separately authorized release.

## Consequences

- Consumer semantics exist before any producer can publish schema17.
- Historical schema16 reports remain immutable and independently meaningful.
- Complete-link negative evidence can be preserved without becoming READY or current.
- No profitability or execution claim is introduced.
