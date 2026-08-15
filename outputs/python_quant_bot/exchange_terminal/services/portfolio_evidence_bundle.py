from __future__ import annotations

import base64
import binascii
from copy import deepcopy
import hashlib
import json
import zlib
from typing import Any

from .market_data_revision_ledger import (
    verify_cross_source_evidence,
    verify_market_data_snapshot,
)


PORTFOLIO_EVIDENCE_BUNDLE_FIELD = "evidence_bundle"
PORTFOLIO_EVIDENCE_BUNDLE_SCHEMA_VERSION = "portfolio-evidence-bundle-v1"
MARKET_DATA_SNAPSHOT_REF_SCHEMA_VERSION = "market-data-snapshot-ref-v1"
MARKET_DATA_SNAPSHOT_CONTENT_TYPE = "market-data-snapshot"
EVIDENCE_BUNDLE_ENCODING = "zlib-level-9+base64+canonical-json-v1"
MAX_BUNDLE_ENTRIES = 4096
MAX_ENTRY_COMPRESSED_BYTES = 16 * 1024 * 1024
MAX_ENTRY_UNCOMPRESSED_BYTES = 32 * 1024 * 1024
MAX_BUNDLE_UNCOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_BUNDLE_COMPRESSED_BYTES = 128 * 1024 * 1024
SNAPSHOT_FIELDS = ("primary_snapshot", "secondary_snapshot")


class PortfolioEvidenceBundleError(ValueError):
    pass


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")


