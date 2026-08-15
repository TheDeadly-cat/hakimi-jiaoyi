from __future__ import annotations

from contextlib import closing
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time
from typing import Any, Callable

from exchange_terminal.services.corporate_action_ledger import (
    REQUIRED_OFFICIAL_ACTION_TYPES,
    build_corporate_action_source_evidence,
    build_official_corporate_action_attestation,
    normalize_corporate_actions,
    verify_official_corporate_action_attestation,
)
from exchange_terminal.services.portfolio_universe import (
    build_membership_source_evidence,
    build_point_in_time_universe_contract,
    normalize_membership_records,
    verify_universe_contract,
)
from exchange_terminal.services.security_lifecycle import normalize_security_lifecycle_events


REFERENCE_DATA_IMPORT_SCHEMA_VERSION = "portfolio-reference-data-import-v1"
REFERENCE_DATA_PACK_SCHEMA_VERSION = "portfolio-reference-data-pack-v1"
REFERENCE_DATA_STORE_SCHEMA_VERSION = "portfolio-reference-data-store-v1"
MEMBERSHIP_SOURCE_SCHEMA_VERSION = "point-in-time-membership-source-v1"
CORPORATE_ACTION_SOURCE_SCHEMA_VERSION = "official-corporate-action-source-v1"
MAX_SOURCE_DOCUMENT_BYTES = 64 * 1024 * 1024
AUTHORITY_FIELDS = {
    "automatic_paper_activation_allowed",
    "live_order_allowed",
    "paper_authorized",
}


def canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _clean_timestamp(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return ""
    if parsed.tzinfo is None:
        return ""
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_date(value: Any) -> str:
    text = str(value or "").strip()[:10]
    try:
        return date.fromisoformat(text).isoformat()
    except ValueError:
        return ""


def _symbols(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return sorted({str(item or "").strip().upper() for item in values if str(item or "").strip()})


def authority_violations(payload: Any, *, path: str = "$") -> list[str]:
    violations: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child = f"{path}.{key}"
            if key in AUTHORITY_FIELDS and value is not False:
                violations.append(child)
            violations.extend(authority_violations(value, path=child))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            violations.extend(authority_violations(value, path=f"{path}[{index}]"))
    return violations


def load_json_object(path: Path | str) -> tuple[dict[str, Any], str]:
    source = Path(path).resolve()
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {source}")
    return payload, file_sha256(source)


def _load_source_document(
    package_root: Path,
    descriptor: dict[str, Any],
    *,
    source_kind: str,
    expected_schema: str,
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    blockers: list[str] = []
    relative_text = str(descriptor.get("document_path") or "").strip()
    relative = Path(relative_text)
    resolved = (package_root / relative).resolve() if relative_text else package_root
    if not relative_text or relative.is_absolute() or relative.drive:
        blockers.append(f"{source_kind}_document_path_invalid")
    elif not resolved.is_relative_to(package_root):
        blockers.append(f"{source_kind}_document_path_escape")
    elif not resolved.is_file():
        blockers.append(f"{source_kind}_document_missing:{relative.as_posix()}")

    expected_hash = str(descriptor.get("document_sha256") or "").strip().lower()
    payload: dict[str, Any] = {}
    actual_hash = ""
    size_bytes = 0
    if not blockers:
        try:
            size_bytes = resolved.stat().st_size
            if size_bytes > MAX_SOURCE_DOCUMENT_BYTES:
                blockers.append(f"{source_kind}_document_too_large:{size_bytes}")
            else:
                actual_hash = file_sha256(resolved)
                raw = json.loads(resolved.read_text(encoding="utf-8"))
                if not isinstance(raw, dict):
                    blockers.append(f"{source_kind}_document_object_required")
                else:
                    payload = raw
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            blockers.append(f"{source_kind}_document_unreadable:{type(exc).__name__}")
    if not _valid_sha256(expected_hash):
        blockers.append(f"{source_kind}_document_expected_hash_invalid")
    elif actual_hash and actual_hash != expected_hash:
        blockers.append(f"{source_kind}_document_hash_mismatch")
    if payload and str(payload.get("schema_version") or "") != expected_schema:
        blockers.append(f"{source_kind}_document_schema_invalid")

    metadata = {
        "source_kind": source_kind,
        "document_path": relative.as_posix() if relative_text else "",
        "expected_document_sha256": expected_hash,
        "actual_document_sha256": actual_hash,
        "size_bytes": size_bytes,
        "source_authority": str(descriptor.get("source_authority") or "").strip().upper(),
        "source_name": str(descriptor.get("source_name") or "").strip(),
        "evidence_ref": str(descriptor.get("evidence_ref") or "").strip(),
    }
    metadata["metadata_hash"] = canonical_hash(metadata)
    return payload, metadata, blockers


def _membership_records_from_source(
    descriptor: dict[str, Any],
    document: dict[str, Any],
    document_sha256: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    blockers: list[str] = []
    raw_records = document.get("records")
    if not isinstance(raw_records, list) or not raw_records:
        return [], ["membership_source_records_missing"]
    authority = str(descriptor.get("source_authority") or "").strip().upper()
    source_name = str(descriptor.get("source_name") or "").strip()
    evidence_ref = str(descriptor.get("evidence_ref") or "").strip()
    published_at = _clean_timestamp(descriptor.get("evidence_published_at"))
    retrieved_at = _clean_timestamp(descriptor.get("retrieved_at"))
    records: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_records):
        if not isinstance(raw, dict):
            blockers.append(f"membership_source_record_invalid:{index}")
            continue
        symbol = str(raw.get("symbol") or "").strip().upper()
        effective_from = _clean_date(raw.get("effective_from"))
        effective_to = _clean_date(raw.get("effective_to"))
        evidence = build_membership_source_evidence(
            symbol=symbol,
            effective_from=effective_from,
            effective_to=effective_to,
            source_authority=authority,
            source_name=source_name,
            evidence_ref=evidence_ref,
            source_document_sha256=document_sha256,
            evidence_published_at=published_at,
            retrieved_at=retrieved_at,
        )
        records.append({
            "symbol": symbol,
            "effective_from": effective_from,
            "effective_to": effective_to,
            "source_authority": authority,
            "source_name": source_name,
            "evidence_ref": evidence_ref,
            "evidence_sha256": evidence["evidence_sha256"],
            "evidence_published_at": published_at,
            "evidence_payload": evidence,
        })
    return records, blockers


def _normalize_corporate_source(
    descriptor: dict[str, Any],
    document: dict[str, Any],
    metadata: dict[str, Any],
    *,
    package_prepared_at: str,
) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    covered_symbols = _symbols(document.get("covered_symbols"))
    coverage_start = _clean_date(document.get("coverage_start"))
    coverage_end = _clean_date(document.get("coverage_end"))
    coverage_types = sorted({
        str(item or "").strip().upper()
        for item in document.get("coverage_types") or []
        if str(item or "").strip()
    }) if isinstance(document.get("coverage_types"), list) else []
    raw_records = document.get("records")
    if not isinstance(raw_records, list):
        blockers.append("corporate_action_source_records_type_invalid")
        raw_records = []
    if not covered_symbols:
        blockers.append("corporate_action_source_covered_symbols_missing")
    if not coverage_start or not coverage_end or coverage_start > coverage_end:
        blockers.append("corporate_action_source_coverage_window_invalid")

    provider = str(descriptor.get("provider_id") or descriptor.get("source_name") or "official").strip().lower()
    actions_by_symbol: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in covered_symbols}
    lifecycle_by_symbol: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in covered_symbols}
    normalized_count = 0
    for index, raw in enumerate(raw_records):
        if not isinstance(raw, dict):
            blockers.append(f"corporate_action_source_record_invalid:{index}")
            continue
        symbol = str(raw.get("symbol") or "").strip().upper()
        action_type = str(raw.get("action_type") or raw.get("type") or "").strip().upper()
        if symbol not in actions_by_symbol:
            blockers.append(f"corporate_action_record_symbol_not_covered:{symbol or '--'}")
            continue
        if action_type in {"SPLIT", "DIVIDEND"}:
            normalized = normalize_corporate_actions(symbol, provider, [{**raw, "provider": provider}])
            if len(normalized) != 1:
                blockers.append(f"corporate_action_record_not_normalized:{symbol}:{index}")
                continue
            actions_by_symbol[symbol].extend(normalized)
            normalized_count += 1
            continue
        lifecycle_status = {
            "SUSPENSION": "SUSPENDED",
            "SUSPENDED": "SUSPENDED",
            "HALT": "HALTED",
            "HALTED": "HALTED",
            "DELISTING": "DELISTED",
            "DELISTED": "DELISTED",
        }.get(action_type, "")
        if lifecycle_status:
            normalized = normalize_security_lifecycle_events(symbol, [{
                **raw,
                "status": lifecycle_status,
                "provider": provider,
            }])
            if len(normalized) != 1:
                blockers.append(f"security_lifecycle_record_not_normalized:{symbol}:{index}")
                continue
            lifecycle_by_symbol[symbol].extend(normalized)
            normalized_count += 1
            continue
        blockers.append(f"corporate_action_record_type_unsupported:{action_type or '--'}:{index}")
    if normalized_count != len(raw_records):
        blockers.append(f"corporate_action_normalized_count_mismatch:{normalized_count}!={len(raw_records)}")

    observed_at = _clean_timestamp(descriptor.get("observed_at"))
    if observed_at and package_prepared_at and observed_at > package_prepared_at:
        blockers.append("corporate_action_source_observed_after_package_prepared")
    if observed_at and coverage_end and observed_at[:10] < coverage_end:
        blockers.append("corporate_action_source_observed_before_coverage_end")
    source_evidence = build_corporate_action_source_evidence(
        source_authority=str(descriptor.get("source_authority") or ""),
        source_name=str(descriptor.get("source_name") or ""),
        evidence_ref=str(descriptor.get("evidence_ref") or ""),
        source_document_sha256=str(metadata.get("actual_document_sha256") or ""),
        observed_at=observed_at,
        coverage_types=coverage_types,
        record_count=len(raw_records),
    )
    attestation = build_official_corporate_action_attestation(
        source_authority=str(descriptor.get("source_authority") or ""),
        source_name=str(descriptor.get("source_name") or ""),
        evidence_ref=str(descriptor.get("evidence_ref") or ""),
        evidence_sha256=str(source_evidence.get("evidence_sha256") or ""),
        observed_at=observed_at,
        coverage_types=coverage_types,
        evidence_payload=source_evidence,
    )
    attestation_audit = verify_official_corporate_action_attestation(attestation)
    blockers.extend(f"corporate_action_attestation:{item}" for item in attestation_audit.get("blockers") or [])
    entry = {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "provider_id": provider,
        "source_document": metadata,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "covered_symbols": covered_symbols,
        "coverage_types": coverage_types,
        "record_count": len(raw_records),
        "attestation": attestation,
        "actions_by_symbol": {
            symbol: normalize_corporate_actions(symbol, provider, actions)
            for symbol, actions in sorted(actions_by_symbol.items())
        },
        "security_lifecycle_by_symbol": {
            symbol: normalize_security_lifecycle_events(symbol, events)
            for symbol, events in sorted(lifecycle_by_symbol.items())
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    entry["source_hash"] = canonical_hash(entry)
    return entry, blockers


def _merge_symbol_records(
    expected_symbols: list[str],
    sources: list[dict[str, Any]],
    field: str,
    id_field: str,
) -> dict[str, list[dict[str, Any]]]:
    merged = {symbol: {} for symbol in expected_symbols}
    for source in sources:
        records_by_symbol = source.get(field)
        if not isinstance(records_by_symbol, dict):
            continue
        for symbol, records in records_by_symbol.items():
            if symbol not in merged or not isinstance(records, list):
                continue
            for record in records:
                if isinstance(record, dict) and str(record.get(id_field) or ""):
                    merged[symbol][str(record[id_field])] = dict(record)
    return {
        symbol: sorted(records.values(), key=lambda item: (
            str(item.get("event_date") or item.get("start_date") or ""),
            str(item.get(id_field) or ""),
        ))
        for symbol, records in merged.items()
    }


def _coverage_summary(
    expected_symbols: list[str],
    coverage_start: str,
    coverage_end: str,
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    fully_covered: list[str] = []
    for symbol in expected_symbols:
        if any(
            source.get("status") == "PASS"
            and symbol in list(source.get("covered_symbols") or [])
            and str(source.get("coverage_start") or "") <= coverage_start
            and str(source.get("coverage_end") or "") >= coverage_end
            for source in sources
        ):
            fully_covered.append(symbol)
    missing = sorted(set(expected_symbols) - set(fully_covered))
    return {
        "expected_symbol_count": len(expected_symbols),
        "fully_covered_symbol_count": len(fully_covered),
        "fully_covered_symbols": sorted(fully_covered),
        "missing_symbols": missing,
        "coverage_start": coverage_start,
        "coverage_end": coverage_end,
        "required_action_types": sorted(REQUIRED_OFFICIAL_ACTION_TYPES),
        "official_source_count": sum(source.get("status") == "PASS" for source in sources),
    }


def build_reference_data_pack(
    manifest: dict[str, Any],
    *,
    package_root: Path | str,
    manifest_file: str = "",
    manifest_sha256: str = "",
) -> dict[str, Any]:
    manifest = dict(manifest) if isinstance(manifest, dict) else {}
    root = Path(package_root).resolve()
    blockers: list[str] = []
    if str(manifest.get("schema_version") or "") != REFERENCE_DATA_IMPORT_SCHEMA_VERSION:
        blockers.append("reference_data_import_schema_invalid")
    package_id = str(manifest.get("package_id") or "").strip()
    prepared_at = _clean_timestamp(manifest.get("prepared_at"))
    if not package_id:
        blockers.append("reference_data_package_id_missing")
    if not prepared_at:
        blockers.append("reference_data_prepared_at_invalid")
    manifest_hash = str(manifest_sha256 or "").strip().lower() or canonical_hash(manifest)
    if not _valid_sha256(manifest_hash):
        blockers.append("reference_data_manifest_hash_invalid")
    blockers.extend(f"manifest_execution_authority:{item}" for item in authority_violations(manifest))

    universe = dict(manifest.get("universe") or {}) if isinstance(manifest.get("universe"), dict) else {}
    benchmark = str(universe.get("benchmark_symbol") or "").strip().upper()
    tradable = _symbols(universe.get("tradable_symbols"))
    selection_basis = str(universe.get("selection_basis") or "").strip()
    selection_rule_id = str(universe.get("selection_rule_id") or "").strip()
    coverage_start = _clean_date(universe.get("coverage_start"))
    coverage_end = _clean_date(universe.get("coverage_end"))
    if selection_basis.startswith("REPLACE_") or selection_rule_id.startswith("REPLACE_"):
        blockers.append("reference_data_selection_rule_placeholder_not_replaced")
    membership_sources_value = universe.get("sources")
    if not isinstance(membership_sources_value, list) or not membership_sources_value:
        blockers.append("reference_data_membership_sources_missing")
        membership_sources_value = []

    source_documents: list[dict[str, Any]] = []
    membership_records: list[dict[str, Any]] = []
    membership_source_rows: list[dict[str, Any]] = []
    for index, value in enumerate(membership_sources_value):
        descriptor = dict(value) if isinstance(value, dict) else {}
        document, metadata, source_blockers = _load_source_document(
            root,
            descriptor,
            source_kind="membership",
            expected_schema=MEMBERSHIP_SOURCE_SCHEMA_VERSION,
        )
        records: list[dict[str, Any]] = []
        if not source_blockers:
            records, record_blockers = _membership_records_from_source(
                descriptor,
                document,
                str(metadata.get("actual_document_sha256") or ""),
            )
            source_blockers.extend(record_blockers)
        blockers.extend(f"membership_source_{index}:{item}" for item in source_blockers)
        source_documents.append(metadata)
        membership_records.extend(records)
        membership_source_row = {
            "status": "PASS" if not source_blockers else "BLOCK",
            "blockers": list(dict.fromkeys(source_blockers)),
            "source_document": metadata,
            "evidence_published_at": _clean_timestamp(descriptor.get("evidence_published_at")),
            "retrieved_at": _clean_timestamp(descriptor.get("retrieved_at")),
            "record_count": len(records),
            "membership_records": records,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        membership_source_row["source_hash"] = canonical_hash(membership_source_row)
        membership_source_rows.append(membership_source_row)

    universe_contract = build_point_in_time_universe_contract(
        benchmark_symbol=benchmark,
        tradable_symbols=tradable,
        declared_at=prepared_at,
        selection_basis=selection_basis,
        selection_rule_id=selection_rule_id,
        coverage_start=coverage_start,
        coverage_end=coverage_end,
        membership_records=membership_records,
    )
    universe_audit = verify_universe_contract(universe_contract)
    blockers.extend(f"universe_contract:{item}" for item in universe_audit.get("blockers") or [])

    expected_symbols = sorted(set([benchmark, *tradable]) - {""})
    corporate_sources_value = manifest.get("corporate_action_sources")
    if not isinstance(corporate_sources_value, list) or not corporate_sources_value:
        blockers.append("reference_data_corporate_action_sources_missing")
        corporate_sources_value = []
    corporate_sources: list[dict[str, Any]] = []
    for index, value in enumerate(corporate_sources_value):
        descriptor = dict(value) if isinstance(value, dict) else {}
        document, metadata, source_blockers = _load_source_document(
            root,
            descriptor,
            source_kind="corporate_action",
            expected_schema=CORPORATE_ACTION_SOURCE_SCHEMA_VERSION,
        )
        entry: dict[str, Any] = {
            "status": "BLOCK",
            "blockers": list(source_blockers),
            "source_document": metadata,
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }
        if not source_blockers:
            entry, normalization_blockers = _normalize_corporate_source(
                descriptor,
                document,
                metadata,
                package_prepared_at=prepared_at,
            )
            source_blockers.extend(normalization_blockers)
        blockers.extend(f"corporate_action_source_{index}:{item}" for item in source_blockers)
        source_documents.append(metadata)
        corporate_sources.append(entry)

    actions_by_symbol = _merge_symbol_records(
        expected_symbols,
        corporate_sources,
        "actions_by_symbol",
        "action_id",
    )
    lifecycle_by_symbol = _merge_symbol_records(
        expected_symbols,
        corporate_sources,
        "security_lifecycle_by_symbol",
        "event_hash",
    )
    coverage = _coverage_summary(expected_symbols, coverage_start, coverage_end, corporate_sources)
    blockers.extend(f"corporate_action_coverage_missing:{symbol}" for symbol in coverage["missing_symbols"])
    blockers = list(dict.fromkeys(blockers))
    status = "PASS" if not blockers else "BLOCK"
    payload = {
        "schema_version": REFERENCE_DATA_PACK_SCHEMA_VERSION,
        "status": status,
        "blockers": blockers,
        "admission_status": (
            "REFERENCE_EVIDENCE_READY_FOR_MANUAL_REVIEW" if status == "PASS" else "BLOCK"
        ),
        "package_id": package_id,
        "prepared_at": prepared_at,
        "manifest_file": str(manifest_file or ""),
        "manifest_sha256": manifest_hash,
        "source_documents": source_documents,
        "membership_sources": membership_source_rows,
        "universe_contract": universe_contract,
        "universe_contract_verification": universe_audit,
        "corporate_action_sources": corporate_sources,
        "corporate_actions_by_symbol": actions_by_symbol,
        "security_lifecycle_by_symbol": lifecycle_by_symbol,
        "coverage_summary": coverage,
        "g42_protocol_input_ready": status == "PASS",
        "manual_source_identity_review_required": True,
        "automatic_paper_activation_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["pack_hash"] = canonical_hash(payload)
    return payload


def build_reference_data_pack_from_manifest(path: Path | str) -> dict[str, Any]:
    manifest_path = Path(path).resolve()
    manifest, manifest_hash = load_json_object(manifest_path)
    return build_reference_data_pack(
        manifest,
        package_root=manifest_path.parent,
        manifest_file=manifest_path.name,
        manifest_sha256=manifest_hash,
    )


def verify_reference_data_pack(
    payload: dict[str, Any],
    *,
    source_root: Path | str | None = None,
) -> dict[str, Any]:
    payload = dict(payload) if isinstance(payload, dict) else {}
    clean = dict(payload)
    expected_hash = str(clean.pop("pack_hash", "") or "")
    blockers: list[str] = []
    if payload.get("schema_version") != REFERENCE_DATA_PACK_SCHEMA_VERSION:
        blockers.append("reference_data_pack_schema_invalid")
    if not _valid_sha256(expected_hash) or canonical_hash(clean) != expected_hash:
        blockers.append("reference_data_pack_hash_invalid")
    declared = payload.get("blockers")
    declared_blockers = [str(item) for item in declared or [] if str(item)] if isinstance(declared, list) else []
    if not isinstance(declared, list):
        blockers.append("reference_data_declared_blockers_type_invalid")
    blockers.extend(f"reference_data_declared_blocker:{item}" for item in declared_blockers)
    if not _valid_sha256(payload.get("manifest_sha256")):
        blockers.append("reference_data_manifest_hash_invalid")

    root = Path(source_root).resolve() if source_root is not None else None
    if root is None or not root.is_dir():
        blockers.append("reference_data_source_root_unavailable")

    documents = payload.get("source_documents")
    if not isinstance(documents, list) or not documents:
        blockers.append("reference_data_source_documents_missing")
        documents = []
    for index, item in enumerate(documents):
        if not isinstance(item, dict):
            blockers.append(f"reference_data_source_document_invalid:{index}")
            continue
        metadata = dict(item)
        metadata_hash = str(metadata.pop("metadata_hash", "") or "")
        if not _valid_sha256(metadata_hash) or canonical_hash(metadata) != metadata_hash:
            blockers.append(f"reference_data_source_metadata_hash_invalid:{index}")
        expected = str(item.get("expected_document_sha256") or "")
        actual = str(item.get("actual_document_sha256") or "")
        if not _valid_sha256(expected) or expected != actual:
            blockers.append(f"reference_data_source_document_hash_invalid:{index}")

    membership_sources_value = payload.get("membership_sources")
    membership_sources = (
        [dict(item) for item in membership_sources_value if isinstance(item, dict)]
        if isinstance(membership_sources_value, list)
        else []
    )
    if not membership_sources:
        blockers.append("reference_data_membership_sources_missing")
    rebuilt_membership_records: list[dict[str, Any]] = []
    rebuilt_documents: list[dict[str, Any]] = []
    for index, source in enumerate(membership_sources):
        source_clean = dict(source)
        source_hash = str(source_clean.pop("source_hash", "") or "")
        if not _valid_sha256(source_hash) or canonical_hash(source_clean) != source_hash:
            blockers.append(f"reference_data_membership_source_hash_invalid:{index}")
        metadata = dict(source.get("source_document") or {})
        rebuilt_documents.append(metadata)
        if root is None:
            continue
        descriptor = {
            "document_path": str(metadata.get("document_path") or ""),
            "document_sha256": str(metadata.get("expected_document_sha256") or ""),
            "source_authority": str(metadata.get("source_authority") or ""),
            "source_name": str(metadata.get("source_name") or ""),
            "evidence_ref": str(metadata.get("evidence_ref") or ""),
            "evidence_published_at": str(source.get("evidence_published_at") or ""),
            "retrieved_at": str(source.get("retrieved_at") or ""),
        }
        document, rebuilt_metadata, source_blockers = _load_source_document(
            root,
            descriptor,
            source_kind="membership",
            expected_schema=MEMBERSHIP_SOURCE_SCHEMA_VERSION,
        )
        rebuilt_records: list[dict[str, Any]] = []
        if not source_blockers:
            rebuilt_records, record_blockers = _membership_records_from_source(
                descriptor,
                document,
                str(rebuilt_metadata.get("actual_document_sha256") or ""),
            )
            source_blockers.extend(record_blockers)
        blockers.extend(f"reference_data_membership_source_{index}:{item}" for item in source_blockers)
        if rebuilt_metadata != metadata:
            blockers.append(f"reference_data_membership_source_metadata_mismatch:{index}")
        if source.get("membership_records") != rebuilt_records:
            blockers.append(f"reference_data_membership_records_mismatch:{index}")
        if source.get("record_count") != len(rebuilt_records):
            blockers.append(f"reference_data_membership_record_count_mismatch:{index}")
        expected_source_status = "PASS" if not source_blockers else "BLOCK"
        if source.get("status") != expected_source_status or source.get("blockers") != list(dict.fromkeys(source_blockers)):
            blockers.append(f"reference_data_membership_source_status_mismatch:{index}")
        rebuilt_membership_records.extend(rebuilt_records)

    universe = dict(payload.get("universe_contract") or {})
    universe_audit = verify_universe_contract(universe)
    if universe_audit.get("status") != "PASS" or universe_audit.get("historical_membership_verified") is not True:
        blockers.extend(f"reference_data_universe:{item}" for item in universe_audit.get("blockers") or ["not_verified"])
    if payload.get("universe_contract_verification") != universe_audit:
        blockers.append("reference_data_universe_audit_mismatch")
    if root is not None and universe.get("membership_records") != normalize_membership_records(rebuilt_membership_records):
        blockers.append("reference_data_universe_membership_source_binding_mismatch")

    expected_symbols = sorted(set([
        str(universe.get("benchmark_symbol") or ""),
        *_symbols(universe.get("tradable_symbols")),
    ]) - {""})
    sources_value = payload.get("corporate_action_sources")
    sources = [dict(item) for item in sources_value or [] if isinstance(item, dict)] if isinstance(sources_value, list) else []
    if not sources:
        blockers.append("reference_data_corporate_sources_missing")
    for index, source in enumerate(sources):
        source_clean = dict(source)
        source_hash = str(source_clean.pop("source_hash", "") or "")
        if not _valid_sha256(source_hash) or canonical_hash(source_clean) != source_hash:
            blockers.append(f"reference_data_corporate_source_hash_invalid:{index}")
        attestation = dict(source.get("attestation") or {})
        metadata = dict(source.get("source_document") or {})
        rebuilt_documents.append(metadata)
        if root is not None:
            descriptor = {
                "provider_id": str(source.get("provider_id") or ""),
                "document_path": str(metadata.get("document_path") or ""),
                "document_sha256": str(metadata.get("expected_document_sha256") or ""),
                "source_authority": str(attestation.get("source_authority") or metadata.get("source_authority") or ""),
                "source_name": str(attestation.get("source_name") or metadata.get("source_name") or ""),
                "evidence_ref": str(attestation.get("evidence_ref") or metadata.get("evidence_ref") or ""),
                "observed_at": str(attestation.get("observed_at") or ""),
            }
            document, rebuilt_metadata, source_blockers = _load_source_document(
                root,
                descriptor,
                source_kind="corporate_action",
                expected_schema=CORPORATE_ACTION_SOURCE_SCHEMA_VERSION,
            )
            rebuilt_source: dict[str, Any] = {}
            if not source_blockers:
                rebuilt_source, normalization_blockers = _normalize_corporate_source(
                    descriptor,
                    document,
                    rebuilt_metadata,
                    package_prepared_at=str(payload.get("prepared_at") or ""),
                )
                source_blockers.extend(normalization_blockers)
            blockers.extend(f"reference_data_corporate_source_{index}:{item}" for item in source_blockers)
            if rebuilt_metadata != metadata:
                blockers.append(f"reference_data_corporate_source_metadata_mismatch:{index}")
            if not source_blockers and rebuilt_source != source:
                blockers.append(f"reference_data_corporate_source_content_mismatch:{index}")
        attestation_audit = verify_official_corporate_action_attestation(attestation)
        if attestation_audit.get("status") != "PASS":
            blockers.extend(
                f"reference_data_corporate_attestation_{index}:{item}"
                for item in attestation_audit.get("blockers") or ["not_verified"]
            )
        document_hash = str((source.get("source_document") or {}).get("actual_document_sha256") or "")
        evidence_document_hash = str((attestation.get("evidence_payload") or {}).get("source_document_sha256") or "")
        if not _valid_sha256(document_hash) or document_hash != evidence_document_hash:
            blockers.append(f"reference_data_corporate_document_binding_invalid:{index}")
        if source.get("status") != "PASS" or source.get("blockers") != []:
            blockers.append(f"reference_data_corporate_source_blocked:{index}")

    if documents != rebuilt_documents:
        blockers.append("reference_data_source_document_index_mismatch")

    rebuilt_actions = _merge_symbol_records(expected_symbols, sources, "actions_by_symbol", "action_id")
    rebuilt_lifecycle = _merge_symbol_records(
        expected_symbols,
        sources,
        "security_lifecycle_by_symbol",
        "event_hash",
    )
    if payload.get("corporate_actions_by_symbol") != rebuilt_actions:
        blockers.append("reference_data_corporate_actions_mismatch")
    if payload.get("security_lifecycle_by_symbol") != rebuilt_lifecycle:
        blockers.append("reference_data_security_lifecycle_mismatch")
    coverage = _coverage_summary(
        expected_symbols,
        str(universe.get("coverage_start") or ""),
        str(universe.get("coverage_end") or ""),
        sources,
    )
    if payload.get("coverage_summary") != coverage:
        blockers.append("reference_data_coverage_summary_mismatch")
    blockers.extend(f"reference_data_corporate_coverage_missing:{item}" for item in coverage["missing_symbols"])
    blockers.extend(f"reference_data_execution_authority:{item}" for item in authority_violations(payload))
    if payload.get("manual_source_identity_review_required") is not True:
        blockers.append("reference_data_manual_source_review_not_required")
    if payload.get("automatic_paper_activation_allowed") is not False:
        blockers.append("reference_data_automatic_paper_activation_not_blocked")
    expected_status = "PASS" if not declared_blockers else "BLOCK"
    if payload.get("status") != expected_status:
        blockers.append("reference_data_status_semantic_mismatch")
    expected_admission = (
        "REFERENCE_EVIDENCE_READY_FOR_MANUAL_REVIEW" if expected_status == "PASS" else "BLOCK"
    )
    if payload.get("admission_status") != expected_admission:
        blockers.append("reference_data_admission_status_semantic_mismatch")
    if payload.get("g42_protocol_input_ready") is not (expected_status == "PASS"):
        blockers.append("reference_data_protocol_readiness_mismatch")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "pack_hash": expected_hash,
        "manual_source_identity_review_required": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


class ReferenceDataStore:
    """Append-only local evidence index. Source files remain outside the database."""

    def __init__(self, db_path: Path | str, now_ms: Callable[[], int] | None = None) -> None:
        self.db_path = Path(db_path)
        self.now_ms = now_ms or (lambda: int(time.time() * 1000))
        self._lock = threading.RLock()
        self._ensure_schema()

    def _connect(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.db_path, timeout=15)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _ensure_schema(self) -> None:
        with self._lock, closing(self._connect()) as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS reference_data_schema (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reference_data_packs (
                    pack_hash TEXT PRIMARY KEY,
                    package_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    prepared_at TEXT NOT NULL,
                    imported_at INTEGER NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reference_source_documents (
                    document_sha256 TEXT NOT NULL,
                    source_kind TEXT NOT NULL,
                    pack_hash TEXT NOT NULL,
                    source_authority TEXT NOT NULL,
                    source_name TEXT NOT NULL,
                    evidence_ref TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY(document_sha256, source_kind, pack_hash),
                    FOREIGN KEY(pack_hash) REFERENCES reference_data_packs(pack_hash)
                );
                CREATE TABLE IF NOT EXISTS reference_universe_contracts (
                    contract_hash TEXT PRIMARY KEY,
                    pack_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    coverage_start TEXT NOT NULL,
                    coverage_end TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(pack_hash) REFERENCES reference_data_packs(pack_hash)
                );
                CREATE TABLE IF NOT EXISTS reference_corporate_sources (
                    source_hash TEXT PRIMARY KEY,
                    pack_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attestation_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(pack_hash) REFERENCES reference_data_packs(pack_hash)
                );
                CREATE TABLE IF NOT EXISTS reference_corporate_actions (
                    pack_hash TEXT NOT NULL,
                    action_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    event_date TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(pack_hash, action_id),
                    FOREIGN KEY(pack_hash) REFERENCES reference_data_packs(pack_hash)
                );
                CREATE TABLE IF NOT EXISTS reference_security_lifecycle (
                    pack_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY(pack_hash, event_hash),
                    FOREIGN KEY(pack_hash) REFERENCES reference_data_packs(pack_hash)
                );
                """
            )
            connection.execute(
                "INSERT OR REPLACE INTO reference_data_schema(key, value) VALUES('schema_version', ?)",
                (REFERENCE_DATA_STORE_SCHEMA_VERSION,),
            )
            connection.commit()

    def import_pack(
        self,
        payload: dict[str, Any],
        *,
        source_root: Path | str | None,
    ) -> dict[str, Any]:
        audit = verify_reference_data_pack(payload, source_root=source_root)
        if audit.get("status") != "PASS" or payload.get("status") != "PASS":
            return {
                "ok": False,
                "status": "BLOCK",
                "blockers": list(audit.get("blockers") or payload.get("blockers") or []),
                "paper_authorized": False,
                "live_order_allowed": False,
            }
        pack_hash = str(payload["pack_hash"])
        imported_at = int(self.now_ms())
        encoded = lambda item: json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        universe = dict(payload.get("universe_contract") or {})
        with self._lock, closing(self._connect()) as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT OR IGNORE INTO reference_data_packs(
                    pack_hash, package_id, status, prepared_at, imported_at, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    pack_hash,
                    str(payload.get("package_id") or ""),
                    str(payload.get("status") or ""),
                    str(payload.get("prepared_at") or ""),
                    imported_at,
                    encoded(payload),
                ),
            )
            for document in payload.get("source_documents") or []:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO reference_source_documents(
                        document_sha256, source_kind, pack_hash, source_authority,
                        source_name, evidence_ref, size_bytes, metadata_json
                    ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(document.get("actual_document_sha256") or ""),
                        str(document.get("source_kind") or ""),
                        pack_hash,
                        str(document.get("source_authority") or ""),
                        str(document.get("source_name") or ""),
                        str(document.get("evidence_ref") or ""),
                        int(document.get("size_bytes") or 0),
                        encoded(document),
                    ),
                )
            connection.execute(
                """
                INSERT OR IGNORE INTO reference_universe_contracts(
                    contract_hash, pack_hash, status, coverage_start, coverage_end, payload_json
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    str(universe.get("contract_hash") or ""),
                    pack_hash,
                    str(universe.get("status") or ""),
                    str(universe.get("coverage_start") or ""),
                    str(universe.get("coverage_end") or ""),
                    encoded(universe),
                ),
            )
            for source in payload.get("corporate_action_sources") or []:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO reference_corporate_sources(
                        source_hash, pack_hash, status, attestation_hash, payload_json
                    ) VALUES(?, ?, ?, ?, ?)
                    """,
                    (
                        str(source.get("source_hash") or ""),
                        pack_hash,
                        str(source.get("status") or ""),
                        str((source.get("attestation") or {}).get("attestation_hash") or ""),
                        encoded(source),
                    ),
                )
            for records in (payload.get("corporate_actions_by_symbol") or {}).values():
                for record in records or []:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO reference_corporate_actions(
                            pack_hash, action_id, symbol, event_date, payload_json
                        ) VALUES(?, ?, ?, ?, ?)
                        """,
                        (
                            pack_hash,
                            str(record.get("action_id") or ""),
                            str(record.get("symbol") or ""),
                            str(record.get("event_date") or ""),
                            encoded(record),
                        ),
                    )
            for records in (payload.get("security_lifecycle_by_symbol") or {}).values():
                for record in records or []:
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO reference_security_lifecycle(
                            pack_hash, event_hash, symbol, start_date, payload_json
                        ) VALUES(?, ?, ?, ?, ?)
                        """,
                        (
                            pack_hash,
                            str(record.get("event_hash") or ""),
                            str(record.get("symbol") or ""),
                            str(record.get("start_date") or ""),
                            encoded(record),
                        ),
                    )
            connection.commit()
        return {
            "ok": True,
            "status": "IMPORTED",
            "pack_hash": pack_hash,
            "db_path": str(self.db_path),
            "manual_source_identity_review_required": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    def summary(self) -> dict[str, Any]:
        with self._lock, closing(self._connect()) as connection:
            counts = {
                "pack_count": int(connection.execute("SELECT COUNT(*) FROM reference_data_packs").fetchone()[0]),
                "source_document_count": int(connection.execute("SELECT COUNT(*) FROM reference_source_documents").fetchone()[0]),
                "universe_contract_count": int(connection.execute("SELECT COUNT(*) FROM reference_universe_contracts").fetchone()[0]),
                "corporate_source_count": int(connection.execute("SELECT COUNT(*) FROM reference_corporate_sources").fetchone()[0]),
                "corporate_action_count": int(connection.execute("SELECT COUNT(*) FROM reference_corporate_actions").fetchone()[0]),
                "security_lifecycle_count": int(connection.execute("SELECT COUNT(*) FROM reference_security_lifecycle").fetchone()[0]),
            }
        return {
            "schema_version": REFERENCE_DATA_STORE_SCHEMA_VERSION,
            "status": "PASS",
            **counts,
            "db_path": str(self.db_path),
            "research_only": True,
            "paper_authorized": False,
            "live_order_allowed": False,
        }


def build_intake_template(
    *,
    candidate_hash: str,
    benchmark_symbol: str,
    tradable_symbols: list[str],
    coverage_start: str,
    coverage_end: str,
    prepared_at: str,
) -> dict[str, Any]:
    return {
        "schema_version": REFERENCE_DATA_IMPORT_SCHEMA_VERSION,
        "package_id": f"reference-intake-{str(candidate_hash or '')[:12] or 'unbound'}",
        "prepared_at": _clean_timestamp(prepared_at),
        "universe": {
            "benchmark_symbol": str(benchmark_symbol or "").strip().upper(),
            "tradable_symbols": _symbols(tradable_symbols),
            "selection_basis": "REPLACE_WITH_EX_ANTE_SELECTION_BASIS",
            "selection_rule_id": "REPLACE_WITH_VERSIONED_SELECTION_RULE",
            "coverage_start": _clean_date(coverage_start),
            "coverage_end": _clean_date(coverage_end),
            "sources": [],
        },
        "corporate_action_sources": [],
        "required_source_document_schemas": {
            "membership": MEMBERSHIP_SOURCE_SCHEMA_VERSION,
            "corporate_actions": CORPORATE_ACTION_SOURCE_SCHEMA_VERSION,
        },
        "required_corporate_action_types": sorted(REQUIRED_OFFICIAL_ACTION_TYPES),
        "manual_source_identity_review_required": True,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
