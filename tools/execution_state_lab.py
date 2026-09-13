"""Credential-free execution state lab; independent of the research package.

Only the local SQLite simulator can be driven by this CLI. This is neither a
broker adapter nor an official paper account. No price matching or backtest
engine is implemented here: fills are explicit simulated venue observations.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from decimal import Decimal, localcontext
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys
import time
import uuid

APP_ID = 0x48454C31
VENUE_APP_ID = 0x48455631
MODE = "LOCAL_SIMULATOR"
CLOSED = {"FILLED", "CANCELLED", "REJECTED", "EXPIRED", "REJECTED_LOCAL"}
BROKER_STATES = {"WORKING", "PARTIAL", "FILLED", "CANCELLED", "REJECTED", "EXPIRED"}
OBS_FIELDS = {"evidence_id", "client_id", "broker_order_id", "symbol", "side", "quantity",
              "limit_price", "state", "cumulative_quantity", "cumulative_notional", "cumulative_fee"}


class StateError(ValueError):
    pass


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def fingerprint(value):
    return hashlib.sha256(encoded(value).encode("ascii")).hexdigest()


def text(value):
    if type(value) is not str or not re.fullmatch(r"[A-Za-z0-9:._-]{1,96}", value):
        raise StateError("invalid_identifier")
    return value


def amount(value, *, signed=False):
    pattern = r"-?(?:0|[1-9][0-9]{0,20})(?:\.[0-9]{1,8})?" if signed else r"(?:0|[1-9][0-9]{0,20})(?:\.[0-9]{1,8})?"
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise StateError("exact_decimal_string_required")
    return Decimal(value)


def formatted(value):
    if value == 0:
        return "0"
    result = format(value, "f")
    return (result.rstrip("0").rstrip(".") if "." in result else result) or "0"


def quantity(value, *, zero=False):
    if type(value) is not int or not (0 if zero else 1) <= value <= 1_000_000_000:
        raise StateError("whole_share_quantity_required")
    return value


def positions(value):
    if type(value) is not dict:
        raise StateError("positions_object_required")
    checked = {text(key): quantity(number, zero=True) for key, number in value.items()}
    return {key: number for key, number in checked.items() if number}


def connect_existing(path, app_id):
    path = Path(path).resolve(strict=True)
    # Inspect before any writable connection or PRAGMA. Never adopt another DB.
    check = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        if check.execute("PRAGMA application_id").fetchone()[0] != app_id:
            raise StateError("foreign_database_refused")
        if check.execute("PRAGMA user_version").fetchone()[0] != 1:
            raise StateError("unsupported_database_version")
        if check.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise StateError("database_integrity_failed")
    finally:
        check.close()
    db = sqlite3.connect(path, isolation_level=None, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA synchronous=FULL")
    return db


def create_database(path, app_id, schema, seed_statements):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb"):
        pass
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.executescript("BEGIN IMMEDIATE;" + schema)
        for sql, parameters in seed_statements:
            db.execute(sql, parameters)
        db.execute(f"PRAGMA application_id={app_id}")
        db.execute("PRAGMA user_version=1")
        db.execute("COMMIT")
    finally:
        db.close()


@contextmanager
def transaction(db):
    with localcontext() as precision:
        precision.prec = 60
        db.execute("BEGIN IMMEDIATE")
        try:
            yield db
            db.execute("COMMIT")
        except BaseException:
            db.execute("ROLLBACK")
            raise


class ExecutionStore:
    """At most one submission attempt per intent; uncertainty always reconciles."""
    mode = MODE
    application_id = APP_ID
    reconciliation_scope = "ALL_LAB_ORDERS_BALANCES_POSITIONS"
    rule_authority = "LAB_DECLARATION_NOT_BROKER_RULES"
    allow_untradable_seed_positions = False

    def __init__(self, path):
        self.db = connect_existing(path, self.application_id)
        self.config = json.loads(self.db.execute("SELECT config FROM meta").fetchone()[0])
        if self.config["mode"] != self.mode:
            self.db.close()
            raise StateError("local_simulator_mode_required")
        # A previous process's successful query never authorizes this process.
        self._ready = None
        self._query = None

    @classmethod
    def create(cls, path, *, cash, holdings, symbols, max_order_notional="1000", fee_reserve="1"):
        cash = formatted(amount(cash))
        holdings = positions(holdings)
        if type(symbols) is not dict or not symbols:
            raise StateError("explicit_instrument_rules_required")
        rules = {}
        for symbol, tick in symbols.items():
            tick = amount(tick)
            if tick <= 0:
                raise StateError("positive_tick_required")
            rules[text(symbol)] = formatted(tick)
        if ((not cls.allow_untradable_seed_positions and not set(holdings) <= set(rules))
                or amount(max_order_notional) <= 0):
            raise StateError("invalid_lab_seed_or_limit")
        amount(fee_reserve)
        config = {"mode": cls.mode, "currency": "USD", "seed_cash": cash, "seed_positions": holdings,
                  "symbols": rules, "max_order_notional": max_order_notional, "fee_reserve": fee_reserve,
                  "rule_authority": cls.rule_authority}
        create_database(path, cls.application_id, """
            CREATE TABLE meta(config TEXT NOT NULL, stop_reason TEXT, query_token TEXT);
            CREATE TABLE orders(intent_id TEXT PRIMARY KEY, client_id TEXT UNIQUE NOT NULL,
                payload TEXT NOT NULL, state TEXT NOT NULL, claim_id TEXT, broker_id TEXT UNIQUE,
                cancel_state TEXT NOT NULL DEFAULT 'NONE', cancel_id TEXT,
                filled INTEGER NOT NULL DEFAULT 0, notional TEXT NOT NULL DEFAULT '0', fee TEXT NOT NULL DEFAULT '0');
            CREATE TABLE observations(evidence_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL);
            CREATE TABLE events(sequence INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL);
        """, [("INSERT INTO meta(config) VALUES(?)", (encoded(config),)),
              ("INSERT INTO events(kind,payload) VALUES('CREATED',?)", (encoded(config),))])
        return cls(path)

    def close(self):
        self.db.close()

    def _event(self, kind, payload):
        return self.db.execute("INSERT INTO events(kind,payload) VALUES(?,?)", (kind, encoded(payload))).lastrowid

    def _revision(self):
        return self.db.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]

    def _row(self, intent_id):
        row = self.db.execute("SELECT * FROM orders WHERE intent_id=?", (intent_id,)).fetchone()
        if row is None:
            raise StateError("intent_not_found")
        return row

    def _halt(self, reason, evidence=None):
        self.db.execute("UPDATE meta SET stop_reason=?", (text(reason),))
        try:
            evidence_hash = fingerprint(evidence) if evidence is not None else None
        except (TypeError, ValueError):
            evidence_hash = None
        self._event("RISK_STOP", {"reason": reason, "rejected_evidence_sha256": evidence_hash})
        self._ready = None

    def stop(self, reason):
        with transaction(self.db):
            self._halt(reason)

    def _balances(self):
        cash, held = amount(self.config["seed_cash"]), dict(self.config["seed_positions"])
        reserved_cash, reserved_shares = Decimal(0), {}
        unresolved = []
        for row in self.db.execute("SELECT * FROM orders"):
            order = json.loads(row["payload"])
            side, symbol = order["side"], order["symbol"]
            sign = 1 if side == "BUY" else -1
            held[symbol] = held.get(symbol, 0) + sign * row["filled"]
            cash -= sign * amount(row["notional"]) + amount(row["fee"])
            if row["state"] == "SUBMIT_UNKNOWN" or row["cancel_state"] in {"UNKNOWN", "ACK_RECEIVED"}:
                unresolved.append(row["intent_id"])
            if row["state"] not in CLOSED | {"PREPARED"}:
                remaining = order["quantity"] - row["filled"]
                if side == "BUY":
                    reserved_cash += remaining * amount(order["limit_price"]) + max(Decimal(0), amount(self.config["fee_reserve"]) - amount(row["fee"]))
                else:
                    reserved_shares[symbol] = reserved_shares.get(symbol, 0) + remaining
        return cash, {key: value for key, value in held.items() if value}, reserved_cash, reserved_shares, unresolved

    def inspect(self):
        with transaction(self.db):
            cash, held, reserved, shares, unresolved = self._balances()
            return {"mode": self.mode, "cash": formatted(cash), "positions": held,
                    "reserved_cash": formatted(reserved), "reserved_sell_quantities": shares,
                    "unresolved_intents": unresolved, "stop_reason": self.db.execute("SELECT stop_reason FROM meta").fetchone()[0],
                    "orders": [dict(row) for row in self.db.execute("SELECT * FROM orders ORDER BY intent_id")],
                    "revision": self._revision(), "official_simulator_verified": False,
                    "broker_calls_allowed": False, "real_funds_allowed": False}

    def prepare(self, intent_id, *, symbol, side, quantity_value, limit_price):
        text(intent_id)
        if symbol not in self.config["symbols"] or side not in {"BUY", "SELL"}:
            raise StateError("unsupported_instrument_or_side")
        price = amount(limit_price)
        with localcontext() as precision:
            precision.prec = 60
            if price <= 0 or price % amount(self.config["symbols"][symbol]) != 0:
                raise StateError("price_tick_mismatch")
        payload = {"symbol": symbol, "side": side, "quantity": quantity(quantity_value), "limit_price": formatted(price)}
        client_id = fingerprint({"intent_id": intent_id, "payload": payload})[:32]
        with transaction(self.db):
            old = self.db.execute("SELECT * FROM orders WHERE intent_id=?", (intent_id,)).fetchone()
            if old:
                if old["payload"] != encoded(payload):
                    raise StateError("intent_id_conflict")
                return old["client_id"]
            self.db.execute("INSERT INTO orders(intent_id,client_id,payload,state) VALUES(?,?,?,'PREPARED')",
                            (intent_id, client_id, encoded(payload)))
            self._event("PREPARED", {"intent_id": intent_id, "client_id": client_id, "order": payload})
        return client_id

    def _require_fresh(self):
        if self._ready is None or self._ready[0] != self._revision() or time.monotonic() - self._ready[1] > 5:
            raise StateError("fresh_reconciliation_required")

    def claim_submit(self, intent_id):
        with transaction(self.db):
            row = self._row(intent_id)
            if row["state"] != "PREPARED":
                return None  # never retry a submitted/unknown intent
            self._require_fresh()
            order = json.loads(row["payload"])
            cash, held, reserved, shares, unresolved = self._balances()
            if unresolved:
                raise StateError("unresolved_external_outcome")
            if order["side"] == "BUY" and self.db.execute("SELECT stop_reason FROM meta").fetchone()[0]:
                raise StateError("new_risk_stopped")
            cost = order["quantity"] * amount(order["limit_price"])
            if cost > amount(self.config["max_order_notional"]):
                raise StateError("order_notional_limit")
            if order["side"] == "BUY" and cost + amount(self.config["fee_reserve"]) > cash - reserved:
                raise StateError("cash_reservation_exceeded")
            if order["side"] == "SELL" and order["quantity"] > held.get(order["symbol"], 0) - shares.get(order["symbol"], 0):
                raise StateError("reduce_only_sell_exceeded")
            claim_id = uuid.uuid4().hex
            self.db.execute("UPDATE orders SET state='SUBMIT_UNKNOWN',claim_id=? WHERE intent_id=?", (claim_id, intent_id))
            command = {"mode": self.mode, "operation": "SUBMIT", "intent_id": intent_id,
                       "client_id": row["client_id"], "claim_id": claim_id, **order}
            self._event("SUBMISSION_MAY_REACH_VENUE", command)
            return command  # committed before the caller can send anything

    def reject_submit(self, intent_id, claim_id, rejection_code):
        with transaction(self.db):
            row = self._row(intent_id)
            if row["claim_id"] != claim_id or row["state"] != "SUBMIT_UNKNOWN" or row["broker_id"]:
                raise StateError("definitive_rejection_not_applicable")
            self.db.execute("UPDATE orders SET state='REJECTED' WHERE intent_id=?", (intent_id,))
            self._event("DEFINITIVE_VENUE_REJECTION", {"intent_id": intent_id, "code": text(rejection_code)})

    def begin_cancel(self, intent_id):
        with transaction(self.db):
            row = self._row(intent_id)
            if row["state"] in CLOSED or row["cancel_state"] in {"UNKNOWN", "ACK_RECEIVED"}:
                return None
            if not row["broker_id"]:
                raise StateError("cancel_requires_known_broker_order_id")
            cancel_id = uuid.uuid4().hex
            self.db.execute("UPDATE orders SET cancel_state='UNKNOWN',cancel_id=? WHERE intent_id=?", (cancel_id, intent_id))
            command = {"mode": self.mode, "operation": "CANCEL", "intent_id": intent_id,
                       "broker_order_id": row["broker_id"], "cancel_id": cancel_id}
            self._event("CANCEL_MAY_REACH_VENUE", command)
            return command

    def cancel_response(self, intent_id, cancel_id, accepted):
        if type(accepted) is not bool:
            raise StateError("explicit_cancel_response_required")
        with transaction(self.db):
            row = self._row(intent_id)
            if row["cancel_id"] != cancel_id:
                raise StateError("cancel_response_identity_mismatch")
            if row["state"] in CLOSED:
                return  # terminal fill/cancellation won the race
            if row["cancel_state"] != "UNKNOWN":
                if row["cancel_state"] == ("ACK_RECEIVED" if accepted else "REJECTED"):
                    return
                raise StateError("cancel_response_conflict")
            self.db.execute("UPDATE orders SET cancel_state=? WHERE intent_id=?", ("ACK_RECEIVED" if accepted else "REJECTED", intent_id))
            self._event("CANCEL_RESPONSE_NOT_TERMINAL_STATUS", {"intent_id": intent_id, "accepted": accepted})

    def _apply_observation(self, value):
        if type(value) is not dict or any(type(key) is not str for key in value) or set(value) != OBS_FIELDS:
            raise StateError("observation_fields_invalid")
        if any(type(value[key]) is not str for key in OBS_FIELDS - {"quantity", "cumulative_quantity"}):
            raise StateError("observation_scalar_types_invalid")
        for key in ("evidence_id", "client_id", "broker_order_id", "symbol"):
            text(value[key])
        payload_hash = fingerprint(value)
        seen = self.db.execute("SELECT payload_hash FROM observations WHERE evidence_id=?", (value["evidence_id"],)).fetchone()
        if seen:
            if seen[0] != payload_hash:
                raise StateError("observation_id_conflict")
            return "DUPLICATE"
        row = self.db.execute("SELECT * FROM orders WHERE client_id=?", (value["client_id"],)).fetchone()
        if row is None or row["claim_id"] is None:
            raise StateError("unrecognized_external_order")
        order = json.loads(row["payload"])
        quantity(value["quantity"])
        if any(value[key] != order[key] for key in ("symbol", "side", "quantity")) or amount(value["limit_price"]) != amount(order["limit_price"]):
            raise StateError("external_order_terms_mismatch")
        if row["broker_id"] not in (None, value["broker_order_id"]):
            raise StateError("multiple_broker_orders_for_one_intent")
        other = self.db.execute("SELECT intent_id FROM orders WHERE broker_id=?", (value["broker_order_id"],)).fetchone()
        if other and other[0] != row["intent_id"]:
            raise StateError("broker_id_reused_across_intents")
        filled = quantity(value["cumulative_quantity"], zero=True)
        notional, fee = amount(value["cumulative_notional"]), amount(value["cumulative_fee"])
        state = value["state"]
        if (state not in BROKER_STATES or filled > order["quantity"] or (filled == 0) != (notional == 0)
                or (state == "FILLED") != (filled == order["quantity"])
                or (state == "PARTIAL" and not 0 < filled < order["quantity"])
                or (state in {"WORKING", "REJECTED"} and filled != 0)):
            raise StateError("invalid_cumulative_order_state")
        self.db.execute("INSERT INTO observations VALUES(?,?)", (value["evidence_id"], payload_hash))
        if filled < row["filled"] or (filled == row["filled"] and notional == amount(row["notional"]) and fee < amount(row["fee"])):
            self._event("STALE_OBSERVATION_IGNORED", {"evidence_id": value["evidence_id"], "payload_hash": payload_hash})
            return "STALE"
        delta_qty = filled - row["filled"]
        delta_value, delta_fee = notional - amount(row["notional"]), fee - amount(row["fee"])
        if delta_fee < 0 or (delta_qty == 0 and delta_value != 0) or (delta_qty > 0 and delta_value <= 0):
            raise StateError("cumulative_value_conflict")
        if delta_qty and ((order["side"] == "BUY" and delta_value > delta_qty * amount(order["limit_price"]))
                          or (order["side"] == "SELL" and delta_value < delta_qty * amount(order["limit_price"]))):
            raise StateError("limit_price_execution_conflict")
        if row["state"] in {"REJECTED", "REJECTED_LOCAL"} and filled:
            raise StateError("fill_after_definitive_rejection")
        if row["state"] in CLOSED and state != "FILLED":
            if state in CLOSED and state != row["state"]:
                raise StateError("terminal_state_conflict")
            state = row["state"]  # a late partial callback cannot reopen a terminal order
        cancel_state = ("SUPERSEDED_BY_FILL" if state == "FILLED" else "CONFIRMED") if state in CLOSED and row["cancel_id"] else row["cancel_state"]
        self.db.execute("UPDATE orders SET broker_id=?,state=?,filled=?,notional=?,fee=?,cancel_state=? WHERE intent_id=?",
                        (value["broker_order_id"], state, filled, formatted(notional), formatted(fee), cancel_state, row["intent_id"]))
        self._event("OBSERVATION_APPLIED", {"intent_id": row["intent_id"], "observation": value,
                    "delta_quantity": delta_qty, "delta_notional": formatted(delta_value), "delta_fee": formatted(delta_fee)})
        return "APPLIED"

    def ingest(self, observation):
        error = None
        with transaction(self.db):
            self.db.execute("SAVEPOINT observation")
            try:
                result = self._apply_observation(observation)
                self.db.execute("RELEASE observation")
                cash, held, *_ = self._balances()
                if cash < 0 or any(value < 0 for value in held.values()):
                    self._halt("negative_lab_balance")
                    error = "negative_lab_balance"
            except (StateError, sqlite3.IntegrityError) as exc:
                self.db.execute("ROLLBACK TO observation")
                self.db.execute("RELEASE observation")
                error = str(exc) if isinstance(exc, StateError) else "database_constraint_conflict"
                self._halt(error, observation)
        if error:
            raise StateError(error)
        return result

    def begin_reconcile(self):
        token = uuid.uuid4().hex
        with transaction(self.db):
            self.db.execute("UPDATE meta SET query_token=?", (token,))
            revision = self._event("RECONCILIATION_REQUESTED", {"query_token": token})
        self._ready = None
        self._query = (token, revision, time.monotonic())
        return token

    def complete_reconcile(self, snapshot):
        error = None
        with transaction(self.db):
            if (self._query is None or self._query[1] != self._revision() or time.monotonic() - self._query[2] > 5
                    or self.db.execute("SELECT query_token FROM meta").fetchone()[0] != self._query[0]):
                raise StateError("stale_or_unsolicited_reconciliation")
            if type(snapshot) is dict and snapshot.get("query_token") != self._query[0]:
                raise StateError("stale_or_unsolicited_reconciliation")
            self.db.execute("SAVEPOINT reconcile")
            try:
                if (type(snapshot) is not dict or set(snapshot) != {"mode", "scope", "query_token", "orders", "cash", "positions"}
                        or any(type(snapshot[key]) is not str for key in ("mode", "scope", "query_token", "cash"))
                        or snapshot["mode"] != self.mode or snapshot["scope"] != self.reconciliation_scope
                        or snapshot["query_token"] != self._query[0] or type(snapshot["orders"]) is not list or len(snapshot["orders"]) > 10000):
                    raise StateError("complete_scoped_snapshot_required")
                client_ids = set()
                for value in snapshot["orders"]:
                    if type(value) is not dict or type(value.get("client_id")) is not str or value["client_id"] in client_ids:
                        raise StateError("ambiguous_snapshot_order_identity")
                    client_ids.add(value.get("client_id"))
                    if self._apply_observation(value) == "STALE":
                        raise StateError("stale_order_in_reconciliation")
                    current = self.db.execute("SELECT state FROM orders WHERE client_id=?", (value["client_id"],)).fetchone()[0]
                    if current in CLOSED and value["state"] not in CLOSED:
                        raise StateError("terminal_order_reported_open")
                for row in self.db.execute("SELECT * FROM orders WHERE claim_id IS NOT NULL"):
                    if row["state"] == "REJECTED" and row["broker_id"] is None:
                        continue
                    if row["client_id"] not in client_ids:
                        raise StateError("submission_absence_does_not_prove_rejection")
                cash, held, _, _, unresolved = self._balances()
                if cash != amount(snapshot["cash"], signed=True) or held != positions(snapshot["positions"]):
                    raise StateError("balance_or_position_reconciliation_mismatch")
                if cash < 0 or any(value < 0 for value in held.values()):
                    raise StateError("negative_lab_balance")
                if unresolved:
                    raise StateError("unresolved_external_outcome")
                self.db.execute("RELEASE reconcile")
                self._event("RECONCILED", {"snapshot_sha256": fingerprint(snapshot), "query_token": self._query[0]})
            except (StateError, sqlite3.IntegrityError) as exc:
                self.db.execute("ROLLBACK TO reconcile")
                self.db.execute("RELEASE reconcile")
                error = str(exc) if isinstance(exc, StateError) else "database_constraint_conflict"
                self._halt(error, snapshot)
            self.db.execute("UPDATE meta SET query_token=NULL")
            self._query = None
            if error is None:
                self._ready = (self._revision(), time.monotonic())
        if error:
            raise StateError(error)
        return self.inspect()

    def resume_new_risk(self, reason):
        with transaction(self.db):
            self._require_fresh()
            if self._balances()[-1]:
                raise StateError("unresolved_external_outcome")
            self.db.execute("UPDATE meta SET stop_reason=NULL")
            revision = self._event("EXPLICIT_LAB_RISK_RESUME", {"reason": text(reason)})
            self._ready = (revision, time.monotonic())


class SimulatedVenue:
    """Separate durable mock. It deliberately DOES NOT deduplicate client IDs."""
    def __init__(self, path):
        self.db = connect_existing(path, VENUE_APP_ID)
        self.seed = json.loads(self.db.execute("SELECT seed FROM venue_meta").fetchone()[0])

    @classmethod
    def create(cls, path, *, cash, holdings):
        seed = {"cash": formatted(amount(cash)), "positions": positions(holdings)}
        create_database(path, VENUE_APP_ID,
                        "CREATE TABLE venue_meta(seed TEXT NOT NULL); CREATE TABLE venue_orders(order_id TEXT PRIMARY KEY,payload TEXT NOT NULL);",
                        [("INSERT INTO venue_meta VALUES(?)", (encoded(seed),))])
        return cls(path)

    def close(self):
        self.db.close()

    def submit(self, command, *, lose_response=False):
        if command.get("mode") != MODE or command.get("operation") != "SUBMIT":
            raise StateError("local_simulator_command_required")
        value = {key: command[key] for key in ("client_id", "symbol", "side", "quantity", "limit_price")}
        value.update(evidence_id=uuid.uuid4().hex, broker_order_id="LABO-" + uuid.uuid4().hex,
                     state="WORKING", cumulative_quantity=0, cumulative_notional="0", cumulative_fee="0")
        with transaction(self.db):
            self.db.execute("INSERT INTO venue_orders VALUES(?,?)", (value["broker_order_id"], encoded(value)))
        if lose_response:
            raise TimeoutError("simulated_response_lost_after_acceptance")
        return value

    def update(self, order_id, *, filled, notional, fee, state):
        with transaction(self.db):
            row = self.db.execute("SELECT payload FROM venue_orders WHERE order_id=?", (order_id,)).fetchone()
            if row is None:
                raise StateError("simulator_order_missing")
            value = json.loads(row[0])
            value.update(evidence_id=uuid.uuid4().hex, state=state, cumulative_quantity=filled,
                         cumulative_notional=notional, cumulative_fee=fee)
            self.db.execute("UPDATE venue_orders SET payload=? WHERE order_id=?", (encoded(value), order_id))
            return value  # explicit fixture observation, no invented market matching

    def snapshot(self, query_token):
        with transaction(self.db):
            rows = [json.loads(row[0]) for row in self.db.execute("SELECT payload FROM venue_orders ORDER BY order_id")]
            cash, held = amount(self.seed["cash"]), dict(self.seed["positions"])
            for value in rows:
                sign = 1 if value["side"] == "BUY" else -1
                cash -= sign * amount(value["cumulative_notional"]) + amount(value["cumulative_fee"])
                held[value["symbol"]] = held.get(value["symbol"], 0) + sign * value["cumulative_quantity"]
            return {"mode": MODE, "scope": "ALL_LAB_ORDERS_BALANCES_POSITIONS", "query_token": query_token,
                    "orders": rows, "cash": formatted(cash), "positions": {key: value for key, value in held.items() if value}}


def reconcile(store, venue):
    if type(venue) is not SimulatedVenue:
        raise StateError("local_simulator_required")
    return store.complete_reconcile(venue.snapshot(store.begin_reconcile()))


def submit_once(store, venue, intent_id, *, lose_response=False):
    if type(venue) is not SimulatedVenue:
        raise StateError("local_simulator_required")
    command = store.claim_submit(intent_id)
    if command is None:
        return "ALREADY_ATTEMPTED_NO_SEND"
    try:
        observation = venue.submit(command, lose_response=lose_response)
    except (TimeoutError, ConnectionError):
        return "UNKNOWN_RECONCILE_BEFORE_NEW_RISK"
    store.ingest(observation)
    return "ACKNOWLEDGED"


def demo(output_dir):
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    path, remote = output_dir / "client.sqlite", output_dir / "simulated-venue.sqlite"
    store = ExecutionStore.create(path, cash="1000", holdings={}, symbols={"TEST": "0.01"})
    venue = SimulatedVenue.create(remote, cash="1000", holdings={})
    try:
        store.prepare("example-1", symbol="TEST", side="BUY", quantity_value=10, limit_price="10")
        reconcile(store, venue)
        lost = submit_once(store, venue, "example-1", lose_response=True)
        store.close()
        store = ExecutionStore(path)
        duplicate = submit_once(store, venue, "example-1")
        reconcile(store, venue)
        order_id = store.inspect()["orders"][0]["broker_id"]
        store.ingest(venue.update(order_id, filled=4, notional="39", fee="0.40", state="PARTIAL"))
        cancel = store.begin_cancel("example-1")
        store.cancel_response("example-1", cancel["cancel_id"], True)
        store.ingest(venue.update(order_id, filled=10, notional="98", fee="0.80", state="FILLED"))
        reconcile(store, venue)
        result = {"scope": "LOCAL_DURABLE_EXECUTION_LAB_NOT_OFFICIAL_SIMULATION", "lost_response": lost,
                  "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "restart_duplicate": duplicate, "simulator_submission_count": venue.db.execute("SELECT COUNT(*) FROM venue_orders").fetchone()[0],
                  "state": store.inspect(), "notification_or_broker_calls": False}
        with (output_dir / "result.json").open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result, stream, indent=2, ensure_ascii=True)
            stream.write("\n")
        return result
    finally:
        store.close()
        venue.close()


if __name__ == "__main__":
    def deny_network(event, args):
        if event in {"socket.connect", "socket.connect_ex", "socket.getaddrinfo", "urllib.Request"}:
            raise RuntimeError("execution_lab_network_denied")
    sys.addaudithook(deny_network)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["demo"])
    parser.add_argument("--output-dir", type=Path, required=True)
    options = parser.parse_args()
    print(json.dumps(demo(options.output_dir), indent=2))
