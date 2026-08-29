# ADR0415: Witness ownership provider conformance neutral presentation and handoff v1

## Status

Accepted as an unmounted, neutral, research-only presentation contract. No assets, browser, route, UI mount, runtime, current, paper, live, writer, migration, or trading activation is authorized.

## Context

ADR0414 can locally verify a 2-of-3 signature quorum over structurally complete observer report claims. It deliberately does not prove observer identity, independence, test execution, provider conformance, durability, linearizability, or rollback resistance. A future UI must not flatten that distinction into a positive readiness or profitability signal, and it must not expose raw reports, keys, signatures, provider material, or ownership documents.

The repository already uses the neutral stage order `SOURCE -> GAP -> MATURITY -> PERMISSION` for unmounted conformance presentations. ADR0415 keeps that visual language while making the maturity label claim-calibrated for ADR0414.

## Decision

Add an exact presentation envelope with four ordered axes:

- `SOURCE / LOCALLY_BOUND`: ADR0412 atomic port, ADR0413 signed receipt, and ADR0414 observer quorum are exactly rebuilt locally.
- `GAP / OPEN`: observer identity, independence, external test execution, provider source truth, durability, linearizability, and rollback resistance remain unverified.
- `MATURITY / SIGNED_REPORT_CANDIDATE`: 18 case results are claimed by a local 2-of-3 signature quorum, while verified external execution count remains zero.
- `PERMISSION / BLOCKED`: assets, browser, route, mount, current, runtime, paper, live, and writer remain disabled.

Add a bounded handoff containing only display fields, blockers, summary, blocked permission, and the presentation-envelope hash. It excludes raw source documents, observer reports, identities, public keys, signatures, test transcripts, provider credentials, and ownership documents.

The handoff pins existing protected stylesheet, app, and evidence-presentation hashes but has no consumer JavaScript or stylesheet. It is not mounted.

## Adversarial matrix

- inexact or resealed upstream quorum: presentation becomes `UNMOUNTED_UNKNOWN` with all axes `UNKNOWN`.
- source axis cannot imply external source truth.
- maturity axis cannot promote claimed case results to verified execution.
- permission axis and all authority fields remain blocked.
- raw report, key, and signature material is absent.
- unknown presentation cannot enter the handoff.
- resealed presentation or handoff permission promotion: exact rebuild verification fails.
- report order changes do not change the presentation.
- `READY`, profitability, assets, browser, route, and mount claims are absent.

## Consequences and limits

ADR0415 provides a safe, bounded data model for future frontend work without touching protected assets. It does not beautify or mount a rendered interface, run a browser, establish accessibility or responsive behavior, invoke providers or observers, prove external conformance, or authorize any trading capability.

The natural-forward chain remains `audit-v2/readiness-v3 -> maturity-v3/dashboard-v7 -> pack-v6/evidence-v2 -> snapshot-v4/summary-v2`. Legacy pack-v5 public reads remain `UNKNOWN`; pointer-v2 is unchanged and not reissued.
