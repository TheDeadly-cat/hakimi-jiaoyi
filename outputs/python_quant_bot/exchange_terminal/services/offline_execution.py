"""Versioned local execution ledger. Only explicit synthetic observations enter it.

The HTTP adapter must verify the saved COMPLETED research reference before
create_plan. This module never opens research files, imports a broker, matches
prices, generates signals, or calls a model. Historical account schemas are not
accepted. All money is an explicit decimal string; this version uses whole shares.
"""
from copy import deepcopy
from decimal import Decimal, InvalidOperation, localcontext
from functools import wraps
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
from threading import RLock


APP_ID = 0x484F4531
SCHEMA = "hakimi-offline-execution-v1"
BINDING_SCHEMA = "hakimi-offline-research-binding-v1"
SNAPSHOT_SCHEMA = "hakimi-offline-reconciliation-v1"
RECEIPT_SCHEMA = "hakimi-offline-execution-receipt-v1"
MAX_ACCOUNT_ORDERS = 1000
MAX_REQUEST_BYTES = 4 * 1024 * 1024
STAGES = ("DRAFT", "BACKTESTED", "SIMULATION", "LIVE_CANDIDATE")
STATES = {"ACCEPTED", "REJECTED", "PARTIAL", "FILLED", "CANCELLED", "TIMEOUT_UNCONFIRMED"}
TERMINAL = {"REJECTED", "FILLED", "CANCELLED"}
PERMISSIONS = {"local_simulation_allowed": True, "paper_order_allowed": False,
               "live_order_allowed": False, "order_allowed": False,
               "broker_connection_allowed": False, "model_calls_allowed": False}


class ExecutionError(ValueError):
    pass