def _canonical_hash(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _native_nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_cross_source_record(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and "primary_snapshot_hash" in payload
        and "secondary_snapshot_hash" in payload
        and any(field in payload for field in SNAPSHOT_FIELDS)
    )


def _is_snapshot_ref(payload: Any) -> bool:
    return (
        isinstance(payload, dict)
        and payload.get("schema_version") == MARKET_DATA_SNAPSHOT_REF_SCHEMA_VERSION
    )


def _walk_cross_source_records(payload: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            if _is_cross_source_record(value):
                records.append(value)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return records


def _snapshot_ref(snapshot: dict[str, Any], content_hash: str) -> dict[str, Any]:
    return {
        "schema_version": MARKET_DATA_SNAPSHOT_REF_SCHEMA_VERSION,
        "content_type": MARKET_DATA_SNAPSHOT_CONTENT_TYPE,
        "content_hash": content_hash,
        "snapshot_hash": str(snapshot.get("snapshot_hash") or ""),
        "rows_hash": str(snapshot.get("rows_hash") or ""),
        "row_count": int(snapshot.get("row_count") or 0),
    }


def _snapshot_entry(snapshot: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    audit = verify_market_data_snapshot(snapshot)
    if audit.get("status") != "PASS":
        raise PortfolioEvidenceBundleError(
            "market_data_snapshot_invalid:" + ",".join(audit.get("blockers") or [])
        )
    raw = _canonical_bytes(snapshot)
    if len(raw) > MAX_ENTRY_UNCOMPRESSED_BYTES:
        raise PortfolioEvidenceBundleError("market_data_snapshot_too_large")
    content_hash = hashlib.sha256(raw).hexdigest()
    compressed = zlib.compress(raw, level=9)
    if len(compressed) > MAX_ENTRY_COMPRESSED_BYTES:
        raise PortfolioEvidenceBundleError("compressed_market_data_snapshot_too_large")
    entry = {
        "content_type": MARKET_DATA_SNAPSHOT_CONTENT_TYPE,
        "encoding": EVIDENCE_BUNDLE_ENCODING,
        "content_hash": content_hash,
        "snapshot_hash": str(snapshot.get("snapshot_hash") or ""),
        "rows_hash": str(snapshot.get("rows_hash") or ""),
        "row_count": int(snapshot.get("row_count") or 0),
        "uncompressed_size": len(raw),
        "compressed_size": len(compressed),
        "payload": base64.b64encode(compressed).decode("ascii"),
    }
    return content_hash, entry


def pack_portfolio_evidence_bundle(payload: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PortfolioEvidenceBundleError("portfolio_evidence_payload_must_be_object")
    if PORTFOLIO_EVIDENCE_BUNDLE_FIELD in payload:
        _expanded, audit = expand_portfolio_evidence_bundle(payload, require_bundle=True)
        if audit.get("status") != "PASS":
            raise PortfolioEvidenceBundleError(
                "existing_portfolio_evidence_bundle_invalid:"
                + ",".join(audit.get("blockers") or [])
            )
        return deepcopy(payload)

    compact = deepcopy(payload)
    records = _walk_cross_source_records(compact)
    entries: dict[str, dict[str, Any]] = {}
    generated_ref_ids: set[int] = set()
    reference_count = 0
    for record in records:
        for field in SNAPSHOT_FIELDS:
            snapshot = record.get(field)
            if not isinstance(snapshot, dict):
                raise PortfolioEvidenceBundleError(f"cross_source_{field}_must_be_embedded_snapshot")
            if _is_snapshot_ref(snapshot):
                if id(snapshot) not in generated_ref_ids:
                    raise PortfolioEvidenceBundleError(f"cross_source_{field}_must_be_embedded_snapshot")
                reference_count += 1
                continue
            content_hash, entry = _snapshot_entry(snapshot)
            existing = entries.get(content_hash)
            if existing is not None and existing != entry:
                raise PortfolioEvidenceBundleError("portfolio_evidence_content_hash_collision")
            entries[content_hash] = entry
            snapshot_ref = _snapshot_ref(snapshot, content_hash)
            record[field] = snapshot_ref
            generated_ref_ids.add(id(snapshot_ref))
            reference_count += 1

    if not entries:
        return compact
    if len(entries) > MAX_BUNDLE_ENTRIES:
        raise PortfolioEvidenceBundleError("portfolio_evidence_bundle_entry_limit_exceeded")
    total_uncompressed = sum(int(entry["uncompressed_size"]) for entry in entries.values())
    total_compressed = sum(int(entry["compressed_size"]) for entry in entries.values())
    if total_uncompressed > MAX_BUNDLE_UNCOMPRESSED_BYTES:
        raise PortfolioEvidenceBundleError("portfolio_evidence_bundle_uncompressed_limit_exceeded")
    ordered_entries = {key: entries[key] for key in sorted(entries)}
    bundle = {
        "schema_version": PORTFOLIO_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "encoding": EVIDENCE_BUNDLE_ENCODING,
        "entry_count": len(ordered_entries),
        "reference_count": reference_count,
        "total_uncompressed_bytes": total_uncompressed,
        "total_compressed_bytes": total_compressed,
        "entries": ordered_entries,
        "entries_hash": _canonical_hash(ordered_entries),
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    bundle["bundle_hash"] = _canonical_hash(bundle)
    compact[PORTFOLIO_EVIDENCE_BUNDLE_FIELD] = bundle
    return compact


def _decode_entry(content_hash: str, entry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    blockers: list[str] = []
    expected_fields = {
        "content_type",
        "encoding",
        "content_hash",
        "snapshot_hash",
        "rows_hash",
        "row_count",
        "uncompressed_size",
        "compressed_size",
        "payload",
    }
    if set(entry) != expected_fields:
        blockers.append(f"evidence_bundle_entry_fields_invalid:{content_hash}")
    if entry.get("content_type") != MARKET_DATA_SNAPSHOT_CONTENT_TYPE:
        blockers.append(f"evidence_bundle_entry_content_type_invalid:{content_hash}")
    if entry.get("encoding") != EVIDENCE_BUNDLE_ENCODING:
        blockers.append(f"evidence_bundle_entry_encoding_invalid:{content_hash}")
    if not _valid_sha256(content_hash) or entry.get("content_hash") != content_hash:
        blockers.append(f"evidence_bundle_entry_content_hash_invalid:{content_hash}")
    for field in ("snapshot_hash", "rows_hash"):
        if not _valid_sha256(entry.get(field)):
            blockers.append(f"evidence_bundle_entry_{field}_invalid:{content_hash}")
    for field in ("row_count", "uncompressed_size", "compressed_size"):
        if not _native_nonnegative_int(entry.get(field)):
            blockers.append(f"evidence_bundle_entry_{field}_invalid:{content_hash}")
    uncompressed_size = int(entry.get("uncompressed_size") or 0)
    compressed_size = int(entry.get("compressed_size") or 0)
    if uncompressed_size <= 0 or uncompressed_size > MAX_ENTRY_UNCOMPRESSED_BYTES:
        blockers.append(f"evidence_bundle_entry_uncompressed_limit_invalid:{content_hash}")
    if compressed_size <= 0 or compressed_size > MAX_ENTRY_COMPRESSED_BYTES:
        blockers.append(f"evidence_bundle_entry_compressed_limit_invalid:{content_hash}")
    encoded = entry.get("payload")
    if not isinstance(encoded, str):
        blockers.append(f"evidence_bundle_entry_payload_invalid:{content_hash}")
        return {}, blockers
    maximum_encoded_size = ((MAX_ENTRY_COMPRESSED_BYTES + 2) // 3) * 4
    if len(encoded) > maximum_encoded_size:
        blockers.append(f"evidence_bundle_entry_base64_limit:{content_hash}")
        return {}, blockers
    try:
        compressed = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (UnicodeEncodeError, binascii.Error, ValueError):
        blockers.append(f"evidence_bundle_entry_base64_invalid:{content_hash}")
        return {}, blockers
    if len(compressed) != compressed_size:
        blockers.append(f"evidence_bundle_entry_compressed_size_mismatch:{content_hash}")
        return {}, blockers
    try:
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(compressed, min(uncompressed_size, MAX_ENTRY_UNCOMPRESSED_BYTES) + 1)
        if decompressor.unconsumed_tail or not decompressor.eof:
            blockers.append(f"evidence_bundle_entry_decompression_limit:{content_hash}")
            return {}, blockers
        raw += decompressor.flush()
    except zlib.error:
        blockers.append(f"evidence_bundle_entry_zlib_invalid:{content_hash}")
        return {}, blockers
    if decompressor.unused_data:
        blockers.append(f"evidence_bundle_entry_trailing_data:{content_hash}")
    if len(raw) > MAX_ENTRY_UNCOMPRESSED_BYTES or len(raw) != uncompressed_size:
        blockers.append(f"evidence_bundle_entry_uncompressed_size_mismatch:{content_hash}")
        return {}, blockers
    if hashlib.sha256(raw).hexdigest() != content_hash:
        blockers.append(f"evidence_bundle_entry_digest_mismatch:{content_hash}")
        return {}, blockers
    try:
        snapshot = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        blockers.append(f"evidence_bundle_entry_json_invalid:{content_hash}")
        return {}, blockers
    if not isinstance(snapshot, dict) or _canonical_bytes(snapshot) != raw:
        blockers.append(f"evidence_bundle_entry_canonical_json_invalid:{content_hash}")
        return {}, blockers
    snapshot_audit = verify_market_data_snapshot(snapshot)
    blockers.extend(
        f"evidence_bundle_entry_snapshot:{content_hash}:{reason}"
        for reason in snapshot_audit.get("blockers") or []
    )
    if str(snapshot.get("snapshot_hash") or "") != str(entry.get("snapshot_hash") or ""):
        blockers.append(f"evidence_bundle_entry_snapshot_hash_mismatch:{content_hash}")
    if str(snapshot.get("rows_hash") or "") != str(entry.get("rows_hash") or ""):
        blockers.append(f"evidence_bundle_entry_rows_hash_mismatch:{content_hash}")
    if int(snapshot.get("row_count") or 0) != int(entry.get("row_count") or 0):
        blockers.append(f"evidence_bundle_entry_row_count_mismatch:{content_hash}")
    return snapshot, blockers


def expand_portfolio_evidence_bundle(
    payload: dict[str, Any],
    *,
    require_bundle: bool = False,
) -> tuple[dict[str, Any], dict[str, Any]]:
    compact = (
        json.loads(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        if isinstance(payload, dict)
        else {}
    )
    bundle = compact.pop(PORTFOLIO_EVIDENCE_BUNDLE_FIELD, None)
    records = _walk_cross_source_records(compact)
    ref_count = sum(
        1
        for record in records
        for field in SNAPSHOT_FIELDS
        if _is_snapshot_ref(record.get(field))
    )
    if bundle is None:
        blockers = []
        if require_bundle:
            blockers.append("portfolio_evidence_bundle_missing")
        if ref_count:
            blockers.append("portfolio_evidence_bundle_missing_for_refs")
        return compact, {
            "schema_version": PORTFOLIO_EVIDENCE_BUNDLE_SCHEMA_VERSION,
            "status": "PASS" if not blockers else "BLOCK",
            "mode": "LEGACY_EMBEDDED" if not blockers else "INVALID",
            "blockers": blockers,
            "entry_count": 0,
            "reference_count": ref_count,
            "bundle_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }

    blockers: list[str] = []
    if not isinstance(bundle, dict):
        blockers.append("portfolio_evidence_bundle_invalid")
        bundle = {}
    expected_bundle_fields = {
        "schema_version",
        "encoding",
        "entry_count",
        "reference_count",
        "total_uncompressed_bytes",
        "total_compressed_bytes",
        "entries",
        "entries_hash",
        "research_only",
        "paper_authorized",
        "live_order_allowed",
        "bundle_hash",
    }
    if set(bundle) != expected_bundle_fields:
        blockers.append("portfolio_evidence_bundle_fields_invalid")
    if bundle.get("schema_version") != PORTFOLIO_EVIDENCE_BUNDLE_SCHEMA_VERSION:
        blockers.append("portfolio_evidence_bundle_schema_invalid")
    if bundle.get("encoding") != EVIDENCE_BUNDLE_ENCODING:
        blockers.append("portfolio_evidence_bundle_encoding_invalid")
    for field in (
        "entry_count",
        "reference_count",
        "total_uncompressed_bytes",
        "total_compressed_bytes",
    ):
        if not _native_nonnegative_int(bundle.get(field)):
            blockers.append(f"portfolio_evidence_bundle_{field}_invalid")
    entries = bundle.get("entries") if isinstance(bundle.get("entries"), dict) else {}
    if not isinstance(bundle.get("entries"), dict):
        blockers.append("portfolio_evidence_bundle_entries_invalid")
    if len(entries) > MAX_BUNDLE_ENTRIES:
        blockers.append("portfolio_evidence_bundle_entry_limit_exceeded")
    if bundle.get("entry_count") != len(entries):
        blockers.append("portfolio_evidence_bundle_entry_count_mismatch")
    if bundle.get("reference_count") != ref_count:
        blockers.append("portfolio_evidence_bundle_reference_count_mismatch")
    if str(bundle.get("entries_hash") or "") != _canonical_hash(entries):
        blockers.append("portfolio_evidence_bundle_entries_hash_invalid")
    declared_hash = str(bundle.get("bundle_hash") or "")
    bundle_content = dict(bundle)
    bundle_content.pop("bundle_hash", None)
    if not _valid_sha256(declared_hash) or _canonical_hash(bundle_content) != declared_hash:
        blockers.append("portfolio_evidence_bundle_hash_invalid")
    if (
        bundle.get("research_only") is not True
        or bundle.get("paper_authorized") is not False
        or bundle.get("live_order_allowed") is not False
    ):
        blockers.append("portfolio_evidence_bundle_has_execution_authority")

    decoded: dict[str, dict[str, Any]] = {}
    total_uncompressed = 0
    total_compressed = 0
    for content_hash, raw_entry in entries.items():
        entry = dict(raw_entry) if isinstance(raw_entry, dict) else {}
        if not isinstance(raw_entry, dict):
            blockers.append(f"evidence_bundle_entry_invalid:{content_hash}")
        entry_uncompressed = (
            int(entry["uncompressed_size"])
            if _native_nonnegative_int(entry.get("uncompressed_size"))
            else 0
        )
        entry_compressed = (
            int(entry["compressed_size"])
            if _native_nonnegative_int(entry.get("compressed_size"))
            else 0
        )
        if (
            total_uncompressed + entry_uncompressed > MAX_BUNDLE_UNCOMPRESSED_BYTES
            or total_compressed + entry_compressed > MAX_BUNDLE_COMPRESSED_BYTES
        ):
            blockers.append("portfolio_evidence_bundle_total_limit_exceeded")
            continue
        snapshot, entry_blockers = _decode_entry(str(content_hash), entry)
        blockers.extend(entry_blockers)
        if snapshot:
            decoded[str(content_hash)] = snapshot
        if _native_nonnegative_int(entry.get("uncompressed_size")):
            total_uncompressed += int(entry["uncompressed_size"])
        if _native_nonnegative_int(entry.get("compressed_size")):
            total_compressed += int(entry["compressed_size"])
    if total_uncompressed > MAX_BUNDLE_UNCOMPRESSED_BYTES:
        blockers.append("portfolio_evidence_bundle_uncompressed_limit_exceeded")
    if total_compressed > MAX_BUNDLE_COMPRESSED_BYTES:
        blockers.append("portfolio_evidence_bundle_compressed_limit_exceeded")
    if bundle.get("total_uncompressed_bytes") != total_uncompressed:
        blockers.append("portfolio_evidence_bundle_uncompressed_total_mismatch")
    if bundle.get("total_compressed_bytes") != total_compressed:
        blockers.append("portfolio_evidence_bundle_compressed_total_mismatch")

    referenced_hashes: set[str] = set()
    for record_index, record in enumerate(records):
        for field in SNAPSHOT_FIELDS:
            ref = record.get(field)
            if not _is_snapshot_ref(ref):
                blockers.append(f"portfolio_evidence_snapshot_ref_missing:{record_index}:{field}")
                continue
            expected_ref_fields = {
                "schema_version",
                "content_type",
                "content_hash",
                "snapshot_hash",
                "rows_hash",
                "row_count",
            }
            if set(ref) != expected_ref_fields:
                blockers.append(f"portfolio_evidence_snapshot_ref_fields_invalid:{record_index}:{field}")
            content_hash = str(ref.get("content_hash") or "")
            referenced_hashes.add(content_hash)
            snapshot = decoded.get(content_hash)
            if snapshot is None:
                blockers.append(f"portfolio_evidence_snapshot_ref_unresolved:{record_index}:{field}")
                continue
            for key in ("snapshot_hash", "rows_hash", "row_count"):
                if ref.get(key) != snapshot.get(key):
                    blockers.append(f"portfolio_evidence_snapshot_ref_{key}_mismatch:{record_index}:{field}")
            if ref.get("content_type") != MARKET_DATA_SNAPSHOT_CONTENT_TYPE:
                blockers.append(f"portfolio_evidence_snapshot_ref_content_type_invalid:{record_index}:{field}")
            record[field] = deepcopy(snapshot)
    if referenced_hashes != set(entries):
        blockers.append("portfolio_evidence_bundle_reference_inventory_mismatch")
    if not blockers:
        for index, record in enumerate(records):
            audit = verify_cross_source_evidence(record)
            blockers.extend(
                f"portfolio_evidence_cross_source:{index}:{reason}"
                for reason in audit.get("blockers") or []
            )
    return compact, {
        "schema_version": PORTFOLIO_EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "status": "PASS" if not blockers else "BLOCK",
        "mode": "CONTENT_ADDRESSED_BUNDLE",
        "blockers": list(dict.fromkeys(blockers)),
        "entry_count": len(entries),
        "reference_count": ref_count,
        "bundle_hash": declared_hash,
        "compression_ratio": round(
            total_compressed / total_uncompressed,
            8,
        ) if total_uncompressed else 0.0,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def verify_portfolio_evidence_bundle(
    payload: dict[str, Any],
    *,
    require_bundle: bool = False,
) -> dict[str, Any]:
    _expanded, audit = expand_portfolio_evidence_bundle(
        payload,
        require_bundle=require_bundle,
    )
    return audit
