from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from statistics import median
import time
from typing import Any, Callable
import urllib.error
import urllib.request


TRUSTED_CLOCK_SCHEMA_VERSION = "trusted-clock-attestation-v2"
TRUSTED_CLOCK_LEGACY_SCHEMA_VERSION = "trusted-clock-attestation-v1"
DEFAULT_CLOCK_TIMEOUT_SECONDS = 2.5
DEFAULT_MAX_LOCAL_SKEW_MS = 30_000
DEFAULT_MAX_PROVIDER_SPREAD_MS = 5_000
DEFAULT_MAX_ROUND_TRIP_MS = 5_000


def _canonical_hash(payload: Any) -> str:
    raw = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _strict_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        clean = value.strip()
        if clean and clean.lstrip("-").isdigit():
            return int(clean)
    return None


def _verify_clock_source_evidence(source: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    clean_source = str(source.get("source") or "").strip()
    status = str(source.get("status") or "").upper()
    expected_hash = str(source.get("evidence_hash") or "")
    hash_payload = dict(source)
    hash_payload.pop("evidence_hash", None)
    if not clean_source:
        blockers.append("source_missing")
    if not expected_hash or _canonical_hash(hash_payload) != expected_hash:
        blockers.append("evidence_hash_invalid")
    if status not in {"PASS", "ERROR"}:
        blockers.append("status_invalid")

    numeric_fields = {
        field: _strict_int(source.get(field))
        for field in (
            "requested_at_ms",
            "received_at_ms",
            "round_trip_ms",
            "midpoint_local_ms",
            "server_time_ms",
            "offset_ms",
        )
    }
    if any(value is None for value in numeric_fields.values()):
        blockers.append("timestamp_fields_invalid")
        return list(dict.fromkeys(blockers))

    requested_at = int(numeric_fields["requested_at_ms"] or 0)
    received_at = int(numeric_fields["received_at_ms"] or 0)
    round_trip_ms = int(numeric_fields["round_trip_ms"] or 0)
    midpoint_local_ms = int(numeric_fields["midpoint_local_ms"] or 0)
    server_time_ms = int(numeric_fields["server_time_ms"] or 0)
    offset_ms = int(numeric_fields["offset_ms"] or 0)
    if requested_at < 0 or received_at < requested_at:
        blockers.append("request_window_invalid")
    expected_round_trip = max(received_at - requested_at, 0)
    if round_trip_ms != expected_round_trip:
        blockers.append("round_trip_mismatch")
    if midpoint_local_ms != requested_at + (expected_round_trip // 2):
        blockers.append("midpoint_mismatch")

    if status == "PASS":
        if not str(source.get("endpoint") or "").strip():
            blockers.append("endpoint_missing")
        if requested_at <= 0 or received_at <= 0:
            blockers.append("request_timestamp_invalid")
        if server_time_ms <= 0:
            blockers.append("server_timestamp_invalid")
        elif offset_ms != server_time_ms - midpoint_local_ms:
            blockers.append("offset_mismatch")
        if str(source.get("error") or ""):
            blockers.append("pass_source_has_error")
    elif status == "ERROR":
        if server_time_ms != 0:
            blockers.append("error_source_has_server_time")
        if offset_ms != 0:
            blockers.append("error_source_has_offset")
        if not str(source.get("error") or ""):
            blockers.append("error_source_reason_missing")
    return list(dict.fromkeys(blockers))


def _fetch_json_clock(
    *,
    source: str,
    endpoint: str,
    parse_server_time_ms: Callable[[dict[str, Any]], int],
    timeout_seconds: float,
    now_ms: Callable[[], int] = _now_ms,
) -> dict[str, Any]:
    requested_at = int(now_ms())
    payload: dict[str, Any] = {}
    error = ""
    try:
        request = urllib.request.Request(
            endpoint,
            headers={"User-Agent": "HakimiTrade-ForwardClock/1.0"},
        )
        with urllib.request.urlopen(request, timeout=max(float(timeout_seconds), 0.1)) as response:
            decoded = json.loads(response.read().decode("utf-8"))
            if not isinstance(decoded, dict):
                raise ValueError("clock_response_is_not_an_object")
            payload = decoded
        server_time_ms = int(parse_server_time_ms(payload))
        if server_time_ms <= 0:
            raise ValueError("clock_server_timestamp_invalid")
        status = "PASS"
    except (OSError, ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, urllib.error.URLError) as exc:
        server_time_ms = 0
        status = "ERROR"
        error = type(exc).__name__
    received_at = int(now_ms())
    round_trip_ms = max(received_at - requested_at, 0)
    midpoint_local_ms = requested_at + (round_trip_ms // 2)
    evidence = {
        "source": str(source),
        "endpoint": str(endpoint),
        "status": status,
        "error": error,
        "requested_at_ms": requested_at,
        "received_at_ms": received_at,
        "round_trip_ms": round_trip_ms,
        "midpoint_local_ms": midpoint_local_ms,
        "server_time_ms": server_time_ms,
        "offset_ms": server_time_ms - midpoint_local_ms if server_time_ms else 0,
    }
    evidence["evidence_hash"] = _canonical_hash(evidence)
    return evidence


def _parse_okx_time(payload: dict[str, Any]) -> int:
    rows = payload.get("data") or []
    return int(rows[0]["ts"])


def _parse_coinbase_time(payload: dict[str, Any]) -> int:
    return int(float((payload.get("data") or {})["epoch"]) * 1000)


def fetch_external_clock_evidence(
    *,
    timeout_seconds: float = DEFAULT_CLOCK_TIMEOUT_SECONDS,
) -> list[dict[str, Any]]:
    providers = [
        (
            "OKX_PUBLIC_TIME",
            "https://www.okx.com/api/v5/public/time",
            _parse_okx_time,
        ),
        (
            "COINBASE_PUBLIC_TIME",
            "https://api.coinbase.com/v2/time",
            _parse_coinbase_time,
        ),
    ]
    evidence: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=len(providers), thread_name_prefix="forward-clock") as executor:
        futures = {
            executor.submit(
                _fetch_json_clock,
                source=source,
                endpoint=endpoint,
                parse_server_time_ms=parser,
                timeout_seconds=timeout_seconds,
            ): source
            for source, endpoint, parser in providers
        }
        for future in as_completed(futures):
            try:
                evidence.append(dict(future.result()))
            except Exception as exc:
                fallback = {
                    "source": futures[future],
                    "endpoint": "",
                    "status": "ERROR",
                    "error": type(exc).__name__,
                    "requested_at_ms": 0,
                    "received_at_ms": 0,
                    "round_trip_ms": 0,
                    "midpoint_local_ms": 0,
                    "server_time_ms": 0,
                    "offset_ms": 0,
                }
                fallback["evidence_hash"] = _canonical_hash(fallback)
                evidence.append(fallback)
    return sorted(evidence, key=lambda item: str(item.get("source") or ""))


def build_trusted_clock_attestation(
    *,
    local_now_ms: int,
    provider_evidence: list[dict[str, Any]],
    minimum_sources: int = 1,
    max_local_skew_ms: int = DEFAULT_MAX_LOCAL_SKEW_MS,
    max_provider_spread_ms: int = DEFAULT_MAX_PROVIDER_SPREAD_MS,
    max_round_trip_ms: int = DEFAULT_MAX_ROUND_TRIP_MS,
) -> dict[str, Any]:
    blockers: list[str] = []
    warnings: list[str] = []
    valid_sources: list[dict[str, Any]] = []
    normalized_sources: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for item in provider_evidence:
        source = dict(item or {})
        normalized_sources.append(source)
        source_name = str(source.get("source") or "UNKNOWN")
        source_blockers = _verify_clock_source_evidence(source)
        if source_name in seen_sources:
            source_blockers.append("duplicate_source")
        seen_sources.add(source_name)
        blockers.extend(
            f"clock_source_invalid:{source_name}:{reason}"
            for reason in source_blockers
        )
        if source_blockers:
            continue
        if source.get("status") != "PASS":
            continue
        if int(source.get("server_time_ms") or 0) <= 0:
            continue
        if int(source.get("round_trip_ms") or 0) > max(int(max_round_trip_ms), 1):
            continue
        valid_sources.append(source)

    required_sources = max(int(minimum_sources), 1)
    if len(valid_sources) < required_sources:
        blockers.append(f"external_clock_sources_insufficient:{len(valid_sources)}<{required_sources}")
    offsets = [int(item.get("offset_ms") or 0) for item in valid_sources]
    median_offset_ms = int(round(float(median(offsets)))) if offsets else 0
    provider_spread_ms = max(offsets) - min(offsets) if offsets else 0
    if offsets and abs(median_offset_ms) > max(int(max_local_skew_ms), 1):
        blockers.append(f"local_clock_skew_exceeds_limit:{abs(median_offset_ms)}")
    if len(offsets) >= 2 and provider_spread_ms > max(int(max_provider_spread_ms), 1):
        blockers.append(f"external_clock_sources_disagree:{provider_spread_ms}")
    if len(valid_sources) == 1:
        warnings.append("single_external_clock_source")

    status = "PASS" if not blockers else "BLOCK"
    quality = "EXTERNAL_QUORUM" if len(valid_sources) >= 2 else "EXTERNAL_SINGLE_SOURCE" if valid_sources else "UNATTESTED"
    payload = {
        "schema_version": TRUSTED_CLOCK_SCHEMA_VERSION,
        "status": status,
        "quality": quality,
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": warnings,
        "local_now_ms": int(local_now_ms),
        "attested_now_ms": int(local_now_ms) + median_offset_ms if valid_sources else 0,
        "median_offset_ms": median_offset_ms,
        "provider_spread_ms": provider_spread_ms,
        "external_source_count": len(valid_sources),
        "required_external_source_count": required_sources,
        "max_local_skew_ms": int(max_local_skew_ms),
        "max_provider_spread_ms": int(max_provider_spread_ms),
        "max_round_trip_ms": int(max_round_trip_ms),
        "sources": normalized_sources,
        "observation_only": True,
        "paper_authorized": False,
        "live_order_allowed": False,
    }
    payload["attestation_hash"] = _canonical_hash(payload)
    return payload


def verify_trusted_clock_attestation(attestation: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(attestation, dict):
        return {
            "status": "BLOCK",
            "blockers": ["clock_attestation_not_an_object"],
            "expected_hash": "",
            "paper_authorized": False,
            "live_order_allowed": False,
        }
    payload = dict(attestation)
    expected_hash = str(payload.pop("attestation_hash", "") or "")
    blockers: list[str] = []
    supplied_schema = str(attestation.get("schema_version") or "")
    if supplied_schema not in {TRUSTED_CLOCK_SCHEMA_VERSION, TRUSTED_CLOCK_LEGACY_SCHEMA_VERSION}:
        blockers.append("clock_attestation_schema_invalid")
    if str(attestation.get("status") or "") != "PASS":
        blockers.append("clock_attestation_not_passed")
    attested_now_ms = _strict_int(attestation.get("attested_now_ms"))
    if attested_now_ms is None or attested_now_ms <= 0:
        blockers.append("clock_attestation_timestamp_invalid")
    if not expected_hash or _canonical_hash(payload) != expected_hash:
        blockers.append("clock_attestation_hash_mismatch")

    sources_value = attestation.get("sources")
    sources = [dict(item) for item in sources_value] if isinstance(sources_value, list) and all(isinstance(item, dict) for item in sources_value) else []
    if not isinstance(sources_value, list) or len(sources) != len(sources_value):
        blockers.append("clock_attestation_sources_invalid")

    integer_fields = {
        field: _strict_int(attestation.get(field))
        for field in (
            "local_now_ms",
            "required_external_source_count",
            "max_local_skew_ms",
            "max_provider_spread_ms",
            "max_round_trip_ms",
        )
    }
    if (
        integer_fields["local_now_ms"] is None
        or int(integer_fields["local_now_ms"] or 0) <= 0
        or integer_fields["required_external_source_count"] is None
        or int(integer_fields["required_external_source_count"] or 0) <= 0
        or any(
            integer_fields[field] is None or int(integer_fields[field] or 0) <= 0
            for field in ("max_local_skew_ms", "max_provider_spread_ms", "max_round_trip_ms")
        )
    ):
        blockers.append("clock_attestation_limits_invalid")
    else:
        rebuilt = build_trusted_clock_attestation(
            local_now_ms=int(integer_fields["local_now_ms"] or 0),
            provider_evidence=sources,
            minimum_sources=int(integer_fields["required_external_source_count"] or 1),
            max_local_skew_ms=int(integer_fields["max_local_skew_ms"] or 0),
            max_provider_spread_ms=int(integer_fields["max_provider_spread_ms"] or 0),
            max_round_trip_ms=int(integer_fields["max_round_trip_ms"] or 0),
        )
        semantic_fields = (
            "status",
            "quality",
            "blockers",
            "warnings",
            "local_now_ms",
            "attested_now_ms",
            "median_offset_ms",
            "provider_spread_ms",
            "external_source_count",
            "required_external_source_count",
            "max_local_skew_ms",
            "max_provider_spread_ms",
            "max_round_trip_ms",
        )
        for field in semantic_fields:
            if attestation.get(field) != rebuilt.get(field):
                blockers.append(f"clock_attestation_semantic_mismatch:{field}")

    if attestation.get("observation_only") is not True:
        blockers.append("clock_attestation_observation_only_invalid")
    if attestation.get("paper_authorized") is not False or attestation.get("live_order_allowed") is not False:
        blockers.append("clock_attestation_execution_authority_invalid")
    return {
        "status": "PASS" if not blockers else "BLOCK",
        "blockers": list(dict.fromkeys(blockers)),
        "warnings": ["legacy_clock_schema_verified_with_v2_semantics"]
        if supplied_schema == TRUSTED_CLOCK_LEGACY_SCHEMA_VERSION and not blockers
        else [],
        "expected_hash": expected_hash,
        "paper_authorized": False,
        "live_order_allowed": False,
    }


def attest_utc_clock(
    *,
    timeout_seconds: float = DEFAULT_CLOCK_TIMEOUT_SECONDS,
    minimum_sources: int = 1,
) -> dict[str, Any]:
    evidence = fetch_external_clock_evidence(timeout_seconds=timeout_seconds)
    return build_trusted_clock_attestation(
        local_now_ms=_now_ms(),
        provider_evidence=evidence,
        minimum_sources=minimum_sources,
    )
