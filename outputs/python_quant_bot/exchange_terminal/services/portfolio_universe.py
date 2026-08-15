from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any
from urllib.parse import urlparse


PORTFOLIO_UNIVERSE_CONTRACT_VERSION = "portfolio-research-universe-v4"
POINT_IN_TIME_MEMBERSHIP_EVIDENCE_VERSION = "point-in-time-membership-evidence-v1"
POINT_IN_TIME_SOURCE_AUTHORITIES = {
    "EXCHANGE_LISTING_HISTORY",
    "OFFICIAL_INDEX_PROVIDER",
    "LICENSED_POINT_IN_TIME_VENDOR",
}


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _clean_date(value: Any) -> str:
    clean = str(value or "").strip()[:10]
    if not clean:
        return ""
    try:
        return date.fromisoformat(clean).isoformat()
    except ValueError:
        return ""


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


def _valid_sha256(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(character in "0123456789abcdef" for character in text)


def _valid_evidence_ref(value: Any) -> bool:
    text = str(value or "").strip()
    if text.startswith("urn:"):
        return len(text) > 4
    parsed = urlparse(text)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _normalize_symbols(symbols: list[str], benchmark: str) -> list[str]:
    return list(dict.fromkeys(
        str(symbol or "").strip().upper()
        for symbol in symbols
        if str(symbol or "").strip() and str(symbol or "").strip().upper() != benchmark
    ))


def build_membership_source_evidence(
    *,
    symbol: str,
    effective_from: str,
    effective_to: str,
    source_authority: str,
    source_name: str,
    evidence_ref: str,
    source_document_sha256: str,
    evidence_published_at: str,
    retrieved_at: str,
) -> dict[str, Any]:
    payload = {
        "schema_version": POINT_IN_TIME_MEMBERSHIP_EVIDENCE_VERSION,
        "source_authority": str(source_authority or "").strip().upper(),
        "source_name": str(source_name or "").strip(),
        "evidence_ref": str(evidence_ref or "").strip(),
        "source_document_sha256": str(source_document_sha256 or "").strip().lower(),
        "evidence_published_at": _clean_timestamp(evidence_published_at),
        "retrieved_at": _clean_timestamp(retrieved_at),
        "membership_claim": {
            "symbol": str(symbol or "").strip().upper(),
            "effective_from": _clean_date(effective_from),
            "effective_to": _clean_date(effective_to),
        },
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["evidence_sha256"] = _canonical_hash(payload)
    return payload


def _membership_source_evidence_blockers(item: dict[str, Any], *, declared_at: str) -> list[str]:
    symbol = str(item.get("symbol") or "")
    effective_from = str(item.get("effective_from") or "")
    evidence = dict(item.get("evidence_payload") or {}) if isinstance(item.get("evidence_payload"), dict) else {}
    blockers: list[str] = []
    if not evidence:
        return [f"membership_evidence_payload_missing:{symbol}:{effective_from or '--'}"]
    supplied_hash = str(evidence.get("evidence_sha256") or "").strip().lower()
    hash_payload = dict(evidence)
    hash_payload.pop("evidence_sha256", None)
    if not _valid_sha256(supplied_hash) or supplied_hash != _canonical_hash(hash_payload):
        blockers.append(f"membership_evidence_payload_hash_invalid:{symbol}:{effective_from or '--'}")
    if str(item.get("evidence_sha256") or "") != supplied_hash:
        blockers.append(f"membership_evidence_hash_binding_invalid:{symbol}:{effective_from or '--'}")
    if str(evidence.get("schema_version") or "") != POINT_IN_TIME_MEMBERSHIP_EVIDENCE_VERSION:
        blockers.append(f"membership_evidence_payload_schema_invalid:{symbol}:{effective_from or '--'}")
    expected_claim = {
        "symbol": symbol,
        "effective_from": effective_from,
        "effective_to": str(item.get("effective_to") or ""),
    }
    if evidence.get("membership_claim") != expected_claim:
        blockers.append(f"membership_evidence_claim_mismatch:{symbol}:{effective_from or '--'}")
    for field in ("source_authority", "source_name", "evidence_ref", "evidence_published_at"):
        if evidence.get(field) != item.get(field):
            blockers.append(f"membership_evidence_source_mismatch:{symbol}:{field}")
    if not _valid_sha256(evidence.get("source_document_sha256")):
        blockers.append(f"membership_source_document_hash_invalid:{symbol}:{effective_from or '--'}")
    retrieved_at = _clean_timestamp(evidence.get("retrieved_at"))
    published_at = _clean_timestamp(evidence.get("evidence_published_at"))
    if not retrieved_at:
        blockers.append(f"membership_evidence_retrieved_at_invalid:{symbol}:{effective_from or '--'}")
    elif published_at and retrieved_at < published_at:
        blockers.append(f"membership_evidence_retrieved_before_publication:{symbol}:{effective_from or '--'}")
    if declared_at and retrieved_at and retrieved_at > declared_at:
        blockers.append(f"membership_evidence_retrieved_after_declaration:{symbol}:{effective_from or '--'}")
    if (
        evidence.get("research_only") is not True
        or evidence.get("paper_authorized") is not False
        or evidence.get("live_order_allowed") is not False
    ):
        blockers.append(f"membership_evidence_has_execution_authority:{symbol}:{effective_from or '--'}")
    return blockers


def normalize_membership_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in records or []:
        if not isinstance(raw, dict):
            continue
        item = {
            "symbol": str(raw.get("symbol") or "").strip().upper(),
            "effective_from": _clean_date(raw.get("effective_from")),
            "effective_to": _clean_date(raw.get("effective_to")),
            "source_authority": str(raw.get("source_authority") or "").strip().upper(),
            "source_name": str(raw.get("source_name") or "").strip(),
            "evidence_ref": str(raw.get("evidence_ref") or "").strip(),
            "evidence_sha256": str(raw.get("evidence_sha256") or "").strip().lower(),
            "evidence_published_at": _clean_timestamp(raw.get("evidence_published_at")),
            "evidence_payload": (
                dict(raw.get("evidence_payload") or {})
                if isinstance(raw.get("evidence_payload"), dict)
                else {}
            ),
        }
        item["membership_id"] = _canonical_hash(item)
        if item["membership_id"] in seen:
            continue
        seen.add(item["membership_id"])
        normalized.append(item)
    return sorted(normalized, key=lambda item: (item["symbol"], item["effective_from"], item["effective_to"]))


def build_static_research_universe_contract(
    *,
    benchmark_symbol: str,
    tradable_symbols: list[str],
    declared_at: str,
    selection_basis: str,
) -> dict[str, Any]:
    benchmark = str(benchmark_symbol or "").strip().upper()
    tradables = _normalize_symbols(tradable_symbols, benchmark)
    declaration = _clean_timestamp(declared_at)
    basis = str(selection_basis or "").strip()
    blockers: list[str] = []
    if not benchmark:
        blockers.append("benchmark_symbol_missing")
    if not tradables:
        blockers.append("tradable_symbols_missing")
    if not declaration:
        blockers.append("universe_declaration_timestamp_invalid")
    if not basis:
        blockers.append("universe_selection_basis_missing")
    payload = {
        "schema_version": PORTFOLIO_UNIVERSE_CONTRACT_VERSION,
        "status": "STATIC_RESEARCH_UNIVERSE" if not blockers else "BLOCK",
        "blockers": blockers,
        "declared_at": declaration,
        "benchmark_symbol": benchmark,
        "tradable_symbols": tradables,
        "selection_basis": basis,
        "selection_rule_id": "",
        "membership_policy": "CURRENT_KNOWLEDGE_STATIC_LIST",
        "membership_records": [],
        "membership_hash": _canonical_hash([]),
        "coverage_start": "",
        "coverage_end": "",
        "historical_membership_verified": False,
        "point_in_time_constituents": False,
        "survivorship_bias_status": "UNCONTROLLED",
        "historical_universe_claim_allowed": False,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["contract_hash"] = _canonical_hash(payload)
    return payload


def build_point_in_time_universe_contract(
    *,
    benchmark_symbol: str,
    tradable_symbols: list[str],
    declared_at: str,
    selection_basis: str,
    selection_rule_id: str,
    coverage_start: str,
    coverage_end: str,
    membership_records: list[dict[str, Any]],
) -> dict[str, Any]:
    benchmark = str(benchmark_symbol or "").strip().upper()
    tradables = _normalize_symbols(tradable_symbols, benchmark)
    records = normalize_membership_records(membership_records)
    declaration = _clean_timestamp(declared_at)
    basis = str(selection_basis or "").strip()
    rule_id = str(selection_rule_id or "").strip()
    start = _clean_date(coverage_start)
    end = _clean_date(coverage_end)
    blockers: list[str] = []
    if not benchmark:
        blockers.append("benchmark_symbol_missing")
    if not tradables:
        blockers.append("tradable_symbols_missing")
    if not declaration:
        blockers.append("universe_declaration_timestamp_invalid")
    if not basis:
        blockers.append("universe_selection_basis_missing")
    if not rule_id:
        blockers.append("point_in_time_selection_rule_missing")
    if not start or not end or start > end:
        blockers.append("point_in_time_coverage_invalid")
    if not records:
        blockers.append("point_in_time_membership_records_missing")

    allowed = set(tradables)
    records_by_symbol: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in tradables}
    for item in records:
        symbol = str(item.get("symbol") or "")
        effective_from = str(item.get("effective_from") or "")
        effective_to = str(item.get("effective_to") or "")
        if symbol not in allowed:
            blockers.append(f"membership_symbol_outside_declared_universe:{symbol or '--'}")
            continue
        records_by_symbol[symbol].append(item)
        if not effective_from:
            blockers.append(f"membership_effective_from_invalid:{symbol}")
        if effective_to and effective_from and effective_to < effective_from:
            blockers.append(f"membership_interval_invalid:{symbol}:{effective_from}:{effective_to}")
        if str(item.get("source_authority") or "") not in POINT_IN_TIME_SOURCE_AUTHORITIES:
            blockers.append(f"membership_source_not_authoritative:{symbol}:{item.get('source_authority') or '--'}")
        if not str(item.get("source_name") or "") or not _valid_evidence_ref(item.get("evidence_ref")):
            blockers.append(f"membership_evidence_missing:{symbol}:{effective_from or '--'}")
        if not _valid_sha256(item.get("evidence_sha256")):
            blockers.append(f"membership_evidence_hash_invalid:{symbol}:{effective_from or '--'}")
        published_at = _clean_timestamp(item.get("evidence_published_at"))
        if not published_at:
            blockers.append(f"membership_evidence_publication_time_missing:{symbol}:{effective_from or '--'}")
        elif effective_from and published_at[:10] > effective_from:
            blockers.append(f"membership_evidence_available_after_effective_date:{symbol}:{effective_from}")
        blockers.extend(_membership_source_evidence_blockers(item, declared_at=declaration))

    for symbol, symbol_records in records_by_symbol.items():
        if not symbol_records:
            blockers.append(f"membership_history_missing:{symbol}")
            continue
        previous_end = ""
        for index, item in enumerate(symbol_records):
            effective_from = str(item.get("effective_from") or "")
            if index > 0 and (not previous_end or (effective_from and effective_from <= previous_end)):
                blockers.append(f"membership_intervals_overlap:{symbol}:{effective_from or '--'}")
            previous_end = str(item.get("effective_to") or "")

    def eligible_on(session_date: str) -> list[str]:
        return sorted(
            symbol
            for symbol, symbol_records in records_by_symbol.items()
            if any(
                str(item.get("effective_from") or "") <= session_date
                and (not str(item.get("effective_to") or "") or session_date <= str(item.get("effective_to") or ""))
                for item in symbol_records
                if str(item.get("effective_from") or "")
            )
        )

    if start and not eligible_on(start):
        blockers.append("point_in_time_universe_empty_at_coverage_start")
    if end and not eligible_on(end):
        blockers.append("point_in_time_universe_empty_at_coverage_end")
    blockers = list(dict.fromkeys(blockers))
    verified = not blockers
    payload = {
        "schema_version": PORTFOLIO_UNIVERSE_CONTRACT_VERSION,
        "status": "POINT_IN_TIME_VERIFIED" if verified else "BLOCK",
        "blockers": blockers,
        "declared_at": declaration,
        "benchmark_symbol": benchmark,
        "tradable_symbols": tradables,
        "selection_basis": basis,
        "selection_rule_id": rule_id,
        "membership_policy": "POINT_IN_TIME_MEMBERSHIP",
        "membership_records": records,
        "membership_hash": _canonical_hash(records),
        "coverage_start": start,
        "coverage_end": end,
        "historical_membership_verified": verified,
        "point_in_time_constituents": verified,
        "survivorship_bias_status": "CONTROLLED_BY_POINT_IN_TIME_MEMBERSHIP" if verified else "UNCONTROLLED",
        "historical_universe_claim_allowed": verified,
        "research_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["contract_hash"] = _canonical_hash(payload)
    return payload


def derive_universe_subset_contract(
    parent_contract: dict[str, Any],
    *,
    tradable_symbols: list[str],
    derivation_purpose: str,
) -> dict[str, Any]:
    """Create an integrity-bound research subset without adding new symbols."""
    parent = dict(parent_contract or {})
    benchmark = str(parent.get("benchmark_symbol") or "").strip().upper()
    parent_symbols = _normalize_symbols(list(parent.get("tradable_symbols") or []), benchmark)
    requested = _normalize_symbols(tradable_symbols, benchmark)
    parent_audit = verify_universe_contract(parent)
    blockers = [f"parent_{item}" for item in parent_audit.get("blockers") or []]
    outside = sorted(set(requested) - set(parent_symbols))
    if outside:
        blockers.append(f"subset_symbols_outside_parent:{','.join(outside)}")
    if not requested:
        blockers.append("subset_tradable_symbols_missing")
    if not str(derivation_purpose or "").strip():
        blockers.append("subset_derivation_purpose_missing")

    allowed = set(requested) & set(parent_symbols)
    subset_symbols = [symbol for symbol in parent_symbols if symbol in allowed]
    if parent.get("historical_membership_verified") is True:
        child = build_point_in_time_universe_contract(
            benchmark_symbol=benchmark,
            tradable_symbols=subset_symbols,
            declared_at=str(parent.get("declared_at") or ""),
            selection_basis=str(parent.get("selection_basis") or ""),
            selection_rule_id=str(parent.get("selection_rule_id") or ""),
            coverage_start=str(parent.get("coverage_start") or ""),
            coverage_end=str(parent.get("coverage_end") or ""),
            membership_records=[
                dict(item)
                for item in parent.get("membership_records") or []
                if str(item.get("symbol") or "").strip().upper() in allowed
            ],
        )
    else:
        child = build_static_research_universe_contract(
            benchmark_symbol=benchmark,
            tradable_symbols=subset_symbols,
            declared_at=str(parent.get("declared_at") or ""),
            selection_basis=str(parent.get("selection_basis") or "STATIC_USER_WATCHLIST"),
        )

    child["derivation_policy"] = "VERIFIED_PARENT_SUBSET_ONLY"
    child["derivation_purpose"] = str(derivation_purpose or "").strip()
    child["parent_contract_hash"] = str(parent.get("contract_hash") or "")
    child["parent_tradable_symbols"] = parent_symbols
    child["removed_symbols"] = sorted(set(parent_symbols) - set(subset_symbols))
    combined_blockers = list(dict.fromkeys([*(child.get("blockers") or []), *blockers]))
    if combined_blockers:
        child["status"] = "BLOCK"
        child["blockers"] = combined_blockers
        child["historical_membership_verified"] = False
        child["point_in_time_constituents"] = False
        child["survivorship_bias_status"] = "UNCONTROLLED"
        child["historical_universe_claim_allowed"] = False
    child.pop("contract_hash", None)
    child["contract_hash"] = _canonical_hash(child)
    return child


def _rebuild_universe_semantics(contract: dict[str, Any]) -> dict[str, Any]:
    policy = str(contract.get("membership_policy") or "")
    tradable_symbols = contract.get("tradable_symbols")
    membership_records = contract.get("membership_records")
    common = {
        "benchmark_symbol": str(contract.get("benchmark_symbol") or ""),
        "tradable_symbols": list(tradable_symbols) if isinstance(tradable_symbols, list) else [],
        "declared_at": str(contract.get("declared_at") or ""),
        "selection_basis": str(contract.get("selection_basis") or ""),
    }
    if policy == "POINT_IN_TIME_MEMBERSHIP":
        return build_point_in_time_universe_contract(
            **common,
            selection_rule_id=str(contract.get("selection_rule_id") or ""),
            coverage_start=str(contract.get("coverage_start") or ""),
            coverage_end=str(contract.get("coverage_end") or ""),
            membership_records=list(membership_records) if isinstance(membership_records, list) else [],
        )
    if policy == "CURRENT_KNOWLEDGE_STATIC_LIST":
        return build_static_research_universe_contract(**common)
    return {}


def verify_universe_contract(contract: dict[str, Any]) -> dict[str, Any]:
    contract = dict(contract) if isinstance(contract, dict) else {}
    payload = dict(contract)
    expected_hash = str(payload.pop("contract_hash", "") or "")
    blockers: list[str] = []
    declared_value = contract.get("blockers")
    declared_blockers = [str(item) for item in declared_value or [] if str(item)] if isinstance(declared_value, list) else []
    if not isinstance(declared_value, list):
        blockers.append("universe_declared_blockers_type_invalid")
    if str(contract.get("schema_version") or "") != PORTFOLIO_UNIVERSE_CONTRACT_VERSION:
        blockers.append("universe_contract_schema_invalid")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("universe_contract_hash_mismatch")
    tradable_value = contract.get("tradable_symbols")
    membership_value = contract.get("membership_records")
    if not isinstance(tradable_value, list):
        blockers.append("universe_tradable_symbols_type_invalid")
    if not isinstance(membership_value, list):
        blockers.append("universe_membership_records_type_invalid")
    membership_records = list(membership_value) if isinstance(membership_value, list) else []
    if str(contract.get("membership_hash") or "") != _canonical_hash(membership_records):
        blockers.append("universe_membership_hash_mismatch")
    if membership_records != normalize_membership_records(membership_records):
        blockers.append("universe_membership_records_not_normalized")
    if not isinstance(contract.get("historical_membership_verified"), bool):
        blockers.append("universe_historical_membership_flag_invalid")
    if not isinstance(contract.get("point_in_time_constituents"), bool):
        blockers.append("universe_point_in_time_flag_invalid")
    historical = contract.get("historical_membership_verified") is True
    point_in_time = contract.get("point_in_time_constituents") is True
    policy = str(contract.get("membership_policy") or "")
    semantic = _rebuild_universe_semantics(contract)
    if not semantic:
        blockers.append("universe_membership_policy_invalid")
    else:
        semantic_fields = (
            "benchmark_symbol",
            "tradable_symbols",
            "declared_at",
            "selection_basis",
            "selection_rule_id",
            "membership_policy",
            "membership_records",
            "membership_hash",
            "coverage_start",
            "coverage_end",
        )
        for field in semantic_fields:
            if contract.get(field) != semantic.get(field):
                blockers.append(f"universe_semantic_field_mismatch:{field}")
        semantic_blockers = [str(item) for item in semantic.get("blockers") or [] if str(item)]
        blockers.extend(f"universe_semantic_validation_failed:{item}" for item in semantic_blockers)
        derived = bool(str(contract.get("derivation_policy") or ""))
        if not derived or str(contract.get("status") or "") != "BLOCK":
            for field in (
                "status",
                "historical_membership_verified",
                "point_in_time_constituents",
                "survivorship_bias_status",
                "historical_universe_claim_allowed",
            ):
                if contract.get(field) != semantic.get(field):
                    blockers.append(f"universe_semantic_field_mismatch:{field}")
    if historical:
        if str(contract.get("status") or "") != "POINT_IN_TIME_VERIFIED" or not point_in_time:
            blockers.append("verified_universe_status_invalid")
        if policy != "POINT_IN_TIME_MEMBERSHIP" or not membership_records:
            blockers.append("verified_universe_membership_missing")
    elif str(contract.get("status") or "") not in {"STATIC_RESEARCH_UNIVERSE", "BLOCK"}:
        blockers.append("unverified_universe_status_invalid")
    if str(contract.get("status") or "") == "BLOCK":
        if declared_blockers:
            blockers.extend(f"universe_declared_blocker:{item}" for item in declared_blockers)
        else:
            blockers.append("universe_contract_declared_block")
    elif declared_blockers:
        blockers.extend(f"universe_declared_blocker:{item}" for item in declared_blockers)
    if str(contract.get("derivation_policy") or ""):
        benchmark = str(contract.get("benchmark_symbol") or "").strip().upper()
        parent_value = contract.get("parent_tradable_symbols")
        parent_symbols = _normalize_symbols(list(parent_value), benchmark) if isinstance(parent_value, list) else []
        child_symbols = _normalize_symbols(list(tradable_value), benchmark) if isinstance(tradable_value, list) else []
        if str(contract.get("derivation_policy") or "") != "VERIFIED_PARENT_SUBSET_ONLY":
            blockers.append("universe_derivation_policy_invalid")
        if not _valid_sha256(contract.get("parent_contract_hash")):
            blockers.append("universe_parent_contract_hash_missing")
        if not str(contract.get("derivation_purpose") or "").strip():
            blockers.append("universe_derivation_purpose_missing")
        if not set(child_symbols).issubset(set(parent_symbols)):
            blockers.append("universe_derived_symbols_outside_parent")
        expected_removed = sorted(set(parent_symbols) - set(child_symbols))
        removed_value = contract.get("removed_symbols")
        if not isinstance(removed_value, list) or sorted(removed_value) != expected_removed:
            blockers.append("universe_removed_symbols_mismatch")
    if (
        contract.get("research_only") is not True
        or contract.get("paper_authorized") is not False
        or contract.get("live_order_allowed") is not False
    ):
        blockers.append("universe_contract_has_execution_authority")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "contract_hash": expected_hash,
        "historical_membership_verified": historical and not blockers,
        "point_in_time_constituents": point_in_time and not blockers,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def eligible_symbols_on(
    contract: dict[str, Any],
    session_date: str,
    requested_symbols: list[str],
) -> dict[str, Any]:
    audit = verify_universe_contract(contract)
    clean_session_date = _clean_date(session_date)
    requested = _normalize_symbols(requested_symbols, str(contract.get("benchmark_symbol") or "").upper())
    declared = set(str(symbol or "").upper() for symbol in contract.get("tradable_symbols") or [])
    blockers = list(audit.get("blockers") or [])
    if not clean_session_date:
        blockers.append("universe_session_date_invalid")
    outside = sorted(symbol for symbol in requested if symbol not in declared)
    if outside:
        blockers.append(f"requested_symbols_outside_universe:{','.join(outside)}")
    if blockers:
        eligible: list[str] = []
    elif contract.get("historical_membership_verified") is True:
        eligible = sorted(
            symbol
            for symbol in requested
            if any(
                str(item.get("symbol") or "") == symbol
                and str(item.get("effective_from") or "") <= clean_session_date
                and (not str(item.get("effective_to") or "") or clean_session_date <= str(item.get("effective_to") or ""))
                for item in contract.get("membership_records") or []
            )
        )
    else:
        eligible = sorted(symbol for symbol in requested if symbol in declared)
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "session_date": clean_session_date,
        "eligible_symbols": eligible,
        "ineligible_symbols": sorted(set(requested) - set(eligible)),
        "historical_membership_verified": contract.get("historical_membership_verified") is True and not blockers,
        "contract_hash": str(contract.get("contract_hash") or ""),
        "paper_authorized": False,
        "live_order_allowed": False,
    }
