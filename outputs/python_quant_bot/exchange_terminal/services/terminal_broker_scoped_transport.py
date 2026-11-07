"""Bounded synchronous transport seam; there is no default socket or permit.

This offline slice supplies local *additional* limits. Durable consumption,
original-intent reservation, source freshness, fee/tick evidence and actual
authorization belong to a future trusted gate/journal. False profile permissions
are never treated as permission. A caller must inject every IO dependency.

Low-level implementations must honour each timeout; a future worker supervisor
must enforce a separate hard process deadline against a wedged implementation.
No Python wrapper can interrupt an arbitrary injected blocking function safely.
"""
from contextlib import AbstractContextManager
from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
import json
import math
from threading import Lock
from types import MappingProxyType
from typing import Protocol

from .terminal_broker_wire_profile import VerifiedWireProfile, WIRE_ACTIONS


class TransportError(ValueError):
    """A local contract refusal; never an acknowledgement from the broker."""


class DispatchGate(Protocol):
    def before_connect(self, context, permit) -> AbstractContextManager: ...
    def before_write(self, context, permit) -> AbstractContextManager: ...


class WireConnection(Protocol):
    # connect/send are nonblocking beginnings (timeout MUST be zero).
    def connect(self, endpoint, *, timeout: float): ...
    def wait_connected(self, *, timeout: float): ...
    def send(self, data: bytes, *, timeout: float) -> int: ...
    def recv(self, maximum: int, *, timeout: float) -> bytes: ...
    def peek(self, maximum: int, *, timeout: float) -> bytes: ...
    def close(self, *, timeout: float): ...


class Clock(Protocol):
    def monotonic(self) -> float: ...
    def utcnow(self) -> datetime: ...


class EvidenceSink(Protocol):
    def write(self, record: bytes): ...


def _require(condition, code):
    if not condition:
        raise TransportError(code)


def _json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


@dataclass(frozen=True, slots=True)
class RawOutcome:
    status: str
    action: str
    channel: str
    profile_id: str
    frame_sha256: str | None
    serial: int | None
    bytes_written: int
    possible_bytes_written: int
    bytes_received: int
    response_sha256: str | None
    broker_ret_type: int | None
    error: str | None
    started_monotonic: float
    finished_monotonic: float
    cleanup_confirmed: bool | None
    automatic_retry: bool = False
    economic_acceptance: str = "NOT_INFERRED"


