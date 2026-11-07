"""One explicit public-daily check per ephemeral local-session authorization.

Production must inject hakimi_research.daily_updates._fetch explicitly: it owns
TLS transport, redirect refusal, response limits and no-retry behavior. This
gate never supplies a default fetcher, changes LOCAL_ONLY, or enables brokers,
models, background collection, or research execution.
"""
from __future__ import annotations

from contextvars import ContextVar
from hashlib import sha256
import inspect
import json
import math
import re
import secrets
from threading import RLock, get_ident
import time
from urllib.parse import parse_qsl, urlsplit


CHECK_STOCK = "terminal_daily_check_stock"
CHECK_UPDATE = "terminal_daily_check_update"
ACTIONS = frozenset({CHECK_STOCK, CHECK_UPDATE})
_OPERATION = re.compile(r"[A-Za-z0-9_-]{8,80}\Z")
_SESSION = re.compile(r"[A-Za-z0-9_-]{16,256}\Z")
_CANONICAL = re.compile(r"canon-[0-9a-f]{32}\Z")
_SYMBOL = re.compile(r"[A-Z][A-Z0-9]{0,9}(?:[.-][A-Z])?\Z")
_QUERY_FIELDS = {"period1", "period2", "interval", "events", "includePrePost"}


class PublicDailyAccessError(PermissionError):
    """A known local denial, without secrets or a claim that a source ran."""
    def __init__(self, code):
        self.code = code
        super().__init__(code + ": 本次公开日线请求未获有效授权，未重复获取来源。")


def _deny(code):
    raise PublicDailyAccessError(code)


def _binding(action, payload):
    if type(action) is not str or action not in ACTIONS:
        _deny("PUBLIC_DAILY_ACTION_NOT_ALLOWED")
    if type(payload) is not dict:
        _deny("PUBLIC_DAILY_PAYLOAD_INVALID")
    expected = {"operation_id", "symbol", "history_sessions"} if action == CHECK_STOCK else {"operation_id", "input_id"}
    if set(payload) != expected:
        _deny("PUBLIC_DAILY_PAYLOAD_INVALID")
    operation = payload["operation_id"]
    if type(operation) is not str or _OPERATION.fullmatch(operation) is None:
        _deny("PUBLIC_DAILY_OPERATION_ID_INVALID")
    if action == CHECK_STOCK:
        if (type(payload["symbol"]) is not str or _SYMBOL.fullmatch(payload["symbol"]) is None
                or type(payload["history_sessions"]) is not int or payload["history_sessions"] not in (20, 60, 120)):
            _deny("PUBLIC_DAILY_STOCK_REQUEST_INVALID")
    elif type(payload["input_id"]) is not str or _CANONICAL.fullmatch(payload["input_id"]) is None:
        _deny("PUBLIC_DAILY_INPUT_ID_INVALID")
    # Same canonical JSON convention as the current canonical documents module.
    raw = json.dumps({"action": action, "payload": payload}, ensure_ascii=True,
                     allow_nan=False, sort_keys=True, separators=(",", ":")).encode("ascii")
    return operation, sha256(raw).hexdigest(), json.loads(raw)["payload"]


def _check_url(url, action, payload):
    if type(url) is not str or not url.isascii() or url != url.strip() or any(ord(char) < 32 for char in url):
        _deny("PUBLIC_DAILY_URL_NOT_ALLOWED")
    try:
        parsed = urlsplit(url)
        prefix = "/v8/finance/chart/"
        symbol = parsed.path[len(prefix):] if parsed.path.startswith(prefix) else ""
        pairs = parse_qsl(parsed.query, keep_blank_values=True, strict_parsing=True)
        query = dict(pairs)
        valid = (parsed.scheme == "https" and parsed.netloc == "query1.finance.yahoo.com"
                 and not parsed.fragment and parsed.geturl() == url
                 and _SYMBOL.fullmatch(symbol) is not None
                 and len(pairs) == len(_QUERY_FIELDS) and set(query) == _QUERY_FIELDS
                 and query["interval"] == "1d" and query["events"] == "div,splits"
                 and query["includePrePost"] == "false"
                 and re.fullmatch(r"[0-9]{1,12}", query["period1"]) is not None
                 and re.fullmatch(r"[0-9]{1,12}", query["period2"]) is not None
                 and 0 < int(query["period1"]) < int(query["period2"]))
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid or action == CHECK_STOCK and symbol != payload["symbol"]:
        _deny("PUBLIC_DAILY_URL_NOT_ALLOWED")


