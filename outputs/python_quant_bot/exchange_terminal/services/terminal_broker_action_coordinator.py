"""One durable action -> bounded transport -> retained facts, default denied.

Trusted backend assembly only: there is no HTTP route or socket implementation.
The current admission factory admits SYNTHETIC_TEST dependencies only. A future
production authority needs its own verified factory and production wire profile;
neither a saved plan, renderer flag nor this test permit grants that authority.
"""
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
from threading import Lock
import time

from . import terminal_broker_execution_plan as contract
from .terminal_broker_account_control import SharedBrokerRoot, _anchor
from .terminal_broker_execution_journal import request as request_id
from .terminal_broker_response_facts import supported_actions_for_profile, verify_response_facts
from .terminal_broker_scoped_transport import ScopedTransport
from .terminal_broker_wire_profile import (
    VerifiedWireProfile, WIRE_ACTIONS_V3, SCHEMA as PROFILE_SCHEMA,
    SCHEMA_V3 as PROFILE_SCHEMA_V3, actions_for_profile,
)
from .terminal_broker_submit_observation import VerifiedSubmitObservation, validate_submit_observation
from .terminal_broker_order_identity import VerifiedAcknowledgedOrder, validate_acknowledged_order
from .terminal_workspace_history import _no_links, _safe


SCHEMA = "hakimi-broker-action-coordinator-v1"
_ORDER_FOLLOWUPS = frozenset({"trade_observe", "trade_cancel", "trade_fees"})
_TOKEN = object()