def _json(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _hash(value):
    return sha256(_json(value).encode()).hexdigest()


def _fields(value, required, optional=()):
    if type(value) is not dict or set(required) - value.keys() or value.keys() - set(required) - set(optional):
        raise ExecutionError("execution_fields_invalid")


def _text(value, maximum=160):
    if type(value) is not str or not value.strip() or len(value) > maximum or "\0" in value:
        raise ExecutionError("execution_text_invalid")
    return value


def _integer(value, *, zero=False, maximum=10**12):
    if type(value) is not int or value < (0 if zero else 1) or value > maximum:
        raise ExecutionError("execution_integer_invalid")
    return value


def _money(value, *, positive=False, signed=False):
    if type(value) is not str or not re.fullmatch(r"-?(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,8})?", value):
        raise ExecutionError("execution_decimal_string_required")
    try:
        result = Decimal(value)
    except InvalidOperation as exc:
        raise ExecutionError("execution_decimal_invalid") from exc
    if not result.is_finite() or abs(result) > Decimal("1000000000000000") or (not signed and result < 0) or (positive and result <= 0):
        raise ExecutionError("execution_decimal_out_of_range")
    return result


def _amount(value):
    return format(value, "f")


def _clock(value):
    return _integer(value, maximum=8640000000000000)


def _native_params(value):
    if type(value) is not dict or len(value) > 80:
        raise ExecutionError("execution_parameters_invalid")
    for key, item in value.items():
        _text(key, 80)
        if type(item) not in (str, bool, int, float) or type(item) is str and len(item) > 300:
            raise ExecutionError("execution_parameters_invalid")
    try:
        return json.loads(_json(value))
    except (ValueError, TypeError) as exc:
        raise ExecutionError("execution_parameters_invalid") from exc


def _binding(value):
    required = {"schema_version", "status", "engine_id", "strategy_id", "strategy_params",
                "task_id", "task_version", "input_id", "report_id", "report_hash"}
    _fields(value, required, {"risk", "costs", "source_hash", "security_id"})
    if value["schema_version"] != BINDING_SCHEMA or value["status"] != "COMPLETED":
        raise ExecutionError("verified_completed_research_binding_required")
    for name in ("engine_id", "strategy_id", "task_id", "input_id", "report_id"):
        _text(value[name], 200)
    if "security_id" in value:
        _text(value["security_id"], 200)
    version = value["task_version"]
    _integer(version) if type(version) is int else _text(version)
    for name in ("report_hash", "source_hash"):
        if name in value and (type(value[name]) is not str or not re.fullmatch("[0-9a-f]{64}", value[name])):
            raise ExecutionError("research_binding_hash_required")
    for name in ("strategy_params", "risk", "costs"):
        if name in value:
            _native_params(value[name])
    return deepcopy(value)


def _safe_path(path):
    target = Path(path).absolute()
    for candidate in (target, *target.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise ExecutionError("execution_link_path_rejected")
    return target


def compare_research_context(reference_binding, plan, reference_assumptions=None):
    """Explain explicit context differences, never rank cross-model performance.

    Root adapters supply verified report identities and only assumptions actually
    recorded by that engine. Missing historical fields stay UNKNOWN. Individual
    fills are not aligned by list position, symbol, or approximate timestamp.
    """
    reference = _binding(reference_binding)
    if type(plan) is not dict or "research_binding" not in plan:
        raise ExecutionError("execution_comparison_plan_required")
    bound = _binding(plan["research_binding"])
    assumptions = reference_assumptions if reference_assumptions is not None else {}
    _fields(assumptions, set(), {"fill_model", "quantity_policy", "timing_policy"})
    for value in assumptions.values():
        _text(value, 300)
    def field(name):
        left, right = reference.get(name), bound.get(name)
        return dict(status="UNKNOWN" if left is None or right is None else "MATCH" if left == right else "DIFFERENT",
                    reference=deepcopy(left), execution_plan=deepcopy(right))
    execution = {"fill_model": "EXPLICIT_SYNTHETIC_CUMULATIVE_OBSERVATIONS_NO_PRICE_MATCHING",
                 "quantity_policy": "WHOLE_SHARES_LONG_ONLY", "timing_policy": "EXPLICIT_SIGNAL_AND_EXECUTION_TIMESTAMPS"}
    return dict(schema_version="hakimi-offline-execution-context-comparison-v1",
                status="CONTEXT_ONLY_NOT_RETURN_COMPARISON",
                data={name: field(name) for name in ("security_id", "input_id")},
                # The trusted saved-result resolver supplies the core's code
                # source_identity hash here, not a price-provider digest.
                rules={name: field(name) for name in ("engine_id", "strategy_id", "strategy_params", "risk", "source_hash")},
                costs=field("costs"), saved_report=field("report_hash"),
                execution_assumptions={name: dict(status="UNKNOWN" if name not in assumptions else "MATCH" if assumptions[name] == value else "DIFFERENT",
                                                 reference=assumptions.get(name), execution=value) for name, value in execution.items()},
                economic_event_alignment="UNKNOWN_REQUIRES_EXPLICIT_CAUSAL_MAPPING",
                unexplained_economic_difference="UNKNOWN", numeric_performance_comparison_allowed=False,
                permissions=dict(PERMISSIONS))


def _serialized(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            return function(self, *args, **kwargs)
    return wrapped


def _read_transaction(function):
    @wraps(function)
    def wrapped(self, *args, **kwargs):
        with self._lock:
            self.db.execute("BEGIN")
            try:
                result = function(self, *args, **kwargs)
                self.db.commit()
                return result
            except BaseException:
                self.db.rollback()
                raise
    return wrapped


class OfflineExecutionStore:
    """One authoritative account database; keep one instance per open app account.

    Reopening requires explicit complete synthetic reconciliation before another
    order. Reading or opening never submits, observes, reconciles or resumes.
    """

    @classmethod
    def create(cls, path, *, account_id, initial_cash, securities, rules):
        _text(account_id)
        cash = _money(initial_cash, positive=True)
        if type(securities) is not dict or not securities or len(securities) > 100:
            raise ExecutionError("explicit_synthetic_securities_required")
        for key, security in securities.items():
            _text(key, 80)
            _fields(security, {"symbol", "tick_size"})
            _text(security["symbol"], 40)
            _money(security["tick_size"], positive=True)
        if len({item["symbol"].casefold() for item in securities.values()}) != len(securities):
            raise ExecutionError("security_symbol_aliases_rejected")
        _fields(rules, {"max_order_notional", "max_total_exposure", "max_security_exposure",
                        "cash_floor", "fee_buffer", "max_account_loss", "quote_max_age_ms"})
        for key in set(rules) - {"quote_max_age_ms"}:
            _money(rules[key], positive=key in {"max_order_notional", "max_total_exposure", "max_security_exposure"})
        _integer(rules["quote_max_age_ms"], maximum=86400000)
        config = dict(schema_version=SCHEMA, account_id=account_id, initial_cash=_amount(cash),
                      securities=deepcopy(securities), rules=deepcopy(rules), currency="USD",
                      evidence_kind="SYNTHETIC_TEST", quantity_policy="WHOLE_SHARES_LONG_ONLY",
                      max_orders=MAX_ACCOUNT_ORDERS,
                      permissions=dict(PERMISSIONS))
        target = _safe_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(descriptor)
        db = sqlite3.connect(target, isolation_level=None)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.executescript("""BEGIN IMMEDIATE;
              CREATE TABLE meta(config TEXT NOT NULL, config_hash TEXT NOT NULL, cash TEXT NOT NULL, stop_reason TEXT);
              CREATE TABLE plans(plan_id TEXT PRIMARY KEY, document TEXT NOT NULL);
              CREATE TABLE orders(order_id TEXT PRIMARY KEY, terms TEXT NOT NULL, terms_hash TEXT NOT NULL,
                state TEXT NOT NULL, filled INTEGER NOT NULL, notional TEXT NOT NULL, fee TEXT NOT NULL,
                reserved_cash TEXT NOT NULL, reserved_shares INTEGER NOT NULL, cancel_state TEXT);
              CREATE TABLE opportunities(opportunity_id TEXT PRIMARY KEY, order_id TEXT NOT NULL UNIQUE);
              CREATE TABLE positions(owner_id TEXT NOT NULL, security_id TEXT NOT NULL, quantity INTEGER NOT NULL,
                PRIMARY KEY(owner_id,security_id));
              CREATE TABLE marks(security_id TEXT PRIMARY KEY, quote TEXT NOT NULL);
              CREATE TABLE fills(evidence_id TEXT PRIMARY KEY, order_id TEXT NOT NULL, quantity INTEGER NOT NULL,
                notional TEXT NOT NULL, fee TEXT NOT NULL);
              CREATE TABLE observations(evidence_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL);
              CREATE TABLE events(sequence INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL,
                previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
              CREATE TABLE requests(request_id TEXT PRIMARY KEY, payload_hash TEXT NOT NULL,
                receipt TEXT NOT NULL, receipt_hash TEXT NOT NULL);
            """)
            db.execute(f"PRAGMA application_id={APP_ID}")
            db.execute("PRAGMA user_version=1")
            db.execute("INSERT INTO meta VALUES(?,?,?,NULL)", (_json(config), _hash(config), _amount(cash)))
            db.commit()
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()
        result = cls(target, account_id=account_id)
        result._ready_revision = 0  # The just-created, empty synthetic seed is known.
        return result

    def __init__(self, path, *, account_id):
        self._lock = RLock()
        self.path = _safe_path(path)
        # Reject another product's database before SQLite can create sidecars.
        with self.path.open("rb") as source:
            header = source.read(100)
        if len(header) < 100 or header[:16] != b"SQLite format 3\0" or int.from_bytes(header[68:72], "big") != APP_ID or int.from_bytes(header[60:64], "big") != 1:
            raise ExecutionError("offline_execution_database_identity_mismatch")
        self.db = sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, isolation_level=None, timeout=10, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA synchronous=FULL")
        self._ready_revision = None
        try:
            self.db.execute("BEGIN")
            if self.db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ExecutionError("offline_execution_database_corrupt")
            row = self.db.execute("SELECT * FROM meta").fetchone()
            self.config = json.loads(row["config"])
            if self.config["schema_version"] != SCHEMA or _hash(self.config) != row["config_hash"]:
                raise ExecutionError("offline_execution_config_mismatch")
            self._account(account_id)
            self._verify()
            self.db.commit()
        except BaseException:
            self.db.close()
            raise

    @classmethod
    def open(cls, path, *, account_id):
        return cls(path, account_id=account_id)

    @_serialized
    def close(self):
        self.db.close()

    def _account(self, value):
        if value != self.config["account_id"]:
            raise ExecutionError("offline_execution_wrong_account")

    def _revision(self):
        return self.db.execute("SELECT COALESCE(MAX(sequence),0) FROM events").fetchone()[0]

    def _event(self, kind, payload):
        row = self.db.execute("SELECT sequence,event_hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        sequence, previous = (row[0] + 1, row[1]) if row else (1, "0" * 64)
        event = dict(sequence=sequence, kind=kind, payload=payload, previous_hash=previous)
        self.db.execute("INSERT INTO events VALUES(?,?,?,?,?)", (sequence, kind, _json(payload), previous, _hash(event)))

    def _after_commit(self):
        """Return boundary, also used by isolated interruption tests."""

    def _mutate(self, request_id, action, payload, operation, *, ready_after=True):
        _text(request_id)
        request = {"action": action, "account_id": self.config["account_id"], "payload": payload}
        encoded = _json(request)
        if len(encoded) > MAX_REQUEST_BYTES:
            raise ExecutionError("execution_request_too_large")
        digest = _hash(request)
        with localcontext() as precision:
            precision.prec = 60
            self.db.execute("BEGIN IMMEDIATE")
            try:
                self._verify()
                old = self.db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
                if old:
                    if old["payload_hash"] != digest:
                        raise ExecutionError("execution_request_id_conflict")
                    receipt = self._validate_receipt(old)
                    self.db.commit()
                    return receipt
                was_ready = self._ready_revision == self._revision()
                outcome = operation()
                self._event("OPERATION_RECORDED", dict(request_id=request_id, request_hash=digest, action=action, outcome=outcome))
                receipt = dict(schema_version=RECEIPT_SCHEMA, request_id=request_id,
                               account_id=self.config["account_id"], action=action, request_hash=digest,
                               revision=self._revision(), outcome=outcome, permissions=dict(PERMISSIONS))
                self.db.execute("INSERT INTO requests VALUES(?,?,?,?)", (request_id, digest, _json(receipt), _hash(receipt)))
                self.db.commit()
            except BaseException:
                self.db.rollback()
                raise
        confirmed_snapshot = action == "RECONCILE_SYNTHETIC" and outcome["status"] == "RECONCILED"
        if ready_after and (was_ready or confirmed_snapshot) and not self._unknown_orders() and not self._deficits():
            self._ready_revision = self._revision()
        else:
            self._ready_revision = None
        self._after_commit()
        return receipt

    @_read_transaction
    def receipt(self, request_id):
        _text(request_id)
        self._verify()
        row = self.db.execute("SELECT * FROM requests WHERE request_id=?", (request_id,)).fetchone()
        if not row:
            return {"status": "NOT_RECORDED", "request_id": request_id, "automatic_retry_allowed": False}
        receipt = self._validate_receipt(row)
        return {"status": "COMMITTED", "receipt": receipt, "automatic_retry_allowed": False}

    def _validate_receipt(self, row):
        receipt = json.loads(row["receipt"])
        required = {"schema_version", "request_id", "account_id", "action", "request_hash", "revision", "outcome", "permissions"}
        if (type(receipt) is not dict or set(receipt) != required or _hash(receipt) != row["receipt_hash"]
                or receipt["schema_version"] != RECEIPT_SCHEMA or receipt["request_id"] != row["request_id"]
                or receipt["account_id"] != self.config["account_id"] or receipt["permissions"] != PERMISSIONS
                or receipt["request_hash"] != row["payload_hash"]):
            raise ExecutionError("offline_execution_receipt_envelope_mismatch")
        return receipt

    @_serialized
    def create_plan(self, request_id, *, account_id, owner_id, research_binding, stage="SIMULATION"):
        self._account(account_id)
        _text(owner_id)
        binding = _binding(research_binding)
        if stage not in STAGES:
            raise ExecutionError("execution_stage_invalid")
        document = dict(schema_version="hakimi-offline-plan-v1", account_id=account_id, owner_id=owner_id,
                        stage=stage, research_stage="BACKTESTED", research_binding=binding,
                        binding_hash=_hash(binding), account_rules_hash=_hash(self.config["rules"]),
                        permissions={**PERMISSIONS, "local_simulation_allowed": stage == "SIMULATION"})
        plan_id = _hash(document)
        def operation():
            self.db.execute("INSERT OR IGNORE INTO plans VALUES(?,?)", (plan_id, _json(document)))
            return {"status": "PLAN_SAVED", "plan_id": plan_id, "stage": stage, "binding_hash": _hash(binding)}
        return self._mutate(request_id, "CREATE_PLAN", document, operation, ready_after=self._ready_revision == self._revision())

    def _plan(self, plan_id):
        row = self.db.execute("SELECT document FROM plans WHERE plan_id=?", (_text(plan_id),)).fetchone()
        if not row:
            raise ExecutionError("execution_plan_not_found")
        value = json.loads(row[0])
        if _hash(value) != plan_id:
            raise ExecutionError("execution_plan_corrupt")
        return value

    def _quote(self, quote, now_ms):
        _fields(quote, {"security_id", "price", "as_of", "observed_at", "source_id", "evidence_kind"})
        if quote["security_id"] not in self.config["securities"] or quote["evidence_kind"] != "SYNTHETIC_TEST":
            raise ExecutionError("explicit_synthetic_quote_required")
        _text(quote["source_id"])
        price = _money(quote["price"], positive=True)
        as_of, observed = _clock(quote["as_of"]), _clock(quote["observed_at"])
        if not as_of <= observed <= now_ms or now_ms - as_of > self.config["rules"]["quote_max_age_ms"]:
            raise ExecutionError("stale_or_future_execution_quote")
        old = self.db.execute("SELECT quote FROM marks WHERE security_id=?", (quote["security_id"],)).fetchone()
        if old:
            previous = json.loads(old[0])
            if as_of < previous["as_of"] or as_of == previous["as_of"] and price != _money(previous["price"]):
                raise ExecutionError("execution_quote_revision_conflict")
        return deepcopy(quote)

    @_serialized
    def mark_quotes(self, request_id, *, account_id, quotes, now_ms):
        self._account(account_id)
        _clock(now_ms)
        if type(quotes) is not list or not quotes or len(quotes) > 100:
            raise ExecutionError("execution_quotes_required")
        def operation():
            seen = set()
            for quote in quotes:
                quote = self._quote(quote, now_ms)
                if quote["security_id"] in seen:
                    raise ExecutionError("execution_duplicate_quote")
                seen.add(quote["security_id"])
                self.db.execute("INSERT OR REPLACE INTO marks VALUES(?,?)", (quote["security_id"], _json(quote)))
            return {"status": "QUOTES_RECORDED", "security_ids": sorted(seen)}
        return self._mutate(request_id, "MARK_QUOTES", dict(quotes=quotes, now_ms=now_ms), operation, ready_after=self._ready_revision == self._revision())

    def _unknown_orders(self):
        return self.db.execute("SELECT COUNT(*) FROM orders WHERE state='TIMEOUT_UNCONFIRMED'").fetchone()[0]

    def _require_ready(self):
        if self._ready_revision != self._revision() or self._unknown_orders() or self._deficits():
            raise ExecutionError("explicit_synthetic_reconciliation_required")

    def _order(self, order_id):
        row = self.db.execute("SELECT * FROM orders WHERE order_id=?", (_text(order_id),)).fetchone()
        if not row:
            raise ExecutionError("execution_order_not_found")
        return dict(row)

    def _cash(self):
        return Decimal(self.db.execute("SELECT cash FROM meta").fetchone()[0])

    def _reserved_cash(self):
        return sum((Decimal(row[0]) for row in self.db.execute("SELECT reserved_cash FROM orders")), Decimal(0))

    def _held(self, owner, security):
        row = self.db.execute("SELECT quantity FROM positions WHERE owner_id=? AND security_id=?", (owner, security)).fetchone()
        return row[0] if row else 0

    def _reserved_shares(self, owner, security):
        return sum(row["reserved_shares"] for row in self.db.execute("SELECT terms,reserved_shares FROM orders")
                   if (lambda terms: terms["owner_id"] == owner and terms["security_id"] == security)(json.loads(row["terms"])))

    def _deficits(self):
        deficits = []
        cash, reserved = self._cash(), self._reserved_cash()
        if cash < reserved:
            deficits.append(dict(kind="CASH_BELOW_RESERVATION", cash=_amount(cash), reserved_cash=_amount(reserved)))
        holdings = {(row["owner_id"], row["security_id"]): row["quantity"] for row in self.db.execute("SELECT * FROM positions")}
        reservations = {}
        for row in self.db.execute("SELECT terms,reserved_shares FROM orders"):
            terms = json.loads(row["terms"])
            key = (terms["owner_id"], terms["security_id"])
            reservations[key] = reservations.get(key, 0) + row["reserved_shares"]
        for owner, security in sorted(set(holdings) | set(reservations)):
            held, locked = holdings.get((owner, security), 0), reservations.get((owner, security), 0)
            if held < 0 or held < locked:
                deficits.append(dict(kind="OWNER_SHARES_BELOW_RESERVATION", owner_id=owner, security_id=security,
                                     quantity=held, reserved_shares=locked))
        return deficits

    def _set_stop(self, reason, source):
        self.db.execute("UPDATE meta SET stop_reason=?", (reason,))
        self._event("RISK_STOP_STATE", dict(stop_reason=reason, source=source))

    def _exposure(self, security, now_ms):
        total = own = Decimal(0)
        for row in self.db.execute("SELECT security_id,SUM(quantity) AS quantity FROM positions GROUP BY security_id"):
            if not row["quantity"]:
                continue
            mark = self.db.execute("SELECT quote FROM marks WHERE security_id=?", (row["security_id"],)).fetchone()
            if not mark:
                raise ExecutionError("current_quote_required_for_all_holdings")
            quote = self._quote(json.loads(mark[0]), now_ms)
            value = _money(quote["price"]) * row["quantity"]
            total += value
            if row["security_id"] == security:
                own += value
        reserved_total = reserved_own = Decimal(0)
        for row in self.db.execute("SELECT terms,filled,state FROM orders"):
            terms = json.loads(row["terms"])
            if row["state"] not in TERMINAL and terms["side"] == "BUY":
                value = _money(terms["limit_price"]) * (terms["quantity"] - row["filled"])
                reserved_total += value
                if terms["security_id"] == security:
                    reserved_own += value
        return total, own, reserved_total, reserved_own

    def _risk(self, terms, now_ms):
        self._require_ready()
        rules = self.config["rules"]
        amount = _money(terms["limit_price"]) * terms["quantity"]
        if amount > _money(rules["max_order_notional"]):
            return "ORDER_NOTIONAL_LIMIT"
        if terms["side"] == "SELL":
            return "OWNER_SHARES_UNAVAILABLE" if terms["quantity"] > self._held(terms["owner_id"], terms["security_id"]) - self._reserved_shares(terms["owner_id"], terms["security_id"]) else None
        if self.db.execute("SELECT stop_reason FROM meta").fetchone()[0]:
            return "NEW_RISK_STOPPED"
        if self._cash() - self._reserved_cash() - amount - _money(rules["fee_buffer"]) < _money(rules["cash_floor"]):
            return "SHARED_CASH_UNAVAILABLE"
        total, own, reserved, reserved_own = self._exposure(terms["security_id"], now_ms)
        if Decimal(self.config["initial_cash"]) - self._cash() - total > _money(rules["max_account_loss"]):
            self._set_stop("ACCOUNT_LOSS_LIMIT", "ACCOUNT_RISK_CHECK")
            return "ACCOUNT_LOSS_LIMIT"
        if total + reserved + amount > _money(rules["max_total_exposure"]):
            return "TOTAL_EXPOSURE_LIMIT"
        if own + reserved_own + amount > _money(rules["max_security_exposure"]):
            return "SECURITY_EXPOSURE_LIMIT"
        return None

    @_serialized
    def submit(self, request_id, *, account_id, plan_id, security_id, side, quantity,
               limit_price, quote, signal_at, execution_at, now_ms, outcome="ACCEPTED"):
        self._account(account_id)
        _clock(now_ms)
        _clock(signal_at)
        _clock(execution_at)
        if signal_at > execution_at or execution_at > now_ms:
            raise ExecutionError("execution_signal_clock_invalid")
        _integer(quantity, maximum=10**9)
        if type(security_id) is not str or type(side) is not str or type(outcome) is not str or security_id not in self.config["securities"] or side not in {"BUY", "SELL"} or outcome not in {"ACCEPTED", "REJECTED", "TIMEOUT_UNCONFIRMED"}:
            raise ExecutionError("execution_order_terms_invalid")
        price = _money(limit_price, positive=True)
        if price % _money(self.config["securities"][security_id]["tick_size"]) != 0:
            raise ExecutionError("execution_price_tick_mismatch")
        plan = self._plan(plan_id)
        if plan["stage"] != "SIMULATION":
            raise ExecutionError("only_simulation_plan_can_submit")
        if type(quote) is not dict or quote.get("security_id") != security_id:
            raise ExecutionError("execution_quote_security_mismatch")
        binding = plan["research_binding"]
        if "security_id" in binding and binding["security_id"] != security_id:
            raise ExecutionError("execution_order_research_security_mismatch")
        opportunity = dict(account_id=account_id, security_id=security_id, signal_at=signal_at, execution_at=execution_at)
        if side == "SELL":
            opportunity.update(owner_id=plan["owner_id"], kind="OWNER_REDUCTION")
        else:
            opportunity.update(kind="GLOBAL_BUY", engine_id=binding["engine_id"], strategy_id=binding["strategy_id"], strategy_params=binding["strategy_params"])
        opportunity_id = _hash(opportunity)
        terms = dict(account_id=account_id, plan_id=plan_id, owner_id=plan["owner_id"], security_id=security_id,
                     side=side, quantity=quantity, limit_price=_amount(price), signal_at=signal_at,
                     execution_at=execution_at, opportunity_id=opportunity_id, binding_hash=plan["binding_hash"])
        payload = dict(terms=terms, quote=quote, now_ms=now_ms, outcome=outcome)
        order_id = _hash(dict(account_id=account_id, request_id=request_id))
        def operation():
            old = self.db.execute("SELECT order_id FROM opportunities WHERE opportunity_id=?", (opportunity_id,)).fetchone()
            if old:
                return {"status": "DUPLICATE_OPPORTUNITY", "order_id": old[0], "new_order": False}
            if self.db.execute("SELECT COUNT(*) FROM orders").fetchone()[0] >= self.config["max_orders"]:
                return {"status": "CAPACITY_REACHED", "reason": "NEW_ACCOUNT_REQUIRED_NO_HISTORY_REWRITE",
                        "max_orders": self.config["max_orders"], "new_order": False}
            checked = self._quote(quote, now_ms)
            self.db.execute("INSERT OR REPLACE INTO marks VALUES(?,?)", (security_id, _json(checked)))
            reason = self._risk(terms, now_ms)
            state = "REJECTED" if reason or outcome == "REJECTED" else outcome
            reason = reason or ("EXPLICIT_SYNTHETIC_REJECTION" if state == "REJECTED" else None)
            reserved = price * quantity + _money(self.config["rules"]["fee_buffer"]) if side == "BUY" and state != "REJECTED" else Decimal(0)
            shares = quantity if side == "SELL" and state != "REJECTED" else 0
            self.db.execute("INSERT INTO orders VALUES(?,?,?,?,?,?,?,?,?,NULL)",
                            (order_id, _json(terms), _hash(terms), state, 0, "0", "0", _amount(reserved), shares))
            self.db.execute("INSERT INTO opportunities VALUES(?,?)", (opportunity_id, order_id))
            self._event("SYNTHETIC_ORDER_DECLARED", dict(order_id=order_id, terms=terms, outcome=state, reason=reason, quote=checked))
            return {"status": state, "order_id": order_id, "reason": reason, "new_order": True}
        return self._mutate(request_id, "SUBMIT_SYNTHETIC", payload, operation, ready_after=outcome != "TIMEOUT_UNCONFIRMED")

    def _reservation(self, terms, state, filled, fee):
        if state in TERMINAL:
            return "0", 0
        remaining = terms["quantity"] - filled
        if terms["side"] == "SELL":
            return "0", remaining
        return _amount(_money(terms["limit_price"]) * remaining + max(_money(self.config["rules"]["fee_buffer"]) - fee, Decimal(0))), 0

    def _apply_observation(self, observation, *, complete_snapshot=False):
        _fields(observation, {"evidence_id", "order_id", "state", "cumulative_quantity", "cumulative_notional", "cumulative_fee"})
        evidence_id = _text(observation["evidence_id"])
        digest = _hash(observation)
        prior = self.db.execute("SELECT payload_hash FROM observations WHERE evidence_id=?", (evidence_id,)).fetchone()
        if prior:
            if prior[0] != digest:
                raise ExecutionError("execution_observation_id_conflict")
            if not complete_snapshot:
                return "DUPLICATE"
        row = self._order(observation["order_id"])
        terms = json.loads(row["terms"])
        filled = _integer(observation["cumulative_quantity"], zero=True, maximum=10**9)
        notional = _money(observation["cumulative_notional"])
        fee = _money(observation["cumulative_fee"])
        state = _text(observation["state"], 40)
        if state not in STATES - {"TIMEOUT_UNCONFIRMED"} or filled > terms["quantity"] or (filled == 0) != (notional == 0):
            raise ExecutionError("execution_cumulative_state_invalid")
        if (state == "FILLED") != (filled == terms["quantity"]) or state == "PARTIAL" and not 0 < filled < terms["quantity"] or state in {"REJECTED", "ACCEPTED"} and filled:
            raise ExecutionError("execution_cumulative_state_invalid")
        if complete_snapshot and row["state"] in TERMINAL and state not in TERMINAL:
            raise ExecutionError("terminal_order_reported_open")
        if filled < row["filled"] or filled == row["filled"] and notional == Decimal(row["notional"]) and fee < Decimal(row["fee"]):
            if complete_snapshot:
                raise ExecutionError("stale_order_in_complete_snapshot")
            self.db.execute("INSERT INTO observations VALUES(?,?)", (evidence_id, digest))
            return "STALE"
        delta_qty, delta_value, delta_fee = filled - row["filled"], notional - Decimal(row["notional"]), fee - Decimal(row["fee"])
        if delta_fee < 0 or delta_qty == 0 and delta_value != 0 or delta_qty > 0 and delta_value <= 0:
            raise ExecutionError("execution_cumulative_value_conflict")
        if delta_qty and (terms["side"] == "BUY" and delta_value > delta_qty * _money(terms["limit_price"]) or terms["side"] == "SELL" and delta_value < delta_qty * _money(terms["limit_price"])):
            raise ExecutionError("execution_fill_limit_conflict")
        if row["state"] == "REJECTED" and state != "REJECTED":
            raise ExecutionError("rejected_order_cannot_reopen")
        if row["state"] in TERMINAL and state != "FILLED":
            state = row["state"]
        signed_qty = delta_qty if terms["side"] == "BUY" else -delta_qty
        cash_delta = -delta_value - delta_fee if terms["side"] == "BUY" else delta_value - delta_fee
        held = self._held(terms["owner_id"], terms["security_id"]) + signed_qty
        self.db.execute("UPDATE meta SET cash=?", (_amount(self._cash() + cash_delta),))
        self.db.execute("INSERT OR REPLACE INTO positions VALUES(?,?,?)", (terms["owner_id"], terms["security_id"], held))
        if not prior:
            self.db.execute("INSERT INTO observations VALUES(?,?)", (evidence_id, digest))
        if delta_qty or delta_fee:
            self.db.execute("INSERT INTO fills VALUES(?,?,?,?,?)", (evidence_id, row["order_id"], delta_qty, _amount(delta_value), _amount(delta_fee)))
        reserved, shares = self._reservation(terms, state, filled, fee)
        cancel = "SUPERSEDED_BY_FILL" if state == "FILLED" and row["cancel_state"] else "CONFIRMED" if state == "CANCELLED" else row["cancel_state"]
        self.db.execute("UPDATE orders SET state=?,filled=?,notional=?,fee=?,reserved_cash=?,reserved_shares=?,cancel_state=? WHERE order_id=?",
                        (state, filled, _amount(notional), _amount(fee), reserved, shares, cancel, row["order_id"]))
        self._event("SYNTHETIC_OBSERVATION_APPLIED", dict(observation=observation, delta_quantity=delta_qty, delta_notional=_amount(delta_value), delta_fee=_amount(delta_fee)))
        if self._deficits():
            self._set_stop("OBSERVED_ACCOUNT_DEFICIT", "SYNTHETIC_OBSERVATION")
        return "APPLIED"

    @_serialized
    def observe(self, request_id, *, account_id, observation, now_ms):
        self._account(account_id)
        _clock(now_ms)
        def operation():
            self.db.execute("SAVEPOINT observe")
            try:
                status = self._apply_observation(observation)
                self.db.execute("RELEASE observe")
                return {"status": status, "order_id": observation["order_id"]}
            except ExecutionError as exc:
                self.db.execute("ROLLBACK TO observe")
                self.db.execute("RELEASE observe")
                self._event("SYNTHETIC_OBSERVATION_REJECTED", dict(reason=str(exc), observation=observation))
                self._set_stop(str(exc), "REJECTED_OBSERVATION")
                return {"status": "BLOCKED", "reason": str(exc)}
        return self._mutate(request_id, "OBSERVE_SYNTHETIC", dict(observation=observation, now_ms=now_ms), operation,
                            ready_after=self._ready_revision == self._revision())

    @_serialized
    def cancel(self, request_id, *, account_id, order_id, now_ms, outcome="ACCEPTED"):
        self._account(account_id)
        _clock(now_ms)
        if type(outcome) is not str or outcome not in {"ACCEPTED", "TIMEOUT_UNCONFIRMED"}:
            raise ExecutionError("cancel_response_is_not_terminal_use_observation")
        def operation():
            row = self._order(order_id)
            if row["state"] in TERMINAL:
                return {"status": "ALREADY_TERMINAL", "order_id": order_id}
            if row["cancel_state"]:
                return {"status": "CANCEL_ALREADY_ATTEMPTED", "order_id": order_id, "automatic_retry_allowed": False}
            if row["state"] == "TIMEOUT_UNCONFIRMED":
                raise ExecutionError("unknown_submission_requires_reconciliation")
            self.db.execute("UPDATE orders SET state=?,cancel_state=? WHERE order_id=?",
                            ("TIMEOUT_UNCONFIRMED" if outcome == "TIMEOUT_UNCONFIRMED" else row["state"], outcome, order_id))
            return {"status": "CANCEL_RESPONSE_" + outcome, "order_id": order_id, "reservation_released": False}
        return self._mutate(request_id, "CANCEL_SYNTHETIC", dict(order_id=order_id, now_ms=now_ms, outcome=outcome), operation,
                            ready_after=outcome != "TIMEOUT_UNCONFIRMED" and self._ready_revision == self._revision())

    @_serialized
    def reconcile(self, request_id, *, account_id, complete_snapshot, now_ms):
        self._account(account_id)
        _clock(now_ms)
        _fields(complete_snapshot, {"schema_version", "evidence_kind", "account_id", "account_revision", "observed_at", "orders", "cash", "positions"})
        if complete_snapshot["schema_version"] != SNAPSHOT_SCHEMA or complete_snapshot["evidence_kind"] != "SYNTHETIC_TEST" or complete_snapshot["account_id"] != account_id:
            raise ExecutionError("explicit_complete_synthetic_snapshot_required")
        _integer(complete_snapshot["account_revision"], zero=True)
        observed = _clock(complete_snapshot["observed_at"])
        if observed > now_ms or now_ms - observed > self.config["rules"]["quote_max_age_ms"]:
            raise ExecutionError("stale_synthetic_reconciliation")
        if (type(complete_snapshot["orders"]) is not list or len(complete_snapshot["orders"]) > self.config["max_orders"]
                or type(complete_snapshot["positions"]) is not list or len(complete_snapshot["positions"]) > self.config["max_orders"]):
            raise ExecutionError("complete_synthetic_snapshot_lists_required")
        def operation():
            if complete_snapshot["account_revision"] != self._revision():
                raise ExecutionError("synthetic_reconciliation_revision_changed")
            self.db.execute("SAVEPOINT reconcile")
            try:
                expected = {row[0] for row in self.db.execute("SELECT order_id FROM orders")}
                seen = set()
                for observation in complete_snapshot["orders"]:
                    identity = _text(observation.get("order_id")) if type(observation) is dict else None
                    if identity in seen or identity not in expected:
                        raise ExecutionError("ambiguous_or_unknown_snapshot_order")
                    seen.add(identity)
                    self._apply_observation(observation, complete_snapshot=True)
                if seen != expected:
                    raise ExecutionError("order_absence_does_not_prove_rejection")
                positions = []
                keys = set()
                for item in complete_snapshot["positions"]:
                    _fields(item, {"owner_id", "security_id", "quantity"})
                    key = (_text(item["owner_id"]), _text(item["security_id"]))
                    if key in keys or key[1] not in self.config["securities"]:
                        raise ExecutionError("snapshot_position_identity_invalid")
                    keys.add(key)
                    quantity = _integer(item["quantity"], zero=True)
                    if quantity:
                        positions.append(dict(owner_id=key[0], security_id=key[1], quantity=quantity))
                positions.sort(key=lambda item: (item["owner_id"], item["security_id"]))
                if _money(complete_snapshot["cash"], signed=True) != self._cash() or positions != self._positions():
                    raise ExecutionError("synthetic_cash_or_owner_position_mismatch")
                if self._unknown_orders() or self._deficits():
                    raise ExecutionError("synthetic_account_still_unconfirmed")
                self.db.execute("RELEASE reconcile")
                return {"status": "RECONCILED", "snapshot_hash": _hash(complete_snapshot), "automatic_submission": False}
            except ExecutionError as exc:
                self.db.execute("ROLLBACK TO reconcile")
                self.db.execute("RELEASE reconcile")
                self._event("SYNTHETIC_RECONCILIATION_REJECTED", dict(reason=str(exc), snapshot=complete_snapshot))
                self._set_stop(str(exc), "REJECTED_RECONCILIATION")
                return {"status": "BLOCKED", "reason": str(exc), "automatic_submission": False}
        receipt = self._mutate(request_id, "RECONCILE_SYNTHETIC", dict(snapshot=complete_snapshot, now_ms=now_ms), operation)
        if receipt["outcome"]["status"] != "RECONCILED":
            self._ready_revision = None
        return receipt

    @_serialized
    def stop(self, request_id, *, account_id, reason):
        self._account(account_id)
        _text(reason, 500)
        def operation():
            self._set_stop(reason, "EXPLICIT_STOP")
            return {"status": "NEW_RISK_STOPPED", "reason": reason}
        return self._mutate(request_id, "STOP", dict(reason=reason), operation,
                            ready_after=self._ready_revision == self._revision())

    @_serialized
    def resume(self, request_id, *, account_id, reason):
        self._account(account_id)
        _text(reason, 500)
        def operation():
            self._require_ready()
            if self._deficits():
                raise ExecutionError("account_deficit_prevents_resume")
            self._set_stop(None, "EXPLICIT_RESUME")
            return {"status": "NEW_RISK_RESUMED", "reason": reason}
        return self._mutate(request_id, "RESUME", dict(reason=reason), operation)

    def _positions(self):
        return [dict(row) for row in self.db.execute("SELECT owner_id,security_id,quantity FROM positions WHERE quantity<>0 ORDER BY owner_id,security_id")]

    @_read_transaction
    def snapshot(self):
        self._verify()
        orders = []
        for row in self.db.execute("SELECT * FROM orders ORDER BY rowid"):
            value = dict(row)
            value["terms"] = json.loads(value["terms"])
            orders.append(value)
        return dict(schema_version=SCHEMA, account_id=self.config["account_id"], evidence_kind="SYNTHETIC_TEST",
                    config=deepcopy(self.config), revision=self._revision(), cash=_amount(self._cash()),
                    reserved_cash=_amount(self._reserved_cash()), available_cash=_amount(self._cash() - self._reserved_cash()),
                    positions=self._positions(), orders=orders,
                    plans=[dict(plan_id=row[0], **json.loads(row[1])) for row in self.db.execute("SELECT * FROM plans ORDER BY rowid")],
                    stop_reason=self.db.execute("SELECT stop_reason FROM meta").fetchone()[0],
                    account_deficits=self._deficits(),
                    reconciliation_required=self._ready_revision != self._revision() or bool(self._unknown_orders()) or bool(self._deficits()),
                    permissions=dict(PERMISSIONS), automatic_submission=False, external_calls=0)

    @_read_transaction
    def history(self, limit=50):
        _integer(limit, maximum=1000)
        self._verify()
        return [dict(sequence=row["sequence"], kind=row["kind"], payload=json.loads(row["payload"]),
                     event_hash=row["event_hash"]) for row in self.db.execute("SELECT * FROM events ORDER BY sequence DESC LIMIT ?", (limit,))]

    def _verify(self):
        metadata = self.db.execute("SELECT config,config_hash FROM meta").fetchone()
        if metadata["config_hash"] != _hash(self.config) or json.loads(metadata["config"]) != self.config:
            raise ExecutionError("offline_execution_config_mismatch")
        previous, sequence = "0" * 64, 0
        declared, recorded_fills, recorded_operations = {}, {}, {}
        expected_stop = None
        for row in self.db.execute("SELECT * FROM events ORDER BY sequence"):
            sequence += 1
            event = dict(sequence=row["sequence"], kind=row["kind"], payload=json.loads(row["payload"]), previous_hash=row["previous_hash"])
            if row["sequence"] != sequence or row["previous_hash"] != previous or _hash(event) != row["event_hash"]:
                raise ExecutionError("offline_execution_event_chain_mismatch")
            previous = row["event_hash"]
            payload = event["payload"]
            if row["kind"] == "RISK_STOP_STATE":
                expected_stop = payload["stop_reason"]
            elif row["kind"] == "SYNTHETIC_ORDER_DECLARED":
                if payload["order_id"] in declared:
                    raise ExecutionError("offline_execution_duplicate_order_declaration")
                declared[payload["order_id"]] = dict(terms=payload["terms"], state=payload["outcome"], filled=0,
                                                     notional=Decimal(0), fee=Decimal(0), cancel_state=None)
            elif row["kind"] == "SYNTHETIC_OBSERVATION_APPLIED":
                observation = payload["observation"]
                original = declared.get(observation["order_id"])
                if original is None:
                    raise ExecutionError("offline_execution_observation_without_order")
                state = observation["state"]
                if original["state"] in TERMINAL and state != "FILLED":
                    state = original["state"]
                cancel = "SUPERSEDED_BY_FILL" if state == "FILLED" and original["cancel_state"] else "CONFIRMED" if state == "CANCELLED" else original["cancel_state"]
                original.update(state=state, filled=observation["cumulative_quantity"],
                                notional=Decimal(observation["cumulative_notional"]), fee=Decimal(observation["cumulative_fee"]), cancel_state=cancel)
                if payload["delta_quantity"] or Decimal(payload["delta_fee"]):
                    if observation["evidence_id"] in recorded_fills:
                        raise ExecutionError("offline_execution_duplicate_fill_event")
                    recorded_fills[observation["evidence_id"]] = (observation["order_id"], payload["delta_quantity"],
                                                                Decimal(payload["delta_notional"]), Decimal(payload["delta_fee"]))
            elif row["kind"] == "OPERATION_RECORDED":
                if payload["request_id"] in recorded_operations:
                    raise ExecutionError("offline_execution_duplicate_request_event")
                recorded_operations[payload["request_id"]] = (row["sequence"], payload)
                status = payload["outcome"]["status"]
                if payload["action"] == "CANCEL_SYNTHETIC" and status.startswith("CANCEL_RESPONSE_"):
                    original = declared[payload["outcome"]["order_id"]]
                    original["cancel_state"] = status.removeprefix("CANCEL_RESPONSE_")
                    if original["cancel_state"] == "TIMEOUT_UNCONFIRMED":
                        original["state"] = "TIMEOUT_UNCONFIRMED"
        for row in self.db.execute("SELECT * FROM plans"):
            self._plan(row["plan_id"])
        if self.db.execute("SELECT stop_reason FROM meta").fetchone()[0] != expected_stop:
            raise ExecutionError("offline_execution_stop_state_mismatch")
        actual_fills = {row["evidence_id"]: (row["order_id"], row["quantity"], Decimal(row["notional"]), Decimal(row["fee"]))
                        for row in self.db.execute("SELECT * FROM fills")}
        if actual_fills != recorded_fills:
            raise ExecutionError("offline_execution_fill_event_mismatch")
        cash, positions = Decimal(self.config["initial_cash"]), {}
        actual_orders, opportunities = set(), {}
        for row in self.db.execute("SELECT * FROM orders"):
            actual_orders.add(row["order_id"])
            terms = json.loads(row["terms"])
            if row["state"] not in STATES or not 0 <= row["filled"] <= terms["quantity"]:
                raise ExecutionError("offline_execution_order_state_invalid")
            if _hash(terms) != row["terms_hash"]:
                raise ExecutionError("offline_execution_order_terms_mismatch")
            observed = dict(terms=terms, state=row["state"], filled=row["filled"], notional=Decimal(row["notional"]),
                            fee=Decimal(row["fee"]), cancel_state=row["cancel_state"])
            if declared.get(row["order_id"]) != observed:
                raise ExecutionError("offline_execution_order_event_mismatch")
            opportunities[terms["opportunity_id"]] = row["order_id"]
            self._plan(terms["plan_id"])
            totals = [0, Decimal(0), Decimal(0)]
            for fill in self.db.execute("SELECT * FROM fills WHERE order_id=?", (row["order_id"],)):
                totals[0] += fill["quantity"]
                totals[1] += Decimal(fill["notional"])
                totals[2] += Decimal(fill["fee"])
            if totals != [row["filled"], Decimal(row["notional"]), Decimal(row["fee"])]:
                raise ExecutionError("offline_execution_fill_totals_mismatch")
            reserved, shares = self._reservation(terms, row["state"], row["filled"], Decimal(row["fee"]))
            if Decimal(reserved) != Decimal(row["reserved_cash"]) or shares != row["reserved_shares"]:
                raise ExecutionError("offline_execution_reservation_mismatch")
            key = (terms["owner_id"], terms["security_id"])
            positions[key] = positions.get(key, 0) + (totals[0] if terms["side"] == "BUY" else -totals[0])
            cash += -totals[1] - totals[2] if terms["side"] == "BUY" else totals[1] - totals[2]
        restored = [dict(owner_id=owner, security_id=security, quantity=qty) for (owner, security), qty in sorted(positions.items()) if qty]
        if cash != self._cash() or restored != self._positions():
            raise ExecutionError("offline_execution_account_reconstruction_mismatch")
        if actual_orders != set(declared) or opportunities != dict(self.db.execute("SELECT opportunity_id,order_id FROM opportunities").fetchall()):
            raise ExecutionError("offline_execution_opportunity_reconstruction_mismatch")
        request_ids = set()
        for row in self.db.execute("SELECT * FROM requests"):
            request_ids.add(row["request_id"])
            receipt = self._validate_receipt(row)
            recorded = recorded_operations.get(row["request_id"])
            if _hash(receipt) != row["receipt_hash"] or recorded is None:
                raise ExecutionError("offline_execution_receipt_mismatch")
            revision, payload = recorded
            if (receipt["revision"] != revision or receipt["request_hash"] != row["payload_hash"] or row["payload_hash"] != payload["request_hash"]
                    or receipt["outcome"] != payload["outcome"] or receipt["action"] != payload["action"]):
                raise ExecutionError("offline_execution_receipt_event_mismatch")
        if request_ids != set(recorded_operations):
            raise ExecutionError("offline_execution_receipt_event_mismatch")