class PublicDailyAccess:
    """Synchronous job-thread gate; all authorization is process-memory only.

    UI intent: one explicit '检查并获取公开日线' click calls allow_once and
    submits the bound job. The job executes run_once(..., lambda: daily.mutate
    (...)); that daily instance must have fetcher=gate.fetch. A repeated grant
    before consumption is idempotent and never extends expiry. A consumed,
    revoked, expired or failed operation ID cannot be authorized again.

    Revoke can stop a preparing operation before fetch, but cannot recall an
    already invoked transport. Status reports that distinction. Completed or
    UNKNOWN jobs are read through their existing durable job records, not rerun.
    """
    def __init__(self, session_id, *, fetcher, clock=time.monotonic, ttl_seconds=120, max_records=4096):
        if type(session_id) is not str or _SESSION.fullmatch(session_id) is None:
            raise ValueError("public_daily_session_id_invalid")
        if not callable(fetcher) or not callable(clock):
            raise ValueError("public_daily_explicit_fetcher_and_clock_required")
        if type(ttl_seconds) not in (int, float) or not math.isfinite(ttl_seconds) or not 0 < ttl_seconds <= 300:
            raise ValueError("public_daily_short_ttl_required")
        if type(max_records) is not int or not 1 <= max_records <= 100000:
            raise ValueError("public_daily_record_limit_invalid")
        self._session = session_id
        self._fetcher, self._clock = fetcher, clock
        self._ttl, self._maximum = ttl_seconds, max_records
        self._records = {}
        self._lock = RLock()
        self._context = ContextVar("hakimi_public_daily_request", default=None)
        self._closed = False
        self._actual_attempts = 0
        self._last_outcome = "NOT_REQUESTED"

    def _session_check(self, session_id):
        if type(session_id) is not str or not session_id.isascii() or not secrets.compare_digest(session_id, self._session):
            _deny("PUBLIC_DAILY_SESSION_MISMATCH")

    def _now(self):
        value = self._clock()
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            _deny("PUBLIC_DAILY_CLOCK_INVALID")
        return value

    @staticmethod
    def _expired(record, now):
        # Backwards clock movement cannot extend an authorization.
        return now < record["issued"] or now >= record["expires"]

    def allow_once(self, session_id, action, payload):
        self._session_check(session_id)
        operation, fingerprint, saved_payload = _binding(action, payload)
        with self._lock:
            if self._closed:
                _deny("PUBLIC_DAILY_ACCESS_CLOSED")
            now = self._now()
            record = self._records.get(operation)
            if record is not None:
                if record["fingerprint"] != fingerprint:
                    _deny("PUBLIC_DAILY_PAYLOAD_MISMATCH")
                if record["consumed"] or record["revoked"] or self._expired(record, now):
                    _deny("PUBLIC_DAILY_OPERATION_NOT_REUSABLE")
                return self._status(now)
            if len(self._records) >= self._maximum:
                _deny("PUBLIC_DAILY_SESSION_CAPACITY_REACHED")
            self._records[operation] = {"fingerprint": fingerprint, "action": action, "payload": saved_payload,
                "issued": now, "expires": now + self._ttl, "consumed": False, "revoked": False,
                "active": False, "nonce": None, "thread": None, "attempted": False, "in_flight": False,
                "transport_outcome": "NOT_ATTEMPTED",
                "outcome": "AUTHORIZED"}
            self._last_outcome = "AUTHORIZED"
            return self._status(now)

    def run_once(self, session_id, action, payload, operation):
        self._session_check(session_id)
        identity, fingerprint, _ = _binding(action, payload)
        if not callable(operation):
            _deny("PUBLIC_DAILY_OPERATION_CALLABLE_REQUIRED")
        if self._context.get() is not None:
            _deny("PUBLIC_DAILY_NESTED_OPERATION_REFUSED")
        with self._lock:
            if self._closed:
                _deny("PUBLIC_DAILY_ACCESS_CLOSED")
            now = self._now()
            record = self._records.get(identity)
            if record is None:
                _deny("PUBLIC_DAILY_PERMISSION_REQUIRED")
            if record["fingerprint"] != fingerprint:
                _deny("PUBLIC_DAILY_PAYLOAD_MISMATCH")
            if record["consumed"]:
                _deny("PUBLIC_DAILY_PERMISSION_CONSUMED")
            if record["revoked"]:
                _deny("PUBLIC_DAILY_PERMISSION_REVOKED")
            if self._expired(record, now):
                _deny("PUBLIC_DAILY_PERMISSION_EXPIRED")
            nonce = object()
            record.update(consumed=True, active=True, nonce=nonce, thread=get_ident(), outcome="PREPARING")
            self._last_outcome = "PREPARING"
        context_token = self._context.set((identity, nonce))
        failed = False
        try:
            result = operation()
            if inspect.isawaitable(result):
                if inspect.iscoroutine(result):
                    result.close()
                _deny("PUBLIC_DAILY_SYNCHRONOUS_OPERATION_REQUIRED")
            return result
        except BaseException:
            failed = True
            raise
        finally:
            self._context.reset(context_token)
            with self._lock:
                if failed or record["transport_outcome"] == "FAILED":
                    outcome = "FAILED_AFTER_REQUEST" if record["attempted"] else "FAILED_WITHOUT_REQUEST"
                elif record["attempted"]:
                    outcome = "COMPLETED_AFTER_REVOCATION" if record["revoked"] else "REQUEST_COMPLETED"
                else:
                    outcome = "REVOKED_WITHOUT_REQUEST" if record["revoked"] else "COMPLETED_WITHOUT_REQUEST"
                record.update(active=False, nonce=None, thread=None, outcome=outcome)
                self._last_outcome = outcome

    def fetch(self, url):
        context = self._context.get()
        if context is None:
            _deny("PUBLIC_DAILY_REQUEST_CONTEXT_REQUIRED")
        identity, nonce = context
        with self._lock:
            record = self._records.get(identity)
            if record is None or not record["active"] or record["nonce"] is not nonce:
                _deny("PUBLIC_DAILY_REQUEST_CONTEXT_EXPIRED")
            if record["thread"] != get_ident():
                _deny("PUBLIC_DAILY_REQUEST_THREAD_MISMATCH")
            if self._closed or record["revoked"]:
                _deny("PUBLIC_DAILY_PERMISSION_REVOKED")
            if record["attempted"]:
                _deny("PUBLIC_DAILY_REQUEST_ALREADY_ATTEMPTED")
            if self._expired(record, self._now()):
                _deny("PUBLIC_DAILY_PERMISSION_EXPIRED")
            _check_url(url, record["action"], record["payload"])
            # Count exactly the invocation of the injected transport, not a
            # source receipt's planned-request field, response or successful IO.
            record.update(attempted=True, in_flight=True, outcome="REQUESTING")
            self._actual_attempts += 1
            self._last_outcome = "REQUESTING"
        try:
            result = self._fetcher(url)
            with self._lock:
                record["transport_outcome"] = "RETURNED"
            return result
        except BaseException:
            with self._lock:
                record["transport_outcome"] = "FAILED"
            raise
        finally:
            with self._lock:
                record["in_flight"] = False

    def revoke(self):
        """Trusted local control: revoke unused grants; do not cancel a socket."""
        with self._lock:
            for record in self._records.values():
                if not record["consumed"] or record["active"]:
                    record["revoked"] = True
            self._last_outcome = "REVOKED"
            return self._status(self._now())

    def close(self):
        with self._lock:
            self._closed = True
            return self.revoke()

    def _status(self, now):
        records = list(self._records.values())
        pending = sum(not row["consumed"] and not row["revoked"] and not self._expired(row, now) for row in records)
        active = sum(row["active"] for row in records)
        in_flight = sum(row["in_flight"] for row in records)
        revoked_in_flight = sum(row["in_flight"] and row["revoked"] for row in records)
        revoked_preparing = sum(row["active"] and row["revoked"] and not row["attempted"] for row in records)
        state = ("REVOKED_IN_FLIGHT" if revoked_in_flight else "REQUESTING" if in_flight
                 else "REVOKED_PREPARING" if revoked_preparing else "PREPARING" if active
                 else "AVAILABLE_ONCE" if pending and not self._closed else "DISABLED")
        return {"schema_version": "hakimi-public-daily-access-v1", "state": state,
            "scope": "ONE_EXPLICIT_DAILY_CHECK", "provider": "Yahoo Finance",
            "supported_actions": sorted(ACTIONS),
            "allowed_actions": sorted({row["action"] for row in records if not row["consumed"]
                and not row["revoked"] and not self._expired(row, now) and not self._closed}),
            "closed": self._closed,
            "unconsumed_authorizations": pending if not self._closed else 0,
            "consumed_authorizations": sum(row["consumed"] for row in records),
            "revoked_authorizations": sum(row["revoked"] for row in records),
            "expired_unconsumed_authorizations": sum(not row["consumed"] and not row["revoked"] and self._expired(row, now) for row in records),
            "operations_in_flight": active, "requests_in_flight": in_flight,
            "revoked_preparing_operations": revoked_preparing,
            "actual_attempts": self._actual_attempts, "last_outcome": self._last_outcome,
            "request_cancellation_supported": False, "automatic_retry": False,
            "broker_allowed": False, "model_requests_allowed": False,
            "background_collection_allowed": False, "paper_allowed": False,
            "live_allowed": False, "order_allowed": False}

    def status(self):
        with self._lock:
            return self._status(self._now())

    def request_status(self, session_id, action, payload):
        """Read counts for the exact bound operation, without returning its ID.

        Useful when the source-intake record counts a planned fetcher invocation
        before this gate allows actual transport. Never overwrite that record.
        """
        self._session_check(session_id)
        identity, fingerprint, _ = _binding(action, payload)
        with self._lock:
            record = self._records.get(identity)
            if record is None:
                _deny("PUBLIC_DAILY_PERMISSION_REQUIRED")
            if record["fingerprint"] != fingerprint:
                _deny("PUBLIC_DAILY_PAYLOAD_MISMATCH")
            return {"consumed": record["consumed"], "revoked": record["revoked"],
                "expired": self._expired(record, self._now()), "operation_in_flight": record["active"],
                "request_in_flight": record["in_flight"], "actual_attempts": int(record["attempted"]),
                "transport_outcome": record["transport_outcome"], "outcome": record["outcome"],
                "request_cancellation_supported": False, "automatic_retry": False}
