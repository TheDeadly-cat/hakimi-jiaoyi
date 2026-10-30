"""Account-wide reservation and dispatch-intent journal; this module never sends.

The coordinator supplies an application-wide root, independently checked facts,
and a short control barrier. Workspace identity is audit data, not a partition.
Receipts are facts about local recording, NEVER authorizations or dispatch permits.
No router, credential reader, SDK, socket factory, or automatic recovery is here.
Synthetic records have a separate permanent namespace from external records.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat

from . import terminal_broker_execution_plan as contract

SCHEMA = "hakimi-broker-execution-journal-v2"
DOMAINS = frozenset({"SYNTHETIC_TEST", "EXTERNAL_RECORD"})
MAX_EVENTS, MAX_BYTES = 1000, 16 * 1024 * 1024
PERMISSIONS = dict(contract.PERMISSIONS)
ZERO = "0" * 64
TERMINAL = frozenset({"FILLED", "CANCELLED", "REJECTED"})


class JournalError(ValueError):
    pass


def require(value, reason):
    if not value:
        raise JournalError(reason)


def raw(value):
    return contract.canonical_bytes(value)


def seal(value):
    return {**value, "id": contract.digest(value)}


def money(value):
    return contract._money(value, allow_zero=True)


def request(value):
    require(type(value) is str and contract.candidate.REQUEST.fullmatch(value), "journal_request_id_invalid")
    return value


def _profile(value):
    from .terminal_broker_wire_profile import VerifiedWireProfile
    require(type(value) is VerifiedWireProfile, "verified_wire_profile_required")
    return value.as_dict()


def _position_key(owner, security):
    contract._hash(owner); contract._text(security)
    return contract.digest({"owner_scope_id": owner, "security_id": security})


def _fresh(profile, at):
    now = contract._time(at)
    require(contract._time(profile["created_at"]) <= now < contract._time(profile["wire_bounds"]["valid_until"]),
            "journal_profile_expired_or_clock_invalid")


def _financial(state):
    snapshot = state["snapshot"]
    if snapshot is None:
        return {"cash_available_after_local_liabilities": None, "cash_reserved": "0", "owner_positions": {},
                "reconciliation_required": bool(state["reasons"]), "reasons": sorted(state["reasons"])}
    cash, reserved = money(snapshot["cash_available"]), Decimal(0)
    holdings = {key: {"quantity": value["quantity"], "reserved": 0} for key, value in snapshot["positions"].items()}
    reasons = set(state["reasons"])
    for claim in state["claims"].values():
        if claim["epoch"] != state["epoch"]:
            continue
        order = claim["order"]
        qty, filled = order["quantity"], claim["filled_quantity"]
        price, fees = money(order["limit_price"]), money(claim["fees"] or "0")
        ceiling = money(claim["fee_ceiling"])
        terminal = claim["order_state"] in TERMINAL
        outstanding = 0 if terminal else max(0, qty - filled)
        fee_reserve = Decimal(0) if terminal and claim["fees_final"] else max(Decimal(0), ceiling - fees)
        reserved += fee_reserve
        cash -= fees
        key = _position_key(claim["owner_scope_id"], order["security_id"])
        held = holdings.setdefault(key, {"quantity": 0, "reserved": 0})
        if order["side"] == "BUY":
            cash -= money(claim["filled_notional"])
            reserved += outstanding * price
            held["quantity"] += filled
        else:
            # Sale proceeds are not buying power until an explicit new account
            # reconciliation. Observing an order is not a new cash snapshot.
            held["quantity"] -= filled
            held["reserved"] += outstanding
        if filled > qty or fees > ceiling:
            reasons.add("ORDER_OR_FEE_LIMIT_EXCEEDED")
        if filled and ((order["side"] == "BUY" and money(claim["filled_notional"]) > filled * price)
                       or (order["side"] == "SELL" and money(claim["filled_notional"]) < filled * price)):
            reasons.add("OBSERVED_FILL_OUTSIDE_LIMIT_PRICE")
    remaining = cash - reserved
    if remaining < 0:
        reasons.add("CASH_BELOW_LOCAL_LIABILITIES")
    if any(row["quantity"] < row["reserved"] for row in holdings.values()):
        reasons.add("OWNER_HOLDINGS_BELOW_RESERVATIONS")
    return {"cash_available_after_local_liabilities": format(remaining, "f"), "cash_reserved": format(reserved, "f"),
            "owner_positions": holdings, "reconciliation_required": bool(reasons), "reasons": sorted(reasons)}


def _state():
    return {"epoch": 0, "snapshot": None, "profiles": {}, "claims": {}, "actions": {}, "observations": {},
            "snapshot_evidence": {}, "reasons": set(), "last_account_fact_at": None, "last_event_at": None}


class BrokerExecutionJournal:
    """Trusted coordinator primitive. Constructing or reading creates no store.

    `shared_root` must be supplied by the application service, never a workspace
    selector or renderer. A production root factory and authorization gate are
    intentionally not exposed by this offline slice.
    """
    def __init__(self, shared_root, *, mode, account_id, record_domain, clock=None):
        require(mode in contract.MODE_CONTRACTS and record_domain in DOMAINS, "journal_scope_invalid")
        require(type(account_id) is str and account_id.isascii() and account_id.isdecimal()
                and account_id[0] != "0" and 0 < int(account_id) < 2**64, "journal_explicit_account_required")
        self.scope = {"provider": "FUTU", "mode": mode, "account_id": account_id}
        self.account_scope_id = contract.digest(self.scope)
        self.domain, self.mode = record_domain, mode
        self.root = Path(shared_root).absolute() / "broker-execution-v2"
        self._safe(self.root)
        self.root = self.root.resolve()
        self.path = self.root / record_domain / self.account_scope_id / "journal.sqlite3"
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.closed = False

    def _safe(self, path):
        require(path == self.root or path.is_relative_to(self.root), "journal_path_outside_root")
        for part in (path, *path.parents):
            if os.path.lexists(part):
                info = part.lstat()
                require(not stat.S_ISLNK(info.st_mode) and not getattr(info, "st_file_attributes", 0) & 0x400,
                        "journal_reparse_path_rejected")

    def _meta(self):
        return seal({"schema_version": SCHEMA, "account": self.scope, "account_scope_id": self.account_scope_id,
                     "record_domain": self.domain, "permissions": PERMISSIONS})

    def _create(self):
        self._safe(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_name(".journal-" + secrets.token_hex(8) + ".pending")
        connection = sqlite3.connect(str(temp))
        try:
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("CREATE TABLE metadata(singleton INTEGER PRIMARY KEY CHECK(singleton=1), body BLOB NOT NULL, head_seq INTEGER NOT NULL, head_hash TEXT NOT NULL)")
            connection.execute("CREATE TABLE events(seq INTEGER PRIMARY KEY, request_id TEXT UNIQUE NOT NULL, body BLOB NOT NULL)")
            connection.execute("INSERT INTO metadata VALUES(1,?,0,?)", (raw(self._meta()), ZERO))
            connection.commit()
        finally:
            connection.close()
        try:
            try:
                os.link(temp, self.path)
            except FileExistsError:
                pass
        finally:
            temp.unlink(missing_ok=True)

    def _check_file(self):
        self._safe(self.path)
        info = self.path.lstat()
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "journal_regular_unaliased_store_required")
        for suffix in ("-wal", "-shm"):
            require(not os.path.lexists(str(self.path) + suffix), "journal_wal_unsupported")
        require(not os.path.lexists(str(self.path) + "-journal"), "journal_rollback_pending_or_writer_busy")
        with self.path.open("rb") as stream:
            opened = os.fstat(stream.fileno())
            require((opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino), "journal_file_replaced")
            header = stream.read(100)
        require(header[:16] == b"SQLite format 3\x00" and header[18:20] == b"\x01\x01", "journal_delete_mode_required")

    @contextmanager
    def _database(self, write=False):
        require(not self.closed, "journal_closed")
        self._safe(self.path)
        if not self.path.exists():
            if not write:
                yield None
                return
            self._create()
        self._check_file()
        connection = sqlite3.connect(str(self.path) if write else self.path.as_uri() + "?mode=ro",
                                     uri=not write, isolation_level=None, timeout=2)
        try:
            if write:
                connection.execute("PRAGMA synchronous=FULL")
            connection.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield connection
        finally:
            if connection.in_transaction:
                connection.rollback()
            connection.close()

    def _load(self, connection):
        state, receipts, previous = _state(), {}, ZERO
        if connection is None:
            return state, receipts, previous
        metadata = connection.execute("SELECT singleton,body,head_seq,head_hash FROM metadata").fetchall()
        require(len(metadata) == 1 and metadata[0][:2] == (1, raw(self._meta())), "journal_metadata_mismatch")
        count, size = connection.execute("SELECT COUNT(*),COALESCE(SUM(LENGTH(body)),0) FROM events").fetchone()
        require(count <= MAX_EVENTS and size <= MAX_BYTES, "journal_capacity_exceeded")
        for index, row in enumerate(connection.execute("SELECT seq,request_id,body FROM events ORDER BY seq"), 1):
            seq, request_id, blob = row
            value = contract._json_document(blob, contract.MAX_DOCUMENT_BYTES)
            require(raw(value) == blob and value.get("id") == contract.digest({k: v for k, v in value.items() if k != "id"}), "journal_event_changed")
            require(seq == index == value["seq"] and value["previous"] == previous and value["request_id"] == request_id,
                    "journal_chain_changed")
            require(value["schema_version"] == SCHEMA and value["request_hash"] ==
                    contract.digest({"kind": value["kind"], "payload": value["payload"]}), "journal_request_identity_changed")
            require(state["last_event_at"] is None or contract._time(value["at"]) >= contract._time(state["last_event_at"]),
                    "journal_clock_regressed")
            result = self._reduce(state, value["kind"], value["payload"], value["at"], previous)
            require(raw(result) == raw(value["result"]), "journal_result_changed")
            if value["kind"] in {"CLAIM", "OUTCOME", "LATE_OUTCOME", "OBSERVATION", "REJECTED_FEE_EVIDENCE"}:
                state["last_account_fact_at"] = value["at"]
            state["last_event_at"] = value["at"]
            receipts[request_id], previous = value, value["id"]
        require((count, previous) == metadata[0][2:], "journal_head_changed")
        return state, receipts, previous

    def _admit_profile(self, state, profile, at):
        require(profile.get("schema_version") == "hakimi-broker-wire-profile-v2"
                and profile.get("id") == contract.digest({k: v for k, v in profile.items() if k != "id"}), "journal_profile_identity_invalid")
        require(profile["mode"] == self.mode and profile["order"]["account_id"] == self.scope["account_id"]
                and profile["deduplication"]["account_scope_id"] == self.account_scope_id, "journal_account_mode_mismatch")
        require(profile["permissions"] == PERMISSIONS, "journal_profile_does_not_grant_authority")
        if self.domain == "EXTERNAL_RECORD":
            require(not profile["research_eligibility"]["offline_only"], "synthetic_profile_cannot_enter_external_journal")
            require(profile["protocol_policy"]["production_transport_available"] is True,
                    "offline_codec_profile_cannot_enter_external_journal")
        _fresh(profile, at)
        if profile["id"] in state["profiles"]:
            require(state["profiles"][profile["id"]] == profile, "journal_profile_rebinding")
        else:
            state["profiles"][profile["id"]] = deepcopy(profile)

    def _reduce(self, state, kind, payload, at, previous):
        now = contract._time(at)
        if kind == "SNAPSHOT":
            require(payload["expected_head"] == previous, "journal_snapshot_head_changed")
            for claim in state["claims"].values():
                require(claim["order_state"] in TERMINAL and claim["fees_final"], "journal_unresolved_claim_blocks_rebase")
            reasons = _financial(state)["reasons"]
            resolution = payload["reconciliation"]
            if reasons:
                require(type(resolution) is dict, "journal_explicit_conflict_reconciliation_required")
                contract._fields(resolution, {"evidence_id", "reviewed_event_head", "reviewed_reasons", "reviewed_observation_ids"})
                contract._hash(resolution["evidence_id"])
                require(resolution["reviewed_event_head"] == previous and resolution["reviewed_reasons"] == reasons
                        and resolution["reviewed_observation_ids"] == sorted(state["observations"]),
                        "journal_conflict_review_scope_changed")
            else:
                require(resolution is None, "journal_unnecessary_conflict_resolution")
            snapshot = deepcopy(payload["snapshot"])
            contract._fields(snapshot, {"evidence_id", "query_started_at", "observed_at", "valid_until", "covered_head", "cash_available", "positions"})
            contract._hash(snapshot["evidence_id"]); money(snapshot["cash_available"])
            require(snapshot["evidence_id"] not in state["snapshot_evidence"], "journal_snapshot_evidence_already_used")
            observed, expiry = contract._time(snapshot["observed_at"]), contract._time(snapshot["valid_until"])
            started = contract._time(snapshot["query_started_at"])
            require(snapshot["covered_head"] == previous and started <= observed <= now < expiry
                    and 0 < (expiry - started).total_seconds() <= 60, "journal_snapshot_freshness_invalid")
            require(state["last_account_fact_at"] is None or started >= contract._time(state["last_account_fact_at"]),
                    "journal_snapshot_predates_recorded_account_facts")
            require(type(snapshot["positions"]) is list and len(snapshot["positions"]) <= 1000, "journal_owner_positions_invalid")
            positions = {}
            for row in snapshot["positions"]:
                contract._fields(row, {"owner_scope_id", "security_id", "quantity"})
                contract._integer(row["quantity"], 0, 10**9)
                key = _position_key(row["owner_scope_id"], row["security_id"])
                require(key not in positions, "journal_duplicate_owner_position")
                positions[key] = deepcopy(row)
            snapshot["positions"] = positions
            state["snapshot_evidence"][snapshot["evidence_id"]] = contract.digest(payload["snapshot"])
            state["snapshot"], state["epoch"], state["reasons"] = snapshot, state["epoch"] + 1, set()
            return {"status": "SNAPSHOT_RECORDED", "epoch": state["epoch"], "evidence_id": snapshot["evidence_id"]}
        if kind in ("CLAIM", "ACTION"):
            profile = payload["profile"]
            self._admit_profile(state, profile, at)
            intent = profile["deduplication"]["intent_scope_id"]
            if kind == "CLAIM":
                contract._hash(payload["authorization_id"])
                require(intent not in state["claims"], "journal_original_intent_already_claimed")
                snapshot = state["snapshot"]
                require(snapshot is not None and snapshot["evidence_id"] == payload["evidence_id"], "journal_cash_evidence_required")
                require(now < contract._time(snapshot["valid_until"]) and
                        (now - contract._time(snapshot["observed_at"])).total_seconds() <= profile["wire_bounds"]["max_evidence_age_seconds"],
                        "journal_account_evidence_stale")
                require(profile["wire_bounds"]["actions"]["trade_submit"] == 1, "journal_submit_budget_required")
                require(not _financial(state)["reconciliation_required"], "journal_reconciliation_required")
                claim = {"profile_id": profile["id"], "base_plan_id": profile["base_plan_id"], "intent_scope_id": intent,
                         "workspace_context": profile["workspace_context"], "owner_scope_id": profile["research"]["owner_scope_id"],
                         "order": deepcopy(profile["order"]), "fee_ceiling": profile["wire_bounds"]["max_total_fees"],
                         "epoch": state["epoch"], "authorization_id": payload["authorization_id"], "evidence_id": payload["evidence_id"],
                         "state": "CLAIMED_RESERVED", "order_state": "OPEN", "broker_order_id": None,
                         "filled_quantity": 0, "filled_notional": "0", "fees": None, "fees_final": False,
                         "submit_started": False, "cancel_acknowledged": False}
                state["claims"][intent] = claim
                require(not _financial(state)["reconciliation_required"], "journal_shared_cash_or_owner_holdings_insufficient")
                return {"status": "CLAIMED_RESERVED", "intent_scope_id": intent}
            action = payload["action"]
            require(action in profile["wire_bounds"]["actions"], "journal_action_unknown")
            contract._hash(payload["authorization_id"])
            frame = payload["frame_sha256"]
            if action in ("quote_connect", "trade_connect"):
                require(frame is None and type(payload["frame_bytes"]) is int and payload["frame_bytes"] == 0,
                        "journal_connect_has_no_frame")
            else:
                contract._hash(frame)
                contract._integer(payload["frame_bytes"], 45, profile["wire_bounds"]["max_frame_bytes"])
            count = sum(item["profile_id"] == profile["id"] and item["action"] == action for item in state["actions"].values())
            require(count < profile["wire_bounds"]["actions"][action], "journal_action_budget_exhausted")
            claim = state["claims"].get(intent)
            if action == "trade_submit":
                require(claim is not None and claim["profile_id"] == profile["id"] and not claim["submit_started"], "journal_unique_reserved_submit_required")
                require(claim["authorization_id"] == payload["authorization_id"], "journal_submit_authorization_reference_changed")
                require(not _financial(state)["reconciliation_required"], "journal_reconciliation_required")
                snapshot = state["snapshot"]
                require(snapshot is not None and now < contract._time(snapshot["valid_until"]) and
                        (now - contract._time(snapshot["observed_at"])).total_seconds() <= profile["wire_bounds"]["max_evidence_age_seconds"],
                        "journal_account_evidence_stale_before_dispatch")
                claim["submit_started"], claim["state"] = True, "DISPATCH_INTENT"
            elif action in ("trade_observe", "trade_cancel", "trade_fees"):
                require(claim is not None and claim["profile_id"] == profile["id"] and claim["broker_order_id"] is not None,
                        "journal_exact_original_broker_order_required")
                require(payload["broker_order_id"] == claim["broker_order_id"], "journal_broker_order_mismatch")
            state["actions"][payload["operation_id"]] = {"profile_id": profile["id"], "intent_scope_id": intent, "action": action,
                "frame_sha256": frame, "frame_bytes": payload["frame_bytes"], "authorization_id": payload["authorization_id"],
                "state": "DISPATCH_INTENT", "outcome": None}
            return {"status": "DISPATCH_INTENT", "operation_id": payload["operation_id"], "action": action,
                    "attempt_count": count + 1, "dispatch_authorization_granted": False}
        if kind in ("OUTCOME", "LATE_OUTCOME"):
            operation = state["actions"].get(payload["operation_id"])
            require(operation is not None, "journal_original_pending_action_required")
            if kind == "LATE_OUTCOME":
                prior = operation["outcome"]
                require(prior is not None and prior["status"] == "UNKNOWN"
                        and prior["evidence_id"] == payload["previous_evidence_id"]
                        and operation["frame_sha256"] == payload["original_frame_sha256"],
                        "journal_original_unknown_dispatch_required")
                require(payload["outcome"]["status"] in ("ACKNOWLEDGED", "EXPLICIT_REJECTED")
                        and payload["outcome"]["frame_bytes"] == prior["frame_bytes"],
                        "journal_late_complete_response_required")
            else:
                require(operation["outcome"] is None, "journal_original_pending_action_required")
            result = payload["outcome"]
            contract._fields(result, {"status", "evidence_id", "sent_bytes", "possible_sent_bytes", "frame_bytes",
                                     "broker_order_id", "write_attempted", "response_complete"})
            require(result["status"] in ("CONNECTED", "ACKNOWLEDGED", "EXPLICIT_REJECTED", "UNKNOWN", "NOT_DISPATCHED"), "journal_outcome_invalid")
            contract._hash(result["evidence_id"])
            require(type(result["write_attempted"]) is bool and type(result["response_complete"]) is bool,
                    "journal_outcome_presence_required")
            contract._integer(result["frame_bytes"], 0, 65536); contract._integer(result["sent_bytes"], 0, result["frame_bytes"])
            require(result["frame_bytes"] == operation["frame_bytes"], "journal_original_frame_length_changed")
            contract._integer(result["possible_sent_bytes"], result["sent_bytes"], result["frame_bytes"])
            require(result["possible_sent_bytes"] == 0 or result["write_attempted"], "journal_write_evidence_invalid")
            if result["status"] == "NOT_DISPATCHED":
                require(result["possible_sent_bytes"] == 0 and not result["write_attempted"], "journal_partial_send_is_unknown")
            if result["status"] == "CONNECTED":
                require(operation["action"] in ("quote_connect", "trade_connect") and result["frame_bytes"] == 0
                        and result["sent_bytes"] == 0 and not result["write_attempted"] and not result["response_complete"],
                        "journal_connection_is_not_rpc_ack")
            if result["status"] in ("ACKNOWLEDGED", "EXPLICIT_REJECTED"):
                # A matched complete broker response can resolve an uncertain
                # write without fabricating a locally observed send count.
                require(result["frame_bytes"] > 0 and result["possible_sent_bytes"] == result["frame_bytes"]
                        and result["write_attempted"] and result["response_complete"], "journal_complete_dispatch_required")
            broker_id = result["broker_order_id"]
            if broker_id is not None:
                # Pinned Futu uses the opaque orderIDEx string. Its obsolete
                # numeric orderID field is not the order ownership identity.
                require(type(broker_id) is str and 1 <= len(broker_id) <= 128 and broker_id.isascii()
                        and all(32 < ord(char) < 127 for char in broker_id), "journal_exact_broker_order_id_required")
            claim = state["claims"].get(operation["intent_scope_id"])
            if operation["action"] == "trade_submit":
                require(claim is not None and claim["submit_started"], "journal_submit_claim_missing")
                if result["status"] == "ACKNOWLEDGED":
                    require(broker_id is not None, "journal_ack_order_id_required")
                    require(not any(other is not claim and other["broker_order_id"] == broker_id for other in state["claims"].values()), "journal_broker_order_already_owned")
                    claim["broker_order_id"] = broker_id
                else:
                    require(broker_id is None, "journal_non_ack_order_id_unproven")
                claim["state"] = result["status"]
                if result["status"] in ("EXPLICIT_REJECTED", "NOT_DISPATCHED"):
                    claim["order_state"] = "REJECTED"
                    # A local outcome does not establish the actual fee total.
                if result["status"] == "NOT_DISPATCHED":
                    claim["fees"], claim["fees_final"] = "0", True
            elif operation["action"] == "trade_cancel" and result["status"] == "ACKNOWLEDGED":
                require(claim is not None and broker_id == claim["broker_order_id"], "journal_cancel_ack_order_mismatch")
                claim["cancel_acknowledged"] = True
            operation.setdefault("outcome_history", []).append(deepcopy(result))
            operation["state"], operation["outcome"] = result["status"], deepcopy(result)
            return {"status": "LATE_OUTCOME_RECORDED" if kind == "LATE_OUTCOME" else "OUTCOME_RECORDED",
                    "operation_id": payload["operation_id"], "outcome_status": result["status"]}
        if kind == "REJECTED_FEE_EVIDENCE":
            claim = state["claims"].get(payload["intent_scope_id"])
            require(claim is not None and claim["state"] == "EXPLICIT_REJECTED" and claim["broker_order_id"] is None,
                    "journal_explicit_rejection_required")
            contract._hash(payload["evidence_id"]); money(payload["fees"])
            require(claim["fees"] is None, "journal_rejected_fee_evidence_already_recorded")
            claim["fees"], claim["fees_final"] = payload["fees"], True
            return {"status": "REJECTED_FEES_RECORDED", "intent_scope_id": payload["intent_scope_id"], "evidence_id": payload["evidence_id"]}
        if kind == "OBSERVATION":
            intent = payload["intent_scope_id"]
            claim = state["claims"].get(intent)
            require(claim is not None and claim["submit_started"] and claim["broker_order_id"] is not None, "journal_original_acknowledged_order_required")
            observed = payload["observation"]
            contract._fields(observed, {"evidence_id", "broker_order_id", "filled_quantity", "filled_notional", "fees", "fees_final", "order_state"})
            identity = contract._hash(observed["evidence_id"])
            require(observed["broker_order_id"] == claim["broker_order_id"], "journal_observation_order_mismatch")
            contract._integer(observed["filled_quantity"], 0, 10**9); money(observed["filled_notional"])
            require(type(observed["fees_final"]) is bool and observed["order_state"] in TERMINAL | {"OPEN"}, "journal_observation_state_invalid")
            if observed["fees"] is not None:
                money(observed["fees"])
            require(not observed["fees_final"] or observed["fees"] is not None, "journal_final_fees_missing")
            if identity in state["observations"]:
                require(state["observations"][identity] == payload, "journal_observation_identity_conflict")
                return {"status": "DUPLICATE_OBSERVATION", "evidence_id": identity}
            state["observations"][identity] = deepcopy(payload)
            qty, old_qty = observed["filled_quantity"], claim["filled_quantity"]
            amount, old_amount = money(observed["filled_notional"]), money(claim["filled_notional"])
            previous_fees, previous_state = claim["fees"], claim["order_state"]
            bad = (qty < old_qty or amount < old_amount or (qty == 0) != (amount == 0)
                   or observed["order_state"] == "FILLED" and qty != claim["order"]["quantity"]
                   or observed["order_state"] == "REJECTED" and qty > 0
                   or claim["fees"] is not None and observed["fees"] is not None and money(observed["fees"]) < money(claim["fees"]))
            if bad:
                state["reasons"].add("CONFLICTING_CUMULATIVE_OBSERVATION")
                return {"status": "OBSERVATION_CONFLICT_RETAINED", "evidence_id": identity}
            changed_economics = qty != old_qty or amount != old_amount or (observed["fees"] is not None and observed["fees"] != previous_fees)
            changed_terminal = previous_state in TERMINAL and observed["order_state"] in TERMINAL and previous_state != observed["order_state"]
            if changed_terminal and not changed_economics:
                state["reasons"].add("CONFLICTING_TERMINAL_OBSERVATION")
                return {"status": "OBSERVATION_CONFLICT_RETAINED", "evidence_id": identity}
            if previous_state in TERMINAL and changed_economics:
                state["reasons"].add("LATE_ECONOMIC_CHANGE_AFTER_TERMINAL")
            changed_after_rebase = claim["epoch"] != state["epoch"] and changed_economics
            if changed_after_rebase:
                state["reasons"].add("LATE_OBSERVATION_AFTER_ACCOUNT_REBASE")
            claim["filled_quantity"], claim["filled_notional"] = qty, observed["filled_notional"]
            if observed["fees"] is not None:
                claim["fees"] = observed["fees"]
            claim["fees_final"] = observed["fees_final"] or (claim["fees_final"] and not changed_economics)
            # A stale OPEN row cannot revive a terminal order or its permission.
            if claim["order_state"] not in TERMINAL or observed["order_state"] in TERMINAL:
                claim["order_state"] = observed["order_state"]
            claim["state"] = "OBSERVED_" + claim["order_state"]
            return {"status": "OBSERVATION_RECORDED", "evidence_id": identity,
                    "reconciliation_required": _financial(state)["reconciliation_required"]}
        raise JournalError("journal_event_kind_unknown")

    def _commit(self, connection):
        connection.commit()

    def _write(self, kind, payload, request_id, barrier=None):
        request(request_id)
        payload = json.loads(raw(payload))
        fingerprint = contract.digest({"kind": kind, "payload": payload})
        with self._database(write=True) as connection:
            state, receipts, previous = self._load(connection)
            if request_id in receipts:
                found = receipts[request_id]
                require(found["request_hash"] == fingerprint, "journal_request_payload_conflict")
                return {"receipt": deepcopy(found), "replayed": True, "permissions": dict(PERMISSIONS)}
            require(len(receipts) < MAX_EVENTS, "journal_event_limit")
            def publish():
                # Take the time after any writer/control wait, at publication.
                at = contract._now(self._clock()).isoformat()
                require(state["last_event_at"] is None or contract._time(at) >= contract._time(state["last_event_at"]),
                        "journal_clock_regressed")
                result = self._reduce(state, kind, payload, at, previous)
                event = seal({"schema_version": SCHEMA, "seq": len(receipts) + 1, "previous": previous, "at": at,
                              "kind": kind, "payload": payload, "request_id": request_id, "request_hash": fingerprint, "result": result})
                blob = raw(event)
                total = connection.execute("SELECT COALESCE(SUM(LENGTH(body)),0) FROM events").fetchone()[0]
                require(total + len(blob) <= MAX_BYTES, "journal_byte_limit")
                connection.execute("INSERT INTO events VALUES(?,?,?)", (event["seq"], request_id, blob))
                connection.execute("UPDATE metadata SET head_seq=?,head_hash=? WHERE singleton=1", (event["seq"], event["id"]))
                self._commit(connection)
                return {"receipt": event, "replayed": False, "permissions": dict(PERMISSIONS)}
            if kind in ("CLAIM", "ACTION"):
                require(callable(barrier), "journal_short_control_barrier_required")
                profile = payload["profile"]
                with barrier() as current:
                    require(current == profile["control"], "journal_control_changed_or_stopped")
                    return publish()
            return publish()

    def snapshot(self, snapshot, *, expected_head, request_id, reconciliation=None):
        """Explicit coordinator reconciliation, only after all claims settle.

        The evidence ID references independently checked cash/owner allocation;
        this API does not verify broker provenance or infer owners from totals.
        """
        contract._hash(expected_head)
        return self._write("SNAPSHOT", {"snapshot": snapshot, "expected_head": expected_head, "reconciliation": reconciliation}, request_id)

    def claim(self, profile, *, evidence_id, authorization_id, request_id, control_barrier):
        return self._write("CLAIM", {"profile": _profile(profile), "evidence_id": evidence_id,
                                   "authorization_id": authorization_id}, request_id, control_barrier)

    def begin_action(self, profile, action, *, request_id, frame_sha256, frame_bytes, authorization_id, control_barrier, broker_order_id=None):
        return self._write("ACTION", {"profile": _profile(profile), "action": action, "operation_id": request_id,
            "frame_sha256": frame_sha256, "frame_bytes": frame_bytes, "authorization_id": authorization_id,
            "broker_order_id": broker_order_id}, request_id, control_barrier)

    def outcome(self, operation_id, outcome, *, request_id):
        return self._write("OUTCOME", {"operation_id": request(operation_id), "outcome": outcome}, request_id)

    def late_outcome(self, operation_id, outcome, *, previous_evidence_id, original_frame_sha256, request_id):
        contract._hash(previous_evidence_id); contract._hash(original_frame_sha256)
        return self._write("LATE_OUTCOME", {"operation_id": request(operation_id), "outcome": outcome,
            "previous_evidence_id": previous_evidence_id, "original_frame_sha256": original_frame_sha256}, request_id)

    def observe(self, intent_scope_id, observation, *, request_id):
        contract._hash(intent_scope_id)
        return self._write("OBSERVATION", {"intent_scope_id": intent_scope_id, "observation": observation}, request_id)

    def rejected_fee_evidence(self, intent_scope_id, *, evidence_id, fees, request_id):
        contract._hash(intent_scope_id)
        return self._write("REJECTED_FEE_EVIDENCE", {"intent_scope_id": intent_scope_id, "evidence_id": evidence_id, "fees": fees}, request_id)

    def read(self, request_id=None):
        if request_id is not None:
            request(request_id)
        with self._database() as connection:
            state, receipts, head = self._load(connection)
        return {"schema_version": SCHEMA, "account_scope_id": self.account_scope_id, "record_domain": self.domain,
                "head": head, "event_count": len(receipts), "epoch": state["epoch"], "financial": _financial(state),
                "claims": deepcopy(state["claims"]), "actions": deepcopy(state["actions"]),
                "observation_ids": sorted(state["observations"]),
                "receipt": deepcopy(receipts.get(request_id)) if request_id else None,
                "read_only": True, "automatic_resume": False, "permissions": dict(PERMISSIONS)}

    def close(self):
        self.closed = True
