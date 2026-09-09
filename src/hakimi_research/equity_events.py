"""Local source-backed event versions and explicit point-in-time clock assumptions.

Hashes bind local bytes; they do not authenticate a publisher, a timestamp, or a
caller's extraction. No provider, language model, execution, or order API is used.
"""
from __future__ import annotations

import base64
import binascii
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

from .documents import canonical_bytes, digest, read_document


SCHEMA_VERSION = "equity-event-v1"
EVENT_KINDS = {"EARNINGS", "GUIDANCE", "MATERIAL_COMPANY", "MACRO", "EARNINGS_SCHEDULE"}
SOURCE_KINDS = {"COMPANY_IR", "SEC_ORIGINAL", "OFFICIAL_MACRO", "SYNTHETIC_FIXTURE"}
MAX_RAW_BYTES = 8 * 1024 * 1024
_METADATA_FIELDS = {
    "event_id", "security_id", "event_kind", "version", "prior_version_hash",
    "source", "first_public_at", "version_public_at", "publication_clock",
    "retrieved_at", "timing", "scheduled_release_at", "facts", "uncertainties",
}
_AUTHORITY = {
    "research_only": True,
    "order_allowed": False,
    "publisher_authenticated": False,
    "publication_clock_independently_verified": False,
    "extraction_semantics_independently_verified": False,
    "profitability_proof": False,
}
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_NUMERIC_TOKEN = re.compile(r"-?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _native(value: Any) -> None:
    if value is None or type(value) in {str, int, bool}:
        return
    if type(value) is list:
        for item in value:
            _native(item)
        return
    if type(value) is dict and all(type(key) is str for key in value):
        for item in value.values():
            _native(item)
        return
    raise ValueError("equity_event_native_json_required_no_floats")


def _shape(value: Any, fields: set[str], label: str) -> None:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("equity_event_shape:" + label)


def _text(value: Any, label: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise ValueError("equity_event_text:" + label)
    return value


def _timestamp(value: Any, label: str) -> datetime:
    _text(value, label)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|\+00:00)", value):
        raise ValueError("equity_event_utc_timestamp_required:" + label)
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("equity_event_timestamp:" + label) from exc
    if "T" not in value or result.tzinfo is None or result.utcoffset() != timedelta(0):
        raise ValueError("equity_event_utc_timestamp_required:" + label)
    return result.astimezone(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _number(value: Any, label: str, *, positive: bool = False) -> Decimal:
    if type(value) is not str or not _DECIMAL.fullmatch(value):
        raise ValueError("equity_event_decimal_string_required:" + label)
    number = Decimal(value)
    if positive and number <= 0:
        raise ValueError("equity_event_positive_number_required:" + label)
    return number


def _seconds(value: Any, label: str, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError("equity_event_delay_seconds:" + label)
    return value


def _evidence(value: Any, raw_text: str) -> list[str]:
    if type(value) is not list:
        raise ValueError("equity_event_evidence_list_required")
    quotes = []
    for item in value:
        if type(item) is not dict:
            raise ValueError("equity_event_evidence_shape")
        if set(item) == {"quote"}:
            quote = _text(item["quote"], "evidence.quote")
            if quote not in raw_text:
                raise ValueError("equity_event_evidence_quote_mismatch")
        elif set(item) == {"start", "end", "quote"}:
            start, end = item["start"], item["end"]
            quote = _text(item["quote"], "evidence.quote")
            if (type(start) is not int or type(end) is not int
                    or not 0 <= start < end <= len(raw_text) or raw_text[start:end] != quote):
                raise ValueError("equity_event_evidence_offset_mismatch")
        else:
            raise ValueError("equity_event_evidence_shape")
        quotes.append(quote)
    return quotes


def _facts(value: Any, raw_text: str) -> None:
    if type(value) is not list:
        raise ValueError("equity_event_facts_list_required")
    names = set()
    fields = {"name", "status", "value", "value_text", "scale", "currency", "unit",
              "fiscal_period", "basis", "evidence", "reason"}
    for fact in value:
        _shape(fact, fields, "fact")
        name = _text(fact["name"], "fact.name")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in names:
            raise ValueError("equity_event_fact_name_invalid_or_duplicate")
        names.add(name)
        status = fact["status"]
        if status not in {"KNOWN", "MISSING", "UNCERTAIN"}:
            raise ValueError("equity_event_fact_status")
        # v1 has no pre-release analyst estimate snapshot/entitlement contract.
        if "consensus" in name and status != "MISSING":
            raise ValueError("equity_event_consensus_not_supported_requires_missing")
        quotes = _evidence(fact["evidence"], raw_text)
        numeric_fields = {"value", "value_text", "scale", "currency", "unit", "fiscal_period", "basis"}
        if status == "MISSING":
            if quotes or any(fact[key] is not None for key in numeric_fields):
                raise ValueError("equity_event_missing_fact_requires_null_fields")
            _text(fact["reason"], "missing_fact.reason")
            continue
        if not quotes:
            raise ValueError("equity_event_nonmissing_fact_requires_evidence")
        if status == "KNOWN" and fact["reason"] is not None:
            raise ValueError("equity_event_known_fact_reason_must_be_null")
        if status == "UNCERTAIN":
            _text(fact["reason"], "uncertain_fact.reason")
            if fact["value"] is None:
                if any(fact[key] is not None for key in numeric_fields):
                    raise ValueError("equity_event_unquantified_fact_requires_null_fields")
                continue
        number = _number(fact["value"], "fact.value")
        token = _text(fact["value_text"], "fact.value_text")
        if not _NUMERIC_TOKEN.fullmatch(token):
            raise ValueError("equity_event_numeric_source_token_invalid")
        if Decimal(token.replace(",", "")) != number:
            raise ValueError("equity_event_numeric_source_token_value_mismatch")
        # A substring of 120 (such as 20) is not evidence for a value of 20.
        token_pattern = r"(?<![\d.,-])" + re.escape(token) + r"(?!\d|[.,]\d)"
        if not any(re.search(token_pattern, quote) for quote in quotes):
            raise ValueError("equity_event_numeric_source_token_absent")
        _number(fact["scale"], "fact.scale", positive=True)
        if fact["unit"] not in {"CURRENCY", "CURRENCY_PER_SHARE", "PERCENT", "COUNT", "RATIO", "DAYS"}:
            raise ValueError("equity_event_fact_unit")
        if fact["unit"] in {"CURRENCY", "CURRENCY_PER_SHARE"}:
            if type(fact["currency"]) is not str or not re.fullmatch(r"[A-Z]{3}", fact["currency"]):
                raise ValueError("equity_event_fact_currency")
        elif fact["currency"] is not None:
            raise ValueError("equity_event_nonmonetary_currency_must_be_null")
        _text(fact["fiscal_period"], "fact.fiscal_period")
        if fact["basis"] not in {"GAAP", "NON_GAAP", "NOT_APPLICABLE"}:
            raise ValueError("equity_event_fact_basis")


def _validate_metadata(metadata: dict, raw_text: str) -> dict:
    _native(metadata)
    _shape(metadata, _METADATA_FIELDS, "metadata")
    for key in ("event_id", "security_id"):
        _text(metadata[key], key)
    if metadata["event_kind"] not in EVENT_KINDS:
        raise ValueError("equity_event_kind")
    version = metadata["version"]
    if type(version) is not int or version < 1:
        raise ValueError("equity_event_version")
    prior = metadata["prior_version_hash"]
    if ((version == 1 and prior is not None)
            or (version > 1 and (type(prior) is not str or not _HASH.fullmatch(prior)))):
        raise ValueError("equity_event_prior_version_hash")
    source = metadata["source"]
    _shape(source, {"url", "kind", "document_type", "disclosure_items", "official_source_status"}, "source")
    url = urlsplit(_text(source["url"], "source.url"))
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.fragment:
        raise ValueError("equity_event_source_https_url_required")
    if source["kind"] not in SOURCE_KINDS or source["official_source_status"] != "DECLARED_UNVERIFIED":
        raise ValueError("equity_event_source_declaration")
    _text(source["document_type"], "source.document_type")
    if type(source["disclosure_items"]) is not list:
        raise ValueError("equity_event_disclosure_items")
    for item in source["disclosure_items"]:
        _text(item, "source.disclosure_item")
    if len(set(source["disclosure_items"])) != len(source["disclosure_items"]):
        raise ValueError("equity_event_duplicate_disclosure_item")
    if source["document_type"] == "8-K" and metadata["event_kind"] == "EARNINGS":
        if "2.02" not in source["disclosure_items"]:
            raise ValueError("equity_event_8k_earnings_requires_results_item")
    clock = metadata["publication_clock"]
    _shape(clock, {"status", "verification_method", "evidence"}, "publication_clock")
    if clock["status"] not in {"ATTESTED", "UNKNOWN"}:
        raise ValueError("equity_event_publication_clock_status")
    if clock["status"] == "ATTESTED":
        _text(clock["verification_method"], "publication_clock.verification_method")
        _text(clock["evidence"], "publication_clock.evidence")
    elif clock["verification_method"] is not None or clock["evidence"] is not None:
        raise ValueError("equity_event_unknown_clock_requires_null_attestation")
    first = metadata["first_public_at"]
    public = metadata["version_public_at"]
    first_at = _timestamp(first, "first_public_at") if first is not None else None
    public_at = _timestamp(public, "version_public_at") if public is not None else None
    if clock["status"] == "ATTESTED" and (first_at is None or public_at is None):
        raise ValueError("equity_event_attested_publication_times_required")
    if first_at is not None and public_at is not None:
        if public_at < first_at or (version == 1 and public_at != first_at):
            raise ValueError("equity_event_publication_clock_order")
        if version > 1 and public_at <= first_at:
            raise ValueError("equity_event_revision_cannot_borrow_first_publication")
    retrieved = _timestamp(metadata["retrieved_at"], "retrieved_at")
    if ((public_at is not None and retrieved < public_at)
            or (first_at is not None and retrieved < first_at)):
        raise ValueError("equity_event_retrieval_before_publication")
    timing = metadata["timing"]
    _shape(timing, {"mode", "received_at", "extraction_completed_at", "collection_delay_seconds",
                    "processing_delay_seconds"}, "timing")
    extracted = _timestamp(timing["extraction_completed_at"], "extraction_completed_at")
    if extracted < retrieved:
        raise ValueError("equity_event_extraction_before_retrieval")
    observed = assumed = None
    if timing["mode"] == "OBSERVED":
        received = _timestamp(timing["received_at"], "received_at")
        if not retrieved <= received <= extracted:
            raise ValueError("equity_event_observed_clock_order")
        if timing["collection_delay_seconds"] is not None or timing["processing_delay_seconds"] is not None:
            raise ValueError("equity_event_observed_delays_must_be_null")
        observed = _iso(extracted)
    elif timing["mode"] == "HISTORICAL_RECONSTRUCTION":
        if timing["received_at"] is not None:
            raise ValueError("equity_event_historical_receipt_must_be_null")
        collection = _seconds(timing["collection_delay_seconds"], "collection", positive=True)
        processing = _seconds(timing["processing_delay_seconds"], "processing", positive=True)
        if public_at is not None:
            try:
                assumed = _iso(public_at + timedelta(seconds=collection + processing))
            except OverflowError as exc:
                raise ValueError("equity_event_assumed_time_overflow") from exc
    else:
        raise ValueError("equity_event_timing_mode")
    scheduled = metadata["scheduled_release_at"]
    if metadata["event_kind"] == "EARNINGS_SCHEDULE":
        scheduled_at = _timestamp(scheduled, "scheduled_release_at")
        if public_at is not None and scheduled_at <= public_at:
            raise ValueError("equity_event_schedule_must_be_announced_before_release")
    elif scheduled is not None:
        raise ValueError("equity_event_schedule_time_only_for_schedule_event")
    _facts(metadata["facts"], raw_text)
    if type(metadata["uncertainties"]) is not list:
        raise ValueError("equity_event_uncertainties_list_required")
    for item in metadata["uncertainties"]:
        _text(item, "uncertainty")
    admissible = clock["status"] == "ATTESTED"
    return {
        "pit_admissible": admissible,
        "available_at": (observed or assumed) if admissible else None,
        "available_at_kind": ("OBSERVED" if observed else "ASSUMED") if admissible else "UNAVAILABLE",
        "observed_available_at": observed if admissible else None,
        "assumed_available_at": assumed if admissible else None,
        "reason": "CALLER_ATTESTED_PUBLICATION_CLOCK" if admissible else "PUBLICATION_CLOCK_UNKNOWN",
    }


def build_equity_event(raw_text_bytes: bytes, metadata: dict) -> dict:
    """Build a sealed local event from exact UTF-8 bytes and explicit caller metadata.

    Retrieval/receipt/extraction times must be actual recorded times. Historical
    mode retains today's retrieval but computes a separately named *assumed*
    availability from this content version's publication and positive delays.
    Publication attestation is supplied by the caller, not verified by this code.
    """
    if type(raw_text_bytes) is not bytes or not raw_text_bytes or len(raw_text_bytes) > MAX_RAW_BYTES:
        raise ValueError("equity_event_raw_bytes_size_or_type")
    try:
        raw_text = raw_text_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("equity_event_raw_utf8_required") from exc
    availability = _validate_metadata(metadata, raw_text)
    # Round trip copies nested caller structures without lossy numeric coercion.
    from .documents import parse_document
    document = parse_document(canonical_bytes(metadata))
    document.update({
        "schema_version": SCHEMA_VERSION,
        "raw": {"encoding": "utf-8", "content_base64": base64.b64encode(raw_text_bytes).decode("ascii"),
                "content_sha256": hashlib.sha256(raw_text_bytes).hexdigest()},
        "availability": availability,
        "authority": dict(_AUTHORITY),
    })
    document["event_hash"] = digest(document)
    return document


def verify_equity_event(document: dict) -> dict:
    """Revalidate bytes, numeric evidence, clocks and seal; return a detached copy."""
    _native(document)
    _shape(document, _METADATA_FIELDS | {"schema_version", "raw", "availability", "authority", "event_hash"}, "document")
    if document["schema_version"] != SCHEMA_VERSION:
        raise ValueError("equity_event_schema_version")
    raw = document["raw"]
    _shape(raw, {"encoding", "content_base64", "content_sha256"}, "raw")
    if raw["encoding"] != "utf-8" or type(raw["content_base64"]) is not str:
        raise ValueError("equity_event_raw_encoding")
    try:
        payload = base64.b64decode(raw["content_base64"], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("equity_event_raw_base64") from exc
    expected = build_equity_event(payload, {key: document[key] for key in _METADATA_FIELDS})
    if canonical_bytes(expected) != canonical_bytes(document):
        raise ValueError("equity_event_document_binding_mismatch")
    return expected


def _lineage(documents: list[dict]) -> dict[tuple[str, str], list[dict]]:
    if type(documents) is not list:
        raise ValueError("equity_event_documents_list_required")
    groups: dict[tuple[str, str], dict[int, dict]] = {}
    for source in documents:
        document = verify_equity_event(source)
        key = (document["security_id"], document["event_id"])
        versions = groups.setdefault(key, {})
        old = versions.get(document["version"])
        if old is not None and old["event_hash"] != document["event_hash"]:
            raise ValueError("equity_event_duplicate_version_conflict")
        versions[document["version"]] = document
    result = {}
    for key, versions in groups.items():
        sequence = [versions[number] for number in sorted(versions)]
        if sorted(versions) != list(range(1, len(versions) + 1)):
            raise ValueError("equity_event_lineage_incomplete")
        for previous, current in zip(sequence, sequence[1:]):
            if current["prior_version_hash"] != previous["event_hash"]:
                raise ValueError("equity_event_lineage_hash_mismatch")
            if current["event_kind"] != previous["event_kind"]:
                raise ValueError("equity_event_lineage_kind_changed")
            old_first, new_first = previous["first_public_at"], current["first_public_at"]
            if old_first is not None and (new_first is None or
                    _timestamp(old_first, "prior_first") != _timestamp(new_first, "new_first")):
                raise ValueError("equity_event_lineage_first_publication_changed")
            old_public, new_public = previous["version_public_at"], current["version_public_at"]
            if old_public is not None and (new_public is None or
                    _timestamp(new_public, "new_public") <= _timestamp(old_public, "prior_public")):
                raise ValueError("equity_event_lineage_publication_not_increasing")
        result[key] = sequence
    return result


def select_event_versions(documents: list[dict], as_of: str) -> list[dict]:
    """Select one latest eligible revision per identity, never a future revision.

    The full contiguous lineage must be supplied, including version 1. Repeated
    copies of exactly the same document are idempotent; conflicts fail closed.
    Unknown publication clocks remain stored but are never PIT-admitted.
    """
    cutoff = _timestamp(as_of, "as_of")
    selected = []
    for _, versions in sorted(_lineage(documents).items()):
        eligible = [item for item in versions if item["availability"]["pit_admissible"]
                    and _timestamp(item["availability"]["available_at"], "available_at") <= cutoff]
        if eligible:
            selected.append(eligible[-1])
    return selected


@contextmanager
def _ledger_lock(directory: Path):
    # OS locks are released on process exit; the small lock file is retained.
    with (directory / ".equity-events.lock").open("a+b") as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            import msvcrt
        except ImportError:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        else:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            try:
                yield
            finally:
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def save_equity_event(document: dict, directory: str | Path) -> Path:
    """Append one validated version under an exclusive lock; never overwrite."""
    verified = verify_equity_event(document)
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ("event_" + verified["event_hash"] + ".json")
    with _ledger_lock(directory):
        existing = []
        for item in sorted(directory.glob("event_*.json")):
            if item.is_symlink() or not item.is_file():
                raise ValueError("equity_event_ledger_regular_file_required")
            stored = verify_equity_event(read_document(item))
            if item.name != "event_" + stored["event_hash"] + ".json":
                raise ValueError("equity_event_ledger_filename_binding")
            existing.append(stored)
        _lineage(existing + [verified])
        if path.exists():
            return path
        with path.open("xb") as handle:
            handle.write(canonical_bytes(verified) + b"\n")
            handle.flush()
    return path


def _sessions(sessions: list[dict]) -> list[dict]:
    if type(sessions) is not list:
        raise ValueError("equity_event_sessions_list_required")
    previous_date = None
    previous_close = None
    result = []
    for session in sessions:
        _shape(session, {"date", "open_utc", "close_utc", "early_close"}, "session")
        try:
            session_date = date.fromisoformat(session["date"])
        except (ValueError, TypeError) as exc:
            raise ValueError("equity_event_session_date") from exc
        if session_date.isoformat() != session["date"] or type(session["early_close"]) is not bool:
            raise ValueError("equity_event_session_date_or_early_close")
        opened = _timestamp(session["open_utc"], "session.open")
        closed = _timestamp(session["close_utc"], "session.close")
        if (opened >= closed or opened.date() != session_date or closed.date() != session_date
                or (previous_date is not None and session_date <= previous_date)
                or (previous_close is not None and opened <= previous_close)):
            raise ValueError("equity_event_session_order_or_window")
        result.append(dict(session))
        previous_date, previous_close = session_date, closed
    return result


def event_session_eligibility(event: dict, sessions: list[dict], bar_latency_seconds: int) -> dict:
    """Locate a full post-availability session, then a strictly later entry open.

    READY only means that the supplied calendar contains the needed sessions;
    it grants no order permission and does not claim those future bars exist.
    The caller must bind sessions to its verified calendar and actual dataset.
    """
    verified = verify_equity_event(event)
    calendar = _sessions(sessions)
    latency = _seconds(bar_latency_seconds, "bar_latency_seconds")
    result = {
        "status": "NOT_READY", "reason": "PUBLICATION_CLOCK_UNKNOWN",
        "event_hash": verified["event_hash"], "available_at": verified["availability"]["available_at"],
        "available_at_kind": verified["availability"]["available_at_kind"],
        "observation_session": None, "confirmation_available_at": None,
        "entry_session": None, "earliest_entry_at": None, "bar_latency_seconds": latency,
        "calendar_authority": "CALLER_SUPPLIED_SESSIONS_NOT_AUTHENTICATED_HERE",
        "order_allowed": False,
    }
    if not verified["availability"]["pit_admissible"]:
        return result
    if verified["event_kind"] == "EARNINGS_SCHEDULE":
        result["reason"] = "SCHEDULE_IS_RISK_CALENDAR_NOT_RELEASE_CONTENT"
        return result
    available = _timestamp(verified["availability"]["available_at"], "available_at")
    for index, session in enumerate(calendar):
        if _timestamp(session["open_utc"], "session.open") < available:
            continue
        result["observation_session"] = session
        try:
            confirmation = _timestamp(session["close_utc"], "session.close") + timedelta(seconds=latency)
        except OverflowError as exc:
            raise ValueError("equity_event_confirmation_time_overflow") from exc
        result["confirmation_available_at"] = _iso(confirmation)
        # Large declared latency can skip one or more subsequent opening prices.
        for candidate in calendar[index + 1:]:
            if _timestamp(candidate["open_utc"], "session.open") > confirmation:
                result.update({"status": "READY", "reason": "CALENDAR_TIMING_ELIGIBLE_ONLY",
                               "entry_session": candidate, "earliest_entry_at": candidate["open_utc"]})
                return result
        result["reason"] = "NEXT_SESSION_AFTER_CONFIRMATION_NOT_IN_CALENDAR"
        return result
    result["reason"] = "FULL_POST_AVAILABILITY_SESSION_NOT_IN_CALENDAR"
    return result