class CoordinatorError(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise CoordinatorError(reason)


class SystemClock:
    monotonic = staticmethod(time.monotonic)

    @staticmethod
    def utcnow():
        return datetime.now(timezone.utc)


@dataclass(frozen=True, slots=True, init=False)
class ActionPermit:
    _data: bytes

    def __init__(self, data, token):
        _require(token is _TOKEN, "trusted_authority_factory_required")
        object.__setattr__(self, "_data", data)

    def as_dict(self):
        return json.loads(self._data)


def synthetic_test_permit(*, shared_root, profile, operation_id, action, frame,
                          local_revision, account_revision, issued_at, expires_at):
    """Explicit test dependency; unavailable for EXTERNAL_RECORD host roots.

    The typed host root comes from the host, never a renderer-selected directory.
    Permission fields remain false and the grant is labelled synthetic throughout.
    """
    return _synthetic_permit(shared_root=shared_root, profile=profile, operation_id=operation_id,
        action=action, frame=frame, local_revision=local_revision, account_revision=account_revision,
        issued_at=issued_at, expires_at=expires_at, profile_schema=PROFILE_SCHEMA)


def synthetic_test_permit_v3(*, shared_root, profile, operation_id, action, frame,
                             local_revision, account_revision, issued_at, expires_at,
                             submit_observation=None, session_binding=None):
    """Distinct synthetic v3 admission; submit cannot omit its original observations."""
    return _synthetic_permit(shared_root=shared_root, profile=profile, operation_id=operation_id,
        action=action, frame=frame, local_revision=local_revision, account_revision=account_revision,
        issued_at=issued_at, expires_at=expires_at, profile_schema=PROFILE_SCHEMA_V3,
        submit_observation=submit_observation, session_binding=session_binding)


def _synthetic_permit(*, shared_root, profile, operation_id, action, frame, local_revision,
                      account_revision, issued_at, expires_at, profile_schema,
                      submit_observation=None, session_binding=None):
    _require(type(shared_root) is SharedBrokerRoot and shared_root.domain == "SYNTHETIC_TEST",
             "synthetic_host_root_required")
    _anchor(shared_root)
    _require(type(profile) is VerifiedWireProfile, "typed_profile_required")
    value = profile.as_dict()
    _require(value["schema_version"] == profile_schema, "permit_profile_version_mismatch")
    _require(value["research_eligibility"]["offline_only"] and
             value["protocol_policy"]["production_transport_available"] is False,
             "synthetic_offline_profile_required")
    request_id(operation_id)
    _require(action in actions_for_profile(value) and type(frame) is bytes, "bounded_operation_required")
    for revision in (local_revision, account_revision):
        _require(type(revision) is int and revision >= 0, "control_revision_required")
    start, end = contract._time(issued_at), contract._time(expires_at)
    _require(contract._time(value["created_at"]) <= start < end <=
             contract._time(value["wire_bounds"]["valid_until"]), "permit_time_outside_profile")
    body = dict(schema_version="hakimi-scoped-action-permit-v1", admission="SYNTHETIC_TEST_DEPENDENCY",
        record_domain=shared_root.domain, shared_root=str(shared_root.path), profile_id=value["id"],
        account_scope_id=value["deduplication"]["account_scope_id"],
        intent_scope_id=value["deduplication"]["intent_scope_id"], mode=value["mode"],
        operation_id=operation_id, action=action,
        frame_sha256=sha256(frame).hexdigest() if frame else None, frame_bytes=len(frame),
        local_revision=local_revision, account_revision=account_revision,
        issued_at=start.isoformat(), expires_at=end.isoformat(), permissions=dict(contract.PERMISSIONS))
    if profile_schema == PROFILE_SCHEMA_V3:
        body.update(schema_version="hakimi-scoped-action-permit-v2",
            admission="SYNTHETIC_REQUIRED_OBSERVATIONS_V1", submit_observation_id=None)
        if action == "trade_submit":
            _require(type(submit_observation) is VerifiedSubmitObservation, "submit_observation_required")
            validate_submit_observation(profile, submit_observation, session_binding=session_binding, now=start)
            body["submit_observation_id"] = submit_observation.as_dict()["id"]
        else:
            _require(submit_observation is None and session_binding is None,
                     "observation_not_applicable_to_operation")
    return ActionPermit(contract.canonical_bytes(dict(body, id=contract.digest(body))), _TOKEN)


@dataclass(frozen=True, slots=True)
class BoundOperation:
    """Created by trusted code after any required handshake; not request JSON."""
    operation_id: str
    action: str
    frame: bytes = b""
    permit: ActionPermit | None = None
    broker_order_id: str | None = None
    cash_evidence_id: str | None = None
    submit_observation: VerifiedSubmitObservation | None = None

    def __post_init__(self):
        request_id(self.operation_id)
        _require(type(self.action) is str and self.action in WIRE_ACTIONS_V3 and type(self.frame) is bytes,
                 "bound_operation_invalid")
        connect = self.action in {"quote_connect", "trade_connect"}
        _require((connect and not self.frame) or (not connect and 44 < len(self.frame) <= 65536),
                 "operation_frame_invalid")
        _require(self.permit is None or type(self.permit) is ActionPermit, "typed_permit_required")
        if self.cash_evidence_id is not None:
            contract._hash(self.cash_evidence_id)
        _require(self.submit_observation is None or (self.action == "trade_submit"
            and type(self.submit_observation) is VerifiedSubmitObservation), "typed_submit_observation_required")


class _EvidenceSink:
    """Private, bounded raw evidence; no second business ledger or resume logic."""
    def __init__(self, owner):
        self.owner, self.records = owner, []
        self.bytes = 0

    def write(self, record):
        active = self.owner._active
        _require(active is not None and type(record) is bytes, "unbound_transport_evidence")
        metadata, separator, raw = record.partition(b"\n")
        header = json.loads(metadata)
        _require(separator and header["raw_bytes"] == len(raw), "transport_evidence_length_changed")
        _require(self.bytes + len(record) <= self.owner.value["wire_bounds"]["max_output_bytes"],
                 "coordinator_evidence_budget_exceeded")
        name = f"frame-{len(self.records) + 1:04d}.bin"
        self.owner._write_evidence(name, record)
        self.records.append(dict(operation_id=active.operation_id, file=name,
            sha256=sha256(record).hexdigest(), bytes=len(record), header=header, raw=raw))
        self.bytes += len(record)

    def response(self, operation):
        self.verify(operation)
        matches = [r for r in self.records if r["operation_id"] == operation.operation_id
                   and r["header"]["kind"] == "response_frame"
                   and r["header"].get("action") == operation.action]
        _require(len(matches) == 1, "one_retained_original_response_required")
        return matches[0]["raw"]

    def verify(self, operation):
        for row in self.records:
            if row["operation_id"] == operation.operation_id:
                raw = self.owner._read_evidence(row["file"])
                _require(len(raw) == row["bytes"] and sha256(raw).hexdigest() == row["sha256"],
                         "retained_transport_evidence_changed")


class _DispatchGate:
    def __init__(self, owner):
        self.owner, self.offset = owner, 0

    @contextmanager
    def barrier(self, context, permit):
        owner, operation = self.owner, self.owner._active
        _require(operation is not None and permit is operation.permit, "active_operation_required")
        owner._validate_permit(operation)
        channel = owner._actions[operation.action][0]
        _require(context["profile_id"] == owner.value["id"] and context["action"] == operation.action
            and context["channel"] == channel and context["mode"] == owner.value["mode"]
            and context["account_scope_id"] == owner.journal.account_scope_id
            and context["intent_scope_id"] == owner.value["deduplication"]["intent_scope_id"]
            and context["frame_sha256"] == (sha256(operation.frame).hexdigest() if operation.frame else None)
            and context["total_bytes"] == len(operation.frame) and context["offset"] == self.offset,
            "actual_write_scope_changed")
        # No journal reads or pipe waits inside these barriers: lock order is
        # journal writer -> local -> shared account. Actual IO begins here in
        # this same process, and is required to be nonblocking by transport.
        with owner._barrier(operation) as current:
            _require(current == owner.value["control"], "original_control_changed")
            owner._validate_permit(operation)
            yield

    before_connect = barrier
    before_write = barrier

    def after_write(self, context, permit, written):
        _require(context["offset"] == self.offset and type(written) is int and written > 0,
                 "write_progress_invalid")
        self.offset += written


class ActionCoordinator:
    """Trusted, single-operation-at-a-time assembly of existing real contracts.

    No queue, automatic restart, provider lookup, user-selected root or default
    connection exists. Registering operations is a trusted backend step; a
    worker message can select an already bound ID but cannot supply new bytes.
    """
    def __init__(self, *, service, profile, codec, evidence_directory, operations=(),
                 connection_factory=None, clock=None):
        from .terminal_research import TerminalResearchService
        _require(type(service) is TerminalResearchService and type(profile) is VerifiedWireProfile,
                 "trusted_service_and_profile_required")
        self.service, self.profile, self.value, self.codec = service, profile, profile.as_dict(), codec
        self._actions = actions_for_profile(self.value)
        self.clock, self.factory = clock or SystemClock(), connection_factory
        self.config_id = self.value["candidate_config"]["id"]
        self.journal = service.broker_execution_journal(mode=self.value["mode"], config_id=self.config_id)
        self.journal._clock = self.clock.utcnow
        _require(self.journal.account_scope_id == self.value["deduplication"]["account_scope_id"],
                 "coordinator_account_scope_changed")
        self._evidence = _no_links(Path(evidence_directory).absolute()).resolve()
        self._evidence_parent = self._evidence.parent
        _require(self._evidence_parent.is_dir() and not self._evidence.exists(), "fresh_evidence_directory_required")
        info = self._evidence_parent.stat()
        self._parent_identity = (info.st_dev, info.st_ino)
        self._directory_identity = None
        self._evidence_bytes = 0
        self._final = None
        self._operations = {}
        self._lock = Lock()
        self._transport = self._active = None
        self._sink, self._gate = _EvidenceSink(self), _DispatchGate(self)
        self._connected, self._initialized = set(), set()
        self._closed = False
        self._last_clock = None
        self._order_identity = None
        for operation in operations:
            self.register(operation)

    def register(self, operation):
        _require(type(operation) is BoundOperation and not self._closed, "trusted_bound_operation_required")
        _require(operation.action in self._actions, "operation_profile_version_mismatch")
        if self.value["schema_version"] == PROFILE_SCHEMA:
            _require(operation.submit_observation is None, "v2_observation_not_applicable")
        _require(operation.operation_id not in self._operations and len(self._operations) < 50,
                 "operation_already_bound_or_capacity")
        self._operations[operation.operation_id] = operation

    def _operation(self, identity):
        request_id(identity)
        _require(identity in self._operations, "operation_not_prebound")
        return self._operations[identity]

    @contextmanager
    def _barrier(self, operation):
        self._validate_permit(operation)
        permit = operation.permit.as_dict()
        with self.service.broker_dispatch_barrier(mode=self.value["mode"], config_id=self.config_id,
                local_revision=permit["local_revision"], account_revision=permit["account_revision"]) as current:
            self._validate_permit(operation)
            yield current

    def _validate_permit(self, operation):
        _require(type(operation.permit) is ActionPermit, "AUTHORIZATION_REQUIRED")
        permit = operation.permit.as_dict()
        _require(permit["id"] == contract.digest({k: v for k, v in permit.items() if k != "id"}),
                 "permit_identity_changed")
        # Current production admission remains unavailable. This is a versioned
        # admission boundary, not an interpretation of false permission flags.
        v3 = self.value["schema_version"] == PROFILE_SCHEMA_V3
        expected_admission = "SYNTHETIC_REQUIRED_OBSERVATIONS_V1" if v3 else "SYNTHETIC_TEST_DEPENDENCY"
        expected_schema = "hakimi-scoped-action-permit-v2" if v3 else "hakimi-scoped-action-permit-v1"
        _require(self.journal.domain == "SYNTHETIC_TEST" and permit["admission"] == expected_admission
            and permit["schema_version"] == expected_schema
            and permit["record_domain"] == self.journal.domain
            and self.value["research_eligibility"]["offline_only"]
            and self.value["protocol_policy"]["production_transport_available"] is False,
            "PRODUCTION_ADMISSION_UNAVAILABLE")
        _require(permit["shared_root"] == str(self.service._broker_control_root.path)
            and permit["profile_id"] == self.value["id"] and permit["mode"] == self.value["mode"]
            and permit["account_scope_id"] == self.journal.account_scope_id
            and permit["intent_scope_id"] == self.value["deduplication"]["intent_scope_id"]
            and permit["operation_id"] == operation.operation_id and permit["action"] == operation.action
            and permit["frame_sha256"] == (sha256(operation.frame).hexdigest() if operation.frame else None)
            and permit["frame_bytes"] == len(operation.frame) and permit["permissions"] == contract.PERMISSIONS,
            "permit_scope_changed")
        now = contract._now(self.clock.utcnow())
        previous_clock = self._last_clock
        if v3:
            # Remember denied future observations too: a clock correction must
            # not resurrect a bundle already seen beyond its expiry.
            self._last_clock = max(now, previous_clock) if previous_clock is not None else now
        _require(contract._time(permit["issued_at"]) <= now < contract._time(permit["expires_at"])
            and (previous_clock is None or now >= previous_clock), "permit_expired_or_clock_regressed")
        self._last_clock = now
        if v3:
            if operation.action == "trade_submit":
                _require(type(operation.submit_observation) is VerifiedSubmitObservation,
                         "submit_observation_required")
                _require(permit.get("submit_observation_id") == operation.submit_observation.as_dict()["id"],
                         "permit_observation_binding_changed")
                validate_submit_observation(self.profile, operation.submit_observation,
                    session_binding=self._submit_session(), now=now)
            else:
                _require(permit.get("submit_observation_id") is None and operation.submit_observation is None,
                         "observation_not_applicable_to_operation")
                if operation.action in _ORDER_FOLLOWUPS:
                    self._validate_order_identity(operation)

    def _validate_order_identity(self, operation, identity=None):
        """Pure check inside write barriers; never reopen the journal here."""
        identity = self._order_identity if identity is None else identity
        accepted = self.codec.acknowledged_order_identity()
        _require(type(identity) is VerifiedAcknowledgedOrder and type(accepted) is VerifiedAcknowledgedOrder,
                 "journal_acknowledged_order_required")
        _require(identity.as_dict() == accepted.as_dict(), "accepted_order_identity_changed")
        validate_acknowledged_order(self.profile, identity, session_binding=self._order_session())
        _require(operation.broker_order_id == identity.as_dict()["broker_order_id"],
                 "operation_original_order_changed")

    def _confirm_order_identity(self, operation):
        """Re-read persisted ownership before admission, outside stop barriers."""
        identity = self.journal.read_acknowledged_order(self.profile)
        _require(type(identity) is VerifiedAcknowledgedOrder, "journal_acknowledged_order_required")
        self._validate_order_identity(operation, identity)
        self._order_identity = identity

    def _order_session(self):
        # Managing an acknowledged order needs the original accepted identity
        # and a live trade channel, not a still-live quote channel. New submits
        # continue to require both live channels in _submit_session below.
        _require("trade" in self._initialized and "trade" in self._connected,
                 "current_trade_handshake_required")
        quote = self.codec.accepted_session_binding("quote")
        trade = self.codec.accepted_session_binding("trade")
        _require(quote.as_dict() == trade.as_dict(), "accepted_session_changed")
        return trade

    def _submit_session(self):
        _require({"quote", "trade"} <= self._initialized and {"quote", "trade"} <= self._connected,
                 "both_current_handshakes_required")
        quote = self.codec.accepted_session_binding("quote")
        trade = self.codec.accepted_session_binding("trade")
        _require(quote.as_dict() == trade.as_dict(), "accepted_session_changed")
        return quote

    def _expected_payload(self, operation):
        _require(type(operation.permit) is ActionPermit, "AUTHORIZATION_REQUIRED")
        payload = dict(profile=self.value, action=operation.action, operation_id=operation.operation_id,
            frame_sha256=sha256(operation.frame).hexdigest() if operation.frame else None,
            frame_bytes=len(operation.frame), authorization_id=operation.permit.as_dict()["id"],
            broker_order_id=operation.broker_order_id)
        if self.value["schema_version"] == PROFILE_SCHEMA_V3 and operation.action == "trade_submit":
            _require(type(operation.submit_observation) is VerifiedSubmitObservation,
                     "submit_observation_required")
            payload["submit_observation"] = operation.submit_observation.as_dict()
        return payload

    def read(self, operation_id):
        operation = self._operation(operation_id)
        view = self.journal.read(operation_id)
        receipt = view["receipt"]
        if receipt is not None:
            _require(receipt["kind"] == "ACTION" and receipt["payload"] == self._expected_payload(operation),
                     "original_operation_binding_changed")
        state = view["actions"].get(operation_id)
        return dict(schema_version=SCHEMA, operation_id=operation_id,
            status=(state["state"] if state and state["outcome"] else "UNKNOWN") if receipt else "NOT_RECORDED",
            original_action_receipt=receipt, action_state=state,
            response_facts=[v for v in view["response_facts"].values() if v["request_id"] == operation_id],
            read_only=True, automatic_retry=False, economic_acceptance="NOT_INFERRED",
            record_domain=self.journal.domain, permissions=dict(contract.PERMISSIONS))

    def _evidence_path(self, name, *, create=False):
        _no_links(self._evidence_parent)
        info = self._evidence_parent.stat()
        _require((info.st_dev, info.st_ino) == self._parent_identity, "evidence_parent_changed")
        if self._directory_identity is None:
            _require(create, "evidence_directory_not_created")
            self._evidence.mkdir()
            info = self._evidence.stat()
            self._directory_identity = (info.st_dev, info.st_ino)
        _no_links(self._evidence)
        info = self._evidence.stat()
        _require((info.st_dev, info.st_ino) == self._directory_identity, "evidence_directory_changed")
        return _safe(self._evidence, self._evidence / name)

    def _write_evidence(self, name, raw, *, final=False):
        bounds = self.value["wire_bounds"]
        maximum = bounds["max_output_bytes"] - (0 if final else bounds["reserved_final_output_bytes"])
        _require(type(raw) is bytes and self._evidence_bytes + len(raw) <= maximum
            and (not final or len(raw) <= bounds["reserved_final_output_bytes"]),
            "coordinator_evidence_budget_exceeded")
        # Reserve the full offered size even when a write/fsync reply is lost.
        self._evidence_bytes += len(raw)
        target = self._evidence_path(name, create=True)
        with target.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())

    def _read_evidence(self, name):
        path = self._evidence_path(name)
        info = path.lstat()
        _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and
                 info.st_size <= self.value["wire_bounds"]["max_output_bytes"], "plain_bounded_evidence_required")
        with path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            _require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino), "evidence_file_replaced")
            return stream.read(self.value["wire_bounds"]["max_output_bytes"] + 1)

    def execute(self, operation_id):
        _require(self._lock.acquire(blocking=False), "operation_busy_no_queue")
        try:
            operation = self._operation(operation_id)
            prior = self.read(operation_id)
            if prior["original_action_receipt"] is not None:
                return dict(prior, recovered_original=True)
            _require(not self._closed, "coordinator_closed")
            if self.value["schema_version"] == PROFILE_SCHEMA_V3 and operation.action in _ORDER_FOLLOWUPS:
                self._confirm_order_identity(operation)
            self._validate_permit(operation)
            _require(callable(self.factory), "CONNECTION_FACTORY_UNAVAILABLE")
            channel = self._actions[operation.action][0]
            if operation.frame:
                _require(channel in self._connected, "NO_ACTIVE_CONNECTION_NO_RESTART")
                _require(operation.action.endswith("_init") or channel in self._initialized,
                         "HANDSHAKE_REQUIRED")
                self.codec.validate_request(self.profile, operation.action, operation.frame)
            # Resolve the exact originals again before committing a new action.
            saved, intent = self.service._broker().read_plan_records(self.value["mode"], self.config_id,
                self.value["candidate_intent"]["id"])
            _require(saved == self.value["candidate_config"] and intent == self.value["candidate_intent"],
                     "original_candidate_changed")
            try:
                observation_arguments = {}
                if self.value["schema_version"] == PROFILE_SCHEMA_V3 and operation.action == "trade_submit":
                    observation_arguments = dict(submit_observation=operation.submit_observation,
                        session_binding=self._submit_session())
                if operation.action == "trade_submit":
                    contract._hash(operation.cash_evidence_id)
                    claim_id = "claim-" + sha256(operation_id.encode()).hexdigest()
                    claim = self.journal.claim(self.profile, evidence_id=operation.cash_evidence_id,
                        authorization_id=operation.permit.as_dict()["id"], request_id=claim_id,
                        control_barrier=lambda: self._barrier(operation), **observation_arguments)
                    if claim["replayed"]:
                        return dict(self.read(operation_id), status="UNKNOWN", reason="PRIOR_CLAIM_NO_AUTOMATIC_RESUME")
                expected = self._expected_payload(operation)
                action = self.journal.begin_action(self.profile, operation.action, request_id=operation_id,
                    frame_sha256=expected["frame_sha256"], frame_bytes=expected["frame_bytes"],
                    authorization_id=expected["authorization_id"], broker_order_id=operation.broker_order_id,
                    control_barrier=lambda: self._barrier(operation), **observation_arguments)
            except Exception as error:
                # A failed reply is not proof of rollback, and even a recovered
                # commit must never cause this invocation to begin transport.
                return dict(self.read(operation_id), status="UNKNOWN", reason="JOURNAL_ADMISSION_UNCONFIRMED",
                            diagnostic=type(error).__name__)
            if action["replayed"]:
                return dict(self.read(operation_id), recovered_original=True)
            self._active, self._gate.offset = operation, 0
            try:
                if self._transport is None:
                    self._transport = ScopedTransport(self.profile, factory=self.factory, clock=self.clock,
                        gate=self._gate, sink=self._sink, codec=self.codec)
                deadline = self.clock.monotonic() + self.value["wire_bounds"]["wall_timeout_seconds"]
                outcome = (self._transport.exchange(channel, operation.action, operation.frame, operation.permit, deadline)
                           if operation.frame else self._transport.connect(channel, operation.permit, deadline))
                if outcome.status == "CONNECTED_NOT_INITIALIZED":
                    self._connected.add(channel)
                elif outcome.status == "RESPONSE_RECEIVED" and operation.action.endswith("_init"):
                    self._initialized.add(channel)
                elif outcome.status in {"UNKNOWN", "NOT_WRITTEN"}:
                    self._connected.discard(channel); self._initialized.discard(channel)
                self._sink.verify(operation)
                record = dict(schema_version=SCHEMA, operation_id=operation_id,
                    action_receipt_id=action["receipt"]["id"], raw_outcome=asdict(outcome),
                    chunks=[{k: v for k, v in row.items() if k not in {"raw", "header"}}
                            for row in self._sink.records if row["operation_id"] == operation_id])
                raw = contract.canonical_bytes(record)
                evidence_id = sha256(raw).hexdigest()
                self._write_evidence("outcome-" + evidence_id + ".json", raw)
                status = ("CONNECTED" if outcome.status == "CONNECTED_NOT_INITIALIZED" else
                          "NOT_DISPATCHED" if outcome.status == "NOT_WRITTEN" else "UNKNOWN")
                observed = dict(status=status, evidence_id=evidence_id, sent_bytes=outcome.bytes_written,
                    possible_sent_bytes=outcome.possible_bytes_written, frame_bytes=len(operation.frame),
                    broker_order_id=None, write_attempted=bool(operation.frame) and outcome.status != "NOT_WRITTEN",
                    response_complete=outcome.status == "RESPONSE_RECEIVED")
                self.journal.outcome(operation_id, observed, request_id="outcome-" + sha256(operation_id.encode()).hexdigest())
                if outcome.status == "RESPONSE_RECEIVED" and operation.action in supported_actions_for_profile(self.value):
                    facts = verify_response_facts(profile=self.profile, codec=self.codec,
                        action_receipt=action["receipt"], expected_action_receipt_id=action["receipt"]["id"],
                        request_frame=operation.frame, response_frame=self._sink.response(operation),
                        received_at=self.clock.utcnow())
                    matched_ack = facts.as_dict()["status"] in {"ACK_SCOPE_MATCHED", "CANCEL_ACK_NOT_TERMINAL"}
                    self.journal.record_verified_response(facts,
                        request_id="facts-" + sha256(operation_id.encode()).hexdigest(),
                        previous_evidence_id=evidence_id if matched_ack else None)
                    if self.value["schema_version"] == PROFILE_SCHEMA_V3 and operation.action == "trade_submit" and matched_ack:
                        # Only a complete original journal readback can supply
                        # the identity. A received frame or failed save reply
                        # must never enable follow-up request construction.
                        identity = self.journal.read_acknowledged_order(self.profile)
                        _require(type(identity) is VerifiedAcknowledgedOrder, "journal_acknowledged_order_required")
                        _require(identity.as_dict()["submit_operation_id"] == operation_id
                            and identity.as_dict()["ack_facts_id"] == facts.as_dict()["id"],
                            "recorded_order_ack_changed")
                        self.codec.accept_acknowledged_order(self.profile, identity)
                        self._order_identity = identity
                return dict(self.read(operation_id), raw_evidence_id=evidence_id)
            except Exception as error:
                # Retained ACTION and any already committed outcome stay as-is.
                # Never infer NOT_DISPATCHED from a worker/evidence/codec error.
                self._connected.discard(channel); self._initialized.discard(channel)
                return dict(self.read(operation_id), status="UNKNOWN", reason="ACTION_COMPLETION_UNCONFIRMED",
                            diagnostic=type(error).__name__)
            finally:
                self._active = None
        finally:
            self._lock.release()

    def close(self):
        _require(self._lock.acquire(blocking=False), "operation_busy_use_worker_stop")
        try:
            if self._final is not None:
                return json.loads(self._final)
            self._closed = True
            self._connected.clear(); self._initialized.clear()
            if self._transport is not None:
                result = self._transport.close(self.clock.monotonic() + self.value["wire_bounds"]["cleanup_timeout_seconds"])
                result = dict(result, transport_summary=self._transport.final_summary(),
                              ordinary_evidence_bytes=self._evidence_bytes)
                raw = contract.canonical_bytes(result)
                self._write_evidence("coordinator-final.json", raw, final=True)
                self._final = raw
                return json.loads(raw)
            return dict(closed=True, cleanup_confirmed=True, business_action=None, automatic_retry=False)
        finally:
            self._lock.release()