class ScopedTransport:
    """Two explicit channels, one in-flight frame each, no queue or retry.

    `factory(channel)` creates an unconnected connection. `peek(1, timeout=0)`
    is nonblocking and is used only to detect already visible unsolicited data;
    it cannot prove that an unsolicited packet will never arrive in the future.
    Neither the gate nor the sink may be supplied by untrusted renderer data.
    """

    def __init__(self, profile, *, factory, clock, gate, sink, codec):
        _require(type(profile) is VerifiedWireProfile, "typed_profile_required")
        value = profile.as_dict()
        _require(value["mode"] == "OFFICIAL_SIMULATION" and value["sdk_environment"] == "SIMULATE",
                 "simulate_only")
        _require(value.get("protocol_policy", {}).get("encryption_policy") == "PLAINTEXT_OFFLINE_CODEC_TEST",
                 "offline_plaintext_profile_required")
        _require(callable(factory) and all(x is not None for x in (clock, gate, sink, codec)),
                 "explicit_dependencies_required")
        self.profile, self._value, self._bounds = profile, value, value["wire_bounds"]
        self._factory, self._clock, self._gate, self._sink, self._codec = factory, clock, gate, sink, codec
        self._wall = clock.monotonic() + self._bounds["wall_timeout_seconds"]
        self._expiry = datetime.fromisoformat(self._bounds["valid_until"])
        self._created = datetime.fromisoformat(value["created_at"])
        self._wall_now()
        self._locks = {name: Lock() for name in ("quote", "trade")}
        self._budget_lock = Lock()
        self._connections, self._ready, self._keepalive = {}, set(), {}
        self._serials = {name: set() for name in self._locks}
        self._counts, self._wire, self._output, self._records = {}, 0, 0, 0
        self._closed = False
        self._cleanup_deadline = None
        self._cleanup_failed = self._unknown_seen = False
        self._final_json = None

    def _wall_now(self):
        now = self._clock.utcnow()
        _require(now.tzinfo is not None, "aware_clock_required")
        _require(now >= self._created, "clock_before_profile_creation")
        _require(now < self._expiry, "deadline_expired")
        return now

    def _reserve_outcome(self):
        # Reserve each ordinary acknowledgement BEFORE IO, in the ordinary
        # output region. The distinct final-summary reserve remains untouched.
        with self._budget_lock:
            _require(self._output + 2048 <= self._bounds["max_output_bytes"] -
                     self._bounds["reserved_final_output_bytes"], "ordinary_output_budget_exhausted")
            self._output += 2048
        return 2048

    def _deadline(self, channel, requested, seconds):
        _require(type(requested) in (int, float) and math.isfinite(requested), "deadline_invalid")
        now = self._clock.monotonic()
        wall_now = self._wall_now()
        result = min(requested, self._wall, now + seconds,
                     now + (self._expiry - wall_now).total_seconds(),
                     self._keepalive.get(channel, math.inf))
        _require(result > now, "deadline_expired")
        return result

    def _remaining(self, deadline):
        result = deadline - self._clock.monotonic()
        self._wall_now()
        _require(result > 0, "deadline_expired")
        return result

    def _lock(self, channel):
        _require(channel in self._locks and not self._closed, "channel_unavailable")
        lock = self._locks[channel]
        _require(lock.acquire(blocking=False), "channel_busy_no_queue")
        return lock

    def _consume(self, channel, action):
        _require(WIRE_ACTIONS.get(action, (None,))[0] == channel, "action_channel_mismatch")
        with self._budget_lock:
            used = self._counts.get(action, 0)
            _require(used < self._bounds["actions"].get(action, 0), "action_budget_exhausted")
            self._counts[action] = used + 1

    def _reserve_wire(self, length):
        with self._budget_lock:
            _require(self._wire + length <= self._bounds["max_wire_bytes"], "wire_budget_exhausted")
            self._wire += length

    def _refund_wire(self, length):
        with self._budget_lock:
            self._wire -= length

    def _emit(self, kind, data=b"", **metadata):
        # Each sink record is a small JSON line followed by bounded raw bytes.
        # Raw handshake data are private evidence and never the UI outcome.
        record = _json({"kind": kind, "raw_bytes": len(data), **metadata}) + b"\n" + data
        with self._budget_lock:
            _require(self._records < self._bounds["max_observation_records"], "evidence_record_budget_exhausted")
            _require(self._output + len(record) <= self._bounds["max_output_bytes"] -
                     self._bounds["reserved_final_output_bytes"], "evidence_byte_budget_exhausted")
            self._records += 1
            self._output += len(record)
        self._sink.write(record)

    def _context(self, channel, action, deadline, *, info=None, offset=0, total=0):
        scopes = self._value["deduplication"]
        return MappingProxyType({"profile_id": self._value["id"],
            "intent_scope_id": scopes["intent_scope_id"], "account_scope_id": scopes["account_scope_id"],
            "mode": self._value["mode"], "channel": channel, "action": action,
            "frame_sha256": info.frame_sha256 if info else None, "serial": info.serial if info else None,
            "offset": offset, "total_bytes": total, "deadline": deadline})

    def _dispose(self, channel, deadline):
        connection = self._connections.pop(channel, None)
        self._ready.discard(channel)
        if connection is not None:
            with self._budget_lock:
                if self._cleanup_deadline is None:
                    self._cleanup_deadline = min(deadline, self._clock.monotonic() +
                                                 self._bounds["cleanup_timeout_seconds"])
                cleanup_deadline = min(deadline, self._cleanup_deadline)
            try:
                # One cleanup deadline for the entire profile. Another channel
                # or a later failure cannot reset this reserved allowance.
                allowance = max(0.0, cleanup_deadline - self._clock.monotonic())
                connection.close(timeout=allowance)
                _require(self._clock.monotonic() <= cleanup_deadline, "cleanup_deadline_exceeded")
            except Exception:
                self._cleanup_failed = True
                return False
        return True

    def _outcome(self, *, status, action, channel, started, info=None, sent=0,
                 possible=0, received=0, response=None, ret_type=None, error=None,
                 cleanup_confirmed=None, slot):
        if status == "UNKNOWN":
            self._unknown_seen = True
        result = RawOutcome(status, action, channel, self._value["id"],
            info.frame_sha256 if info else None, info.serial if info else None,
            sent, possible, received, sha256(response).hexdigest() if response else None,
            ret_type, error, started, self._clock.monotonic(), cleanup_confirmed)
        final = _json(asdict(result))
        _require(len(final) <= slot, "bounded_outcome_contract_failed")
        with self._budget_lock:
            self._output -= slot - len(final)
        return result

    @staticmethod
    def _error(error, fallback):
        text = str(error) if isinstance(error, TransportError) else ""
        return text if text.isascii() and len(text) <= 80 and text.replace("_", "").isalnum() else fallback

    def connect(self, channel, permit, deadline):
        lock = self._lock(channel)
        try:
            slot = self._reserve_outcome()
        except Exception:
            lock.release()
            raise
        started = self._clock.monotonic()
        action = channel + "_connect"
        attempted = False
        try:
            _require(channel not in self._connections, "connection_already_exists")
            deadline = self._deadline(channel, deadline, self._bounds["connect_timeout_seconds"])
            self._consume(channel, action)
            context = self._context(channel, action, deadline)
            with self._gate.before_connect(context, permit):
                self._remaining(deadline)
                attempted = True
                connection = self._factory(channel)
                self._connections[channel] = connection
                self._remaining(deadline)
                connection.connect(dict(self._bounds["endpoint"]), timeout=0)
            # Wait for the nonblocking connection attempt without holding the
            # stop barrier. A stop can take effect before the first frame write.
            connection.wait_connected(timeout=self._remaining(deadline))
            self._remaining(deadline)
            self._emit("connected", channel=channel, profile_id=self._value["id"])
            return self._outcome(status="CONNECTED_NOT_INITIALIZED", action=action, channel=channel,
                                 started=started, slot=slot)
        except Exception as error:
            clean = self._dispose(channel, self._clock.monotonic() + self._bounds["cleanup_timeout_seconds"])
            return self._outcome(status="UNKNOWN" if attempted else "NOT_WRITTEN", action=action,
                channel=channel, started=started, error=self._error(error, "connect_or_gate_failed"),
                cleanup_confirmed=clean, slot=slot)
        finally:
            lock.release()

    def _peek(self, connection, deadline):
        self._remaining(deadline)
        data = connection.peek(1, timeout=0)
        _require(type(data) is bytes and len(data) <= 1, "peek_contract_invalid")
        if data:
            self._reserve_wire(len(data))
            self._emit("unsolicited_peek", data)
            raise TransportError("unsolicited_or_trailing_data")

    def exchange(self, channel, action, frame, permit, deadline):
        _require(type(action) is str and action in WIRE_ACTIONS, "unknown_action")
        lock = self._lock(channel)
        try:
            slot = self._reserve_outcome()
        except Exception:
            lock.release()
            raise
        started = self._clock.monotonic()
        sent = possible = received = 0
        attempted = False
        response = bytearray()
        info = None
        try:
            _require(channel in self._connections, "connection_required")
            _require(action == channel + "_init" or channel in self._ready, "handshake_required")
            info = self._codec.validate_request(self.profile, action, frame)
            _require(info.serial not in self._serials[channel], "serial_already_used")
            _require(WIRE_ACTIONS.get(action, (None,))[0] == channel, "action_channel_mismatch")
            seconds = self._bounds["handshake_timeout_seconds" if action.endswith("_init") else "rpc_timeout_seconds"]
            deadline = self._deadline(channel, deadline, seconds)
            self._consume(channel, action)
            self._serials[channel].add(info.serial)
            connection = self._connections[channel]
            self._peek(connection, deadline)
            self._emit("request_frame", frame, action=action, channel=channel, frame_sha256=info.frame_sha256)
            while sent < len(frame):
                context = self._context(channel, action, deadline, info=info, offset=sent, total=len(frame))
                remaining = len(frame) - sent
                self._reserve_wire(remaining)
                entered_send = False
                try:
                    with self._gate.before_write(context, permit):
                        # Repeat the same immutable bytes/scope/deadline check on
                        # every continuation while the stop barrier is held.
                        current = self._codec.validate_request(self.profile, action, frame)
                        _require(current == info and sha256(frame).hexdigest() == info.frame_sha256,
                                 "frame_changed")
                        self._remaining(deadline)
                        entered_send = attempted = True
                        possible = sent + remaining
                        written = connection.send(frame[sent:], timeout=0)
                        _require(type(written) is int and 0 < written <= remaining, "short_write_contract_invalid")
                        # Preserve a returned write count even if the barrier's
                        # __exit__ subsequently fails. Its economic result is
                        # still UNKNOWN, but these bytes are a known fact.
                        sent += written
                        possible = sent
                    self._refund_wire(remaining - written)
                except Exception:
                    if not entered_send:
                        self._refund_wire(remaining)
                    # A send exception has unknown written length. Reserve the
                    # entire offered part rather than silently refund it.
                    raise
                after_write = getattr(self._gate, "after_write", None)
                if after_write is not None:
                    after_write(context, permit, written)
                self._remaining(deadline)
            wanted = 44
            while True:
                while len(response) < wanted:
                    amount = wanted - len(response)
                    self._reserve_wire(amount)
                    try:
                        data = connection.recv(amount, timeout=self._remaining(deadline))
                    except Exception:
                        # No bytes returned: conservatively retain reservation.
                        raise
                    _require(type(data) is bytes and 0 < len(data) <= amount, "read_contract_invalid")
                    self._refund_wire(amount - len(data))
                    response.extend(data)
                    received += len(data)
                    self._remaining(deadline)
                if wanted != 44:
                    break
                body_length = self._codec.response_header(self.profile, action, info.serial, bytes(response))
                _require(type(body_length) is int and 0 < body_length <= self._bounds["max_frame_bytes"] - 44,
                         "response_body_length_invalid")
                wanted += body_length
            self._peek(connection, deadline)
            raw = bytes(response)
            self._emit("response_frame", raw, action=action, channel=channel)
            decoded = self._codec.decode_response(self.profile, action, info.serial, raw)
            self._emit("response_presence", decoded.fields_json, action=action, channel=channel)
            self._remaining(deadline)
            if action.endswith("_init"):
                _require(decoded.ret_type == 0 and type(decoded.keep_alive_interval) is int and
                         decoded.keep_alive_interval > 0, "handshake_interval_or_result_missing")
                # No heartbeat is scheduled. This deadline can only shorten the
                # remaining channel lifetime. Anchor at request start rather
                # than receipt time: a delayed reply cannot add new lifetime.
                self._keepalive[channel] = started + decoded.keep_alive_interval
                _require(self._clock.monotonic() < self._keepalive[channel], "handshake_interval_already_elapsed")
                self._codec.accept_handshake(self.profile, channel, info.serial, raw)
                self._ready.add(channel)
            return self._outcome(status="RESPONSE_RECEIVED", action=action, channel=channel,
                started=started, info=info, sent=sent, possible=possible, received=received,
                response=raw, ret_type=decoded.ret_type, slot=slot)
        except Exception as error:
            if response:
                try:
                    self._emit("incomplete_or_rejected_response", bytes(response), action=action, channel=channel)
                except Exception:
                    pass  # Budget/sink failure cannot become success or a retry.
            clean = self._dispose(channel, self._clock.monotonic() + self._bounds["cleanup_timeout_seconds"])
            return self._outcome(status="UNKNOWN" if attempted else "NOT_WRITTEN", action=action,
                channel=channel, started=started, info=info, sent=sent, possible=possible, received=received,
                response=bytes(response) or None,
                error=self._error(error, "codec_gate_or_io_failed"), cleanup_confirmed=clean, slot=slot)
        finally:
            lock.release()

    def close(self, deadline):
        """Release idle handles only, without cancel RPCs, retries or business IO."""
        _require(type(deadline) in (int, float) and math.isfinite(deadline), "deadline_invalid")
        acquired = []
        try:
            for lock in self._locks.values():
                _require(lock.acquire(blocking=False), "channel_busy_no_queue")
                acquired.append(lock)
            self._closed = True
            deadline = min(deadline, self._clock.monotonic() + self._bounds["cleanup_timeout_seconds"])
            confirmations = [self._dispose(channel, deadline) for channel in self._locks]
            return {"closed": True, "cleanup_confirmed": all(confirmations) and not self._cleanup_failed, "automatic_retry": False,
                    "business_action": None}
        finally:
            for lock in acquired:
                lock.release()

    def budget_snapshot(self):
        with self._budget_lock:
            return {"local_action_counts": dict(self._counts), "conservative_wire_bytes": self._wire,
                    "output_bytes": self._output, "observation_records": self._records,
                    "persistent_journal": False, "permissions_granted": False}

    def final_summary(self):
        """One bounded final receipt after close, even when ordinary output fills.

        Repeated reads return the same bytes' projection and consume no budget.
        It does not assert broker acceptance, cancel an order or clear UNKNOWN.
        """
        _require(self._closed, "close_before_final_summary")
        with self._budget_lock:
            if self._final_json is None:
                result = {"status": "UNKNOWN_PRESENT" if self._unknown_seen or self._cleanup_failed else "TRANSPORT_CLOSED",
                    "profile_id": self._value["id"], "local_action_counts": dict(self._counts),
                    "wire_bytes_conservative": self._wire, "ordinary_output_bytes": self._output,
                    "cleanup_confirmed": not self._cleanup_failed, "automatic_retry": False,
                    "economic_acceptance": "NOT_INFERRED", "persistent_journal": False,
                    "permissions_granted": False}
                encoded = _json(result)
                _require(len(encoded) <= self._bounds["reserved_final_output_bytes"], "final_summary_contract_exceeded")
                self._final_json = encoded
                self._output += len(encoded)
            return json.loads(self._final_json)
