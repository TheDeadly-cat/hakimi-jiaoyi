"""Explicit historical replay prototype; never a broker or manual-account store.

Trusted caller admits complete saved bars and binds the actual signal function.
Event time is a bar's original UTC open/close; recorded_at is audit time only.
No quote-freshness substitution, native fill-equivalence or automatic stepping.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_EVEN
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import stat
from threading import Event, RLock

MODEL = "HISTORICAL_REPLAY_WHOLE_SHARE_NEXT_OPEN_V1"
APP_ID = 0x48525032
ZERO = "0" * 64
MAX_BARS = 20000
LOADED_IMPLEMENTATION_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
DEFAULT_LIMITS = dict(max_events=10000, control_reserve=4, history_page_limit=100,
                      max_input_versions=64, max_input_bytes=64 * 1024 * 1024)
PERMISSIONS = {"broker_allowed": False, "manual_account_import_allowed": False,
               "automatic_step": False, "automatic_resume": False, "live_allowed": False}


class ReplayError(ValueError):
    pass


class ReplayRefusedNotApplied(ReplayError):
    """Only raised inside a transaction before any request/business write."""
    def __init__(self, reason, metadata):
        super().__init__(reason)
        self.reason,self.metadata=reason,deepcopy(metadata)


API_ACTIONS={'SEED':'seed','ADVANCE':'step','PAUSED':'pause','RECONCILED':'reconcile',
             'RESUMED':'resume','INPUT_ADOPTED':'adopt'}


def encoded(value):
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False, separators=(",", ":"))
    if len(raw) > 32 * 1024 * 1024:
        raise ReplayError("bounded_replay_document_required")
    return raw


def digest(value):
    return sha256(encoded(value).encode()).hexdigest()


def fields(value, expected):
    if type(value) is not dict or set(value) != set(expected):
        raise ReplayError("replay_fields_invalid")


def money(value, *, zero=False):
    if type(value) is not str or not re.fullmatch(r"(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,8})?", value):
        raise ReplayError("decimal_string_required")
    number = Decimal(value)
    if number < 0 or (not zero and number == 0) or number > Decimal("1000000000000"):
        raise ReplayError("bounded_nonnegative_money_required")
    return number


def amount(value):
    return format(value.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_EVEN), "f")


def positive_int(value, maximum=1000000):
    if type(value) is not int or not 1 <= value <= maximum:
        raise ReplayError("positive_bounded_integer_required")
    return value


def milliseconds(value):
    if type(value) is not int or not 0 < value < 32503680000000:
        raise ReplayError("original_event_clock_required")
    return value


def safe_path(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        try:
            info = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ReplayError("replay_reparse_path_rejected")
    return path


def validate_limits(value=None):
    value = deepcopy(DEFAULT_LIMITS if value is None else value)
    fields(value, DEFAULT_LIMITS)
    ranges = dict(max_events=(5,100000), control_reserve=(4,16), history_page_limit=(1,100),
                  max_input_versions=(1,256), max_input_bytes=(1024,512*1024*1024))
    for name,(low,high) in ranges.items():
        if type(value[name]) is not int or not low <= value[name] <= high:
            raise ReplayError("bounded_replay_limits_required:"+name)
    return value


def validate_data(value):
    required = {"security_id", "price_basis", "calendar_id", "observed_at", "corporate_actions", "evidence_kind", "bars"}
    if type(value) is not dict or set(value)-required-{"input_binding"} or required-set(value):
        raise ReplayError("replay_fields_invalid")
    if "input_binding" in value and (type(value["input_binding"]) is not dict or not value["input_binding"]):
        raise ReplayError("input_binding_invalid")
    for name in ("security_id", "calendar_id"):
        if type(value[name]) is not str or not 1 <= len(value[name]) <= 150:
            raise ReplayError("explicit_input_identity_required")
    if value["price_basis"] != "RAW_UNADJUSTED" or value["corporate_actions"] != []:
        raise ReplayError("action_free_raw_window_required_no_automatic_adjustment")
    if value["evidence_kind"] not in {"SYNTHETIC_TEST", "SAVED_MARKET_INPUT"}:
        raise ReplayError("explicit_input_evidence_kind_required")
    observed = milliseconds(value["observed_at"])
    bars = value["bars"]
    if type(bars) is not list or not 1 <= len(bars) <= MAX_BARS:
        raise ReplayError("bounded_complete_daily_bars_required")
    previous_date, previous_close = "", 0
    for row in bars:
        fields(row, {"date", "open_at", "close_at", "open", "high", "low", "close", "volume", "complete"})
        try:
            if date.fromisoformat(row["date"]).isoformat() != row["date"]:
                raise ValueError()
        except (ValueError, TypeError):
            raise ReplayError("session_date_invalid") from None
        if row["date"] <= previous_date or not previous_close < milliseconds(row["open_at"]) < milliseconds(row["close_at"]) <= observed or row["complete"] is not True:
            raise ReplayError("completed_strictly_ordered_original_sessions_required")
        prices = {key: money(row[key]) for key in ("open", "high", "low", "close")}
        if not prices["low"] <= min(prices["open"], prices["close"]) <= max(prices["open"], prices["close"]) <= prices["high"]:
            raise ReplayError("ohlc_bounds_invalid")
        money(row["volume"], zero=True)
        previous_date, previous_close = row["date"], row["close_at"]
    return deepcopy(value)


class HistoricalReplay:
    @classmethod
    def create(cls, path, *, account_id, initial_cash, unit_quantity, fee_rate, slippage_bps,
               strategy_binding, dataset, signal_fn, source_guard, clock=None, limits=None, creation_request=None):
        path = safe_path(path)
        if type(account_id) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}", account_id):
            raise ReplayError("new_replay_account_id_required")
        money(initial_cash); positive_int(unit_quantity)
        if money(fee_rate, zero=True) > Decimal("0.05") or money(slippage_bps, zero=True) > Decimal("1000"):
            raise ReplayError("bounded_explicit_model_costs_required")
        if type(strategy_binding) is not dict or not strategy_binding or not callable(signal_fn) or not callable(source_guard):
            raise ReplayError("trusted_bound_signal_engine_required")
        data = validate_data(dataset)
        limits = validate_limits(limits)
        if len(encoded(data).encode()) > limits["max_input_bytes"]:
            raise ReplayError("replay_input_capacity_reached")
        config = dict(model=MODEL, account_id=account_id, initial_cash=initial_cash, unit_quantity=unit_quantity,
                      fee_rate=fee_rate, slippage_bps=slippage_bps, strategy_binding=deepcopy(strategy_binding),
                      signal_binding_hash=digest(strategy_binding), model_implementation_sha256=LOADED_IMPLEMENTATION_SHA256,
                      limits=limits, creation_request=deepcopy(creation_request), permissions=dict(PERMISSIONS))
        if source_guard() != config["signal_binding_hash"]:
            raise ReplayError("loaded_signal_binding_mismatch")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb"):
            pass
        connection = sqlite3.connect(path)
        try:
            connection.executescript("""
                CREATE TABLE config(document TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TABLE datasets(id TEXT PRIMARY KEY, document TEXT NOT NULL);
                CREATE TABLE events(sequence INTEGER PRIMARY KEY, document TEXT NOT NULL, hash TEXT UNIQUE NOT NULL);
                CREATE TABLE requests(id TEXT PRIMARY KEY, action TEXT NOT NULL, payload TEXT NOT NULL, hash TEXT NOT NULL,
                                      status TEXT NOT NULL, intent_head TEXT NOT NULL, receipt TEXT, error TEXT);
            """)
            connection.execute("PRAGMA application_id=" + str(APP_ID))
            connection.execute("INSERT INTO config VALUES(?,?)", (encoded(config), digest(config)))
            connection.execute("INSERT INTO datasets VALUES(?,?)", (digest(data), encoded(data)))
            state = dict(dataset_id=digest(data), cursor=None, event_at=None, cash=amount(money(initial_cash)),
                         quantity=0, entry_price=None, pending_signal=None, paused=False, pause_reason=None)
            recorded = (clock or (lambda: datetime.now(timezone.utc)))().isoformat()
            event = dict(sequence=1, previous_hash=ZERO, kind="CREATED", payload={}, state_after=state, recorded_at=recorded)
            connection.execute("INSERT INTO events VALUES(?,?,?)", (1, encoded(event), digest(event)))
            if source_guard() != config["signal_binding_hash"] or sha256(Path(__file__).read_bytes()).hexdigest()!=LOADED_IMPLEMENTATION_SHA256:
                raise ReplayError("source_changed_before_creation_commit")
            connection.commit()
        finally:
            connection.close()
        result = cls(path, signal_fn=signal_fn, source_guard=source_guard, clock=clock)
        result.creation_head=digest(event)
        result._reconciled_head = result.creation_head
        return result

    def __init__(self, path, *, signal_fn, source_guard, clock=None, readonly=False):
        self.path = safe_path(path)
        if not self.path.is_file():
            raise ReplayError("existing_new_replay_store_required")
        self.db = sqlite3.connect(self.path.as_uri() + ("?mode=ro" if readonly else "?mode=rw"), uri=True, isolation_level=None, timeout=3, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        if self.db.execute("PRAGMA application_id").fetchone()[0] != APP_ID:
            self.db.close(); raise ReplayError("manual_or_foreign_account_store_rejected")
        self.signal_fn, self.source_guard = signal_fn, source_guard
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock, self._pause_requested, self._working = RLock(), Event(), set()
        self._reconciled_head = None
        self.config = json.loads(self.db.execute("SELECT document FROM config").fetchone()[0])
        try:self._verify()
        except BaseException:
            self.db.close();raise

    def close(self):
        with self._lock:
            if self._working:raise ReplayError('operation_still_processing')
            self.db.close()

    def _time(self):
        value = self.clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise ReplayError("aware_recording_clock_required")
        return value.astimezone(timezone.utc).isoformat()

    def _data(self, identity):
        row = self.db.execute("SELECT document FROM datasets WHERE id=?", (identity,)).fetchone()
        if row is None: raise ReplayError("saved_input_version_missing")
        data = validate_data(json.loads(row[0]))
        if digest(data) != identity: raise ReplayError("saved_input_version_changed")
        return data

    def _head(self):
        row = self.db.execute("SELECT document,hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        return row["hash"], json.loads(row["document"])["state_after"]

    def _append(self, kind, payload, state):
        row = self.db.execute("SELECT sequence,hash FROM events ORDER BY sequence DESC LIMIT 1").fetchone()
        limit = self.config["limits"]["max_events"]
        if kind in {"PAUSED", "RECONCILED"}: limit += self.config["limits"]["control_reserve"]
        if row["sequence"] >= limit:
            raise ReplayError("replay_event_capacity_reached_existing_state_retained")
        event = dict(sequence=row["sequence"] + 1, previous_hash=row["hash"], kind=kind,
                     payload=deepcopy(payload), state_after=deepcopy(state), recorded_at=self._time())
        identity = digest(event)
        self.db.execute("INSERT INTO events VALUES(?,?,?)", (event["sequence"], encoded(event), identity))
        return identity

    def _guard(self):
        if (self.config["model_implementation_sha256"] != LOADED_IMPLEMENTATION_SHA256
                or sha256(Path(__file__).read_bytes()).hexdigest() != LOADED_IMPLEMENTATION_SHA256):
            raise ReplayError("replay_implementation_changed_new_steps_blocked")
        if self.source_guard() != self.config["signal_binding_hash"]:
            raise ReplayError("signal_source_changed_restart_or_new_replay_required")

    def _capacity(self, needed=2):
        count = self.db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        return dict(events=count, business_limit=self.config["limits"]["max_events"],
                    total_limit=self.config["limits"]["max_events"]+self.config["limits"]["control_reserve"],
                    reached=count+needed>self.config["limits"]["max_events"], preserved_events=True)

    def _pending(self):
        return [dict(row) for row in self.db.execute("SELECT id,action,error FROM requests WHERE status='PENDING' ORDER BY rowid")]

    def _api_metadata(self, request_id, action, payload, *, dataset=None):
        if '_api' not in payload:return None
        api=payload['_api'];fields(api,{'action','payload','hash'})
        expected=dict(account_id=self.config['account_id'],request_id=request_id,
                      **{key:value for key,value in payload.items() if key!='_api'})
        if action=='INPUT_ADOPTED':
            data=self._data(payload['input_id']) if dataset is None else dataset
            native_id=data.get('input_binding',{}).get('native_input_id')
            if type(native_id) is not str or not re.fullmatch('[a-f0-9]{64}',native_id):
                raise ReplayError('api_adopt_native_input_binding_missing')
            expected['input_id']=native_id
        if (api['action']!=API_ACTIONS.get(action) or type(api['payload']) is not dict
                or encoded(api['payload'])!=encoded(expected) or api['hash']!=digest(api['payload'])):
            raise ReplayError('api_request_binding_changed')
        return dict(account_id=self.config['account_id'],request_id=request_id,
                    request_action=api['action'],request_hash=api['hash'])

    def _with_api(self, request_id, action, payload, api_request, *, dataset=None):
        if api_request is not None:
            payload=dict(payload,_api=deepcopy(api_request))
            self._api_metadata(request_id,action,payload,dataset=dataset)
        return payload

    def _refuse_before_write(self, request_id, action, payload, reason):
        # Call sites below hold BEGIN IMMEDIATE, have verified the whole store,
        # and have not called _append/INSERT/operation/commit for this request.
        if request_id in self._working or self.db.execute('SELECT 1 FROM requests WHERE id=?',(request_id,)).fetchone():
            raise ReplayError('refusal_requires_absent_original_request')
        api=payload.get('_api')
        # _with_api already checked the caller's original payload, including
        # a not-yet-inserted adoption dataset. Do not read that future dataset.
        metadata=None if api is None else dict(account_id=self.config['account_id'],request_id=request_id,
                                               request_action=api['action'],request_hash=api['hash'])
        raise ReplayRefusedNotApplied(reason,metadata)

    def _verified_request(self, request_id, action, payload):
        if type(request_id) is not str or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{7,119}", request_id):
            raise ReplayError("bounded_request_id_required")
        request_hash = digest(dict(action=action, payload=payload))
        self._verify()
        old = self.db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
        if old is not None:
            if old["hash"] != request_hash:
                raise ReplayError("request_id_conflict")
            if old["receipt"] is not None: return request_hash, json.loads(old["receipt"])
            raise ReplayError("pending_intent_requires_explicit_reconciliation_no_replay")
        return request_hash, None

    def _ready(self, expected_head, *, allow_paused=False, refusal_context=None):
        self._verify()
        head, state = self._head()
        if head != expected_head:
            if refusal_context is not None:self._refuse_before_write(*refusal_context,'expected_head_changed')
            raise ReplayError("expected_head_changed")
        if self._pending() or self._reconciled_head != head:
            raise ReplayError("explicit_reconciliation_required")
        if not allow_paused and (state["paused"] or self._pause_requested.is_set()):
            raise ReplayError("replay_paused")
        return head, state

    def _fault(self, phase):
        """Test seam; never selectable in request payloads."""

    def _begin(self, request_id, action, payload, expected_head):
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                request_hash, old = self._verified_request(request_id, action, payload)
                if old is not None:
                    self.db.rollback(); return None, None, old
                if self._capacity()["reached"]:
                    raise ReplayError("replay_event_capacity_reached_new_account_required")
                _, state = self._ready(expected_head,refusal_context=(request_id,action,payload))
                data = self._data(state["dataset_id"])
                if action == "SEED":
                    if state["cursor"] is not None: raise ReplayError("seed_already_recorded")
                    index = positive_int(payload["seed_count"], len(data["bars"])) - 1
                else:
                    if state["cursor"] is None: raise ReplayError("explicit_seed_close_required")
                    index = state["cursor"] + 1
                    if index >= len(data["bars"]): raise ReplayError("waiting_for_next_complete_saved_bar")
                intent = dict(request_id=request_id, action=action, request_hash=request_hash, before_head=expected_head,
                              dataset_id=state["dataset_id"], index=index, bar_hash=digest(data["bars"][index]))
                intent_head = self._append("INTENT_RECORDED", intent, state)
                self.db.execute("INSERT INTO requests VALUES(?,?,?,?,?,?,NULL,NULL)",
                    (request_id, action, encoded(payload), request_hash, "PENDING", intent_head))
                self.db.commit()
                self._working.add(request_id)
                return intent, state, None
            except BaseException:
                self.db.rollback(); raise

    def _signal(self, data, index, state):
        self._guard()
        prefix = deepcopy(data["bars"][:index + 1])
        position = dict(quantity=state["quantity"], has_position=state["quantity"] > 0, entry_price=state["entry_price"])
        result = self.signal_fn(prefix, deepcopy(position))
        self._guard()
        if type(result) is not dict or result.get("action") not in {"BUY", "EXIT", "HOLD"} or type(result.get("reason")) is not str:
            raise ReplayError("bound_long_only_signal_required")
        if result.get("validation_blocker") or result["reason"] in {"unsupported_strategy", "invalid_indicator_history", "invalid_bar_history", "signal_input_mismatch"}:
            raise ReplayError("signal_rule_not_eligible")
        if (result["action"] == "BUY" and state["quantity"]) or (result["action"] == "EXIT" and not state["quantity"]):
            raise ReplayError("signal_position_context_conflict")
        return dict(value=deepcopy(result), signal_at=prefix[-1]["close_at"], prefix_hash=digest(prefix),
                    signal_binding_hash=self.config["signal_binding_hash"])

    def _opening(self, previous, bar):
        state = deepcopy(previous)
        signal = previous["pending_signal"]
        if signal["signal_at"] >= bar["open_at"]: raise ReplayError("next_open_must_follow_signal_close")
        action = signal["value"]["action"]
        result = dict(status="NO_ORDER", action=action, signal_at=signal["signal_at"], execution_at=bar["open_at"],
                      quantity=0, fill_price=None, fee="0.00000000", model=MODEL, evidence_kind="HISTORICAL_REPLAY_SYNTHETIC_FILL")
        if action == "HOLD": return state, result
        quantity = self.config["unit_quantity"] if action == "BUY" else state["quantity"]
        if (action == "BUY" and state["quantity"]) or quantity <= 0: raise ReplayError("pending_signal_position_conflict")
        slip = money(self.config["slippage_bps"], zero=True) / 10000
        price = Decimal(amount(money(bar["open"]) * (1 + slip if action == "BUY" else 1 - slip)))
        notional = price * quantity
        fee = Decimal(amount(notional * money(self.config["fee_rate"], zero=True)))
        cash = money(state["cash"], zero=True)
        if action == "BUY" and cash < notional + fee:
            result["status"] = "REJECTED_INSUFFICIENT_CASH"
            return state, result
        resulting_cash = amount(cash - notional - fee if action == "BUY" else cash + notional - fee)
        money(resulting_cash, zero=True)
        state.update(cash=resulting_cash,
                     quantity=quantity if action == "BUY" else 0, entry_price=amount(price) if action == "BUY" else None)
        result.update(status="FILLED_BY_DECLARED_REPLAY_MODEL", quantity=quantity, fill_price=amount(price), fee=amount(fee))
        return state, result

    def _step(self, request_id, action, expected_head, seed_count=None, api_request=None):
        payload = dict(expected_head=expected_head, **({"seed_count": seed_count} if action == "SEED" else {}))
        payload=self._with_api(request_id,action,payload,api_request)
        self._guard()
        intent, before, old = self._begin(request_id, action, payload, expected_head)
        if old is not None: return old
        try:
            self._fault("after_intent")
            data, index = self._data(intent["dataset_id"]), intent["index"]
            state, fill = (deepcopy(before), None) if action == "SEED" else self._opening(before, data["bars"][index])
            signal = self._signal(data, index, state)
            state.update(cursor=index, event_at=data["bars"][index]["close_at"], pending_signal=signal)
            self._fault("after_calculation")
            with self._lock:
                self.db.execute("BEGIN IMMEDIATE")
                try:
                    self._guard()
                    row = self.db.execute("SELECT intent_head,status FROM requests WHERE id=?", (request_id,)).fetchone()
                    if row["status"] != "PENDING" or self._head()[0] != row["intent_head"] or self._pause_requested.is_set():
                        raise ReplayError("head_or_pause_changed_reconciliation_required")
                    outcome = dict(status="SEED_SIGNAL_ONLY" if action == "SEED" else "ONE_BAR_APPLIED", index=index, fill=fill, signal=signal)
                    if self._capacity(1)["events"]+1 >= self.config["limits"]["max_events"]:
                        state.update(paused=True, pause_reason="EVENT_CAPACITY_REACHED")
                    head = self._append("SEED_APPLIED" if action == "SEED" else "STEP_APPLIED",
                        dict(request_id=request_id, outcome=outcome), state)
                    receipt = dict(request_id=request_id, head=head, outcome=outcome, automatic_next_step=False)
                    self.db.execute("UPDATE requests SET status='APPLIED',receipt=? WHERE id=?", (encoded(receipt), request_id))
                    self.db.commit(); self._reconciled_head = head
                except BaseException:
                    self.db.rollback(); raise
            self._fault("after_commit")
            return receipt
        except Exception as error:
            with self._lock:
                self.db.execute("UPDATE requests SET error=? WHERE id=? AND status='PENDING'", (type(error).__name__ + ":" + str(error)[:200], request_id))
            raise
        finally:
            with self._lock:
                self._working.discard(request_id)

    def seed_close(self, request_id, *, expected_head, seed_count, api_request=None):
        return self._step(request_id, "SEED", expected_head, seed_count,api_request)

    def advance_next(self, request_id, *, expected_head, api_request=None):
        return self._step(request_id, "ADVANCE", expected_head,api_request=api_request)

    def _control(self, request_id, action, payload, operation):
        with self._lock:
            self.db.execute("BEGIN IMMEDIATE")
            try:
                request_hash, old = self._verified_request(request_id, action, payload)
                if old is not None:
                    self.db.rollback(); return old
                if action not in {"PAUSED","RECONCILED"} and self._capacity()["reached"]:
                    raise ReplayError("replay_event_capacity_reached_new_account_required")
                self._verify()
                head, state = self._head()
                if head != payload["expected_head"]:
                    active=payload.get("in_flight_request_id") if action=="PAUSED" else None
                    row=self.db.execute("SELECT * FROM requests WHERE id=?",(active,)).fetchone() if active else None
                    if not (row and row['status']=='PENDING' and row['intent_head']==head
                            and json.loads(row['payload'])['expected_head']==payload['expected_head']):
                        self._refuse_before_write(request_id,action,payload,'expected_head_changed')
                outcome, state = operation(head, state)
                head = self._append(action, dict(request_id=request_id, request_hash=request_hash, outcome=outcome), state)
                receipt = dict(request_id=request_id, head=head, outcome=outcome, automatic_next_step=False)
                self.db.execute("INSERT INTO requests VALUES(?,?,?,?,?,?,?,NULL)",
                    (request_id, action, encoded(payload), request_hash, "APPLIED", head, encoded(receipt)))
                self.db.commit(); self._reconciled_head = head if not self._pending() else None
                return receipt
            except BaseException:
                self.db.rollback(); raise

    def pause(self, request_id, *, expected_head, reason, in_flight_request_id=None, api_request=None):
        if type(reason) is not str or not 1 <= len(reason) <= 200: raise ReplayError("explicit_pause_reason_required")
        def operation(head, state):
            state.update(paused=True, pause_reason=reason)
            return dict(status="PAUSED", broker_orders_cancelled=False), state
        payload=dict(expected_head=expected_head, reason=reason,
            **({'in_flight_request_id':in_flight_request_id} if in_flight_request_id is not None else {}))
        result = self._control(request_id, "PAUSED", self._with_api(request_id,'PAUSED',payload,api_request), operation)
        self._pause_requested.set()
        return result

    def reconcile(self, request_id, *, expected_head, api_request=None):
        def operation(head, state):
            if self._working: raise ReplayError("operation_still_processing")
            pending = self._pending()
            for row in pending:
                receipt = dict(request_id=row["id"], head=head, outcome={"status": "ABANDONED_NOT_APPLIED_AFTER_RECONCILIATION"}, automatic_next_step=False)
                self.db.execute("UPDATE requests SET status='ABANDONED',receipt=? WHERE id=?", (encoded(receipt), row["id"]))
            state.update(paused=True, pause_reason="RECONCILED_REQUIRES_EXPLICIT_RESUME")
            return dict(status="RECONCILED_PAUSED", abandoned_request_ids=[r["id"] for r in pending], recomputed_steps=0), state
        result = self._control(request_id, "RECONCILED", self._with_api(request_id,'RECONCILED',dict(expected_head=expected_head),api_request), operation)
        self._pause_requested.set()
        return result

    def resume(self, request_id, *, expected_head, api_request=None):
        def operation(head, state):
            self._ready(head, allow_paused=True); self._guard()
            state.update(paused=False, pause_reason=None)
            return dict(status="EXPLICITLY_RESUMED_NO_STEP", computed_steps=0), state
        result = self._control(request_id, "RESUMED", self._with_api(request_id,'RESUMED',dict(expected_head=expected_head),api_request), operation)
        self._pause_requested.clear()
        return result

    def adopt_input(self, request_id, *, expected_head, dataset, api_request=None):
        data = validate_data(dataset)
        def operation(head, state):
            self._ready(head, allow_paused=True)
            self._guard()
            old = self._data(state["dataset_id"])
            for key in ("security_id", "price_basis", "calendar_id", "corporate_actions", "evidence_kind"):
                if old[key] != data[key]: raise ReplayError("replay_input_context_changed_new_account_required")
            protected = 0 if state["cursor"] is None else state["cursor"] + 1
            if old["bars"][:protected] != data["bars"][:protected]:
                raise ReplayError("consumed_prefix_revision_requires_new_replay")
            identity = digest(data)
            if not self.db.execute("SELECT 1 FROM datasets WHERE id=?",(identity,)).fetchone():
                count,size = self.db.execute("SELECT COUNT(*),COALESCE(SUM(LENGTH(CAST(document AS BLOB))),0) FROM datasets").fetchone()
                if count >= self.config["limits"]["max_input_versions"] or size+len(encoded(data).encode()) > self.config["limits"]["max_input_bytes"]:
                    raise ReplayError("replay_input_capacity_reached_existing_versions_retained")
            self.db.execute("INSERT OR IGNORE INTO datasets VALUES(?,?)", (identity, encoded(data)))
            self._guard()
            state["dataset_id"] = identity
            return dict(status="INPUT_VERSION_ADOPTED_NO_STEP", input_id=identity, protected_prefix_rows=protected), state
        payload=self._with_api(request_id,'INPUT_ADOPTED',dict(expected_head=expected_head,input_id=digest(data)),api_request,dataset=data)
        return self._control(request_id, "INPUT_ADOPTED", payload, operation)

    def snapshot(self):
        with self._lock:
            self._verify()
            head, state = self._head(); pending = self._pending()
            data = self._data(state["dataset_id"])
            phase = ("PROCESSING" if self._working else "ERROR_RECONCILIATION_REQUIRED" if any(p["error"] for p in pending)
                     else "RECOVERY_REQUIRED" if pending or self._reconciled_head != head
                     else "CAPACITY_PAUSED" if self._capacity()["reached"] else "PAUSED" if state["paused"] else "SEED_REQUIRED" if state["cursor"] is None
                     else "WAITING_DATA" if state["cursor"] + 1 >= len(data["bars"]) else "READY_FOR_EXPLICIT_STEP")
            return dict(model=MODEL, account_id=self.config["account_id"], head=head, phase=phase, state=deepcopy(state),
                last_session=None if state['cursor'] is None else deepcopy(data['bars'][state['cursor']]),
                next_session=None if state['cursor'] is None or state['cursor']+1>=len(data['bars']) else deepcopy(data['bars'][state['cursor']+1]),
                session_count=len(data['bars']),
                input_evidence_kind=data["evidence_kind"],
                capacity=self._capacity(), model_implementation_sha256=self.config["model_implementation_sha256"],
                implementation_compatible=self.config["model_implementation_sha256"]==LOADED_IMPLEMENTATION_SHA256,
                pending_intents=pending, next_step_automatic=False, permissions=dict(PERMISSIONS),
                interpretation="独立整股、下一日线开盘合成模型；不等同原生回测或券商成交。")

    def receipt(self, request_id):
        with self._lock:
            self._verify()
            row = self.db.execute("SELECT * FROM requests WHERE id=?", (request_id,)).fetchone()
            if row is None: raise ReplayError("request_not_found")
            result=json.loads(row["receipt"]) if row["receipt"] else dict(request_id=request_id, status=row["status"], error=row["error"], automatic_next_step=False)
            metadata=self._api_metadata(request_id,row['action'],json.loads(row['payload']))
            if metadata is not None:result.update(metadata)
            return result

    def history(self, *, after_sequence=0, limit=None, expected_head=None):
        with self._lock:
            self._verify()
            if limit is None: limit=min(50,self.config["limits"]["history_page_limit"])
            if type(after_sequence) is not int or after_sequence < 0 or type(limit) is not int or not 1 <= limit <= self.config["limits"]["history_page_limit"]:
                raise ReplayError("bounded_history_cursor_and_limit_required")
            head=self._head()[0]
            if expected_head is not None and head != expected_head: raise ReplayError("history_head_changed_refresh_required")
            rows=list(self.db.execute("SELECT * FROM events WHERE sequence>? ORDER BY sequence LIMIT ?",(after_sequence,limit+1)))
            items=[dict(json.loads(r["document"]),hash=r["hash"]) for r in rows[:limit]]
            return dict(items=items,head=head,has_more=len(rows)>limit,next_after=items[-1]["sequence"] if items else after_sequence)

    def _verify(self):
        validate_limits(self.config["limits"])
        config = self.db.execute("SELECT * FROM config").fetchone()
        if config["hash"] != digest(self.config) or json.loads(config["document"]) != self.config or self.config["model"] != MODEL:
            raise ReplayError("replay_configuration_changed")
        previous, state, events = ZERO, None, {}
        for sequence, row in enumerate(self.db.execute("SELECT * FROM events ORDER BY sequence"), 1):
            event = json.loads(row["document"])
            if row["sequence"] != sequence or event["sequence"] != sequence or event["previous_hash"] != previous or digest(event) != row["hash"]:
                raise ReplayError("replay_event_chain_changed")
            after = event["state_after"]; data = self._data(after["dataset_id"])
            money(after["cash"], zero=True)
            if type(after["quantity"]) is not int or not 0 <= after["quantity"] <= self.config["unit_quantity"]:
                raise ReplayError("replay_position_invalid")
            kind = event["kind"]
            if kind == "CREATED":
                initial = dict(dataset_id=after["dataset_id"], cursor=None, event_at=None,
                    cash=amount(money(self.config["initial_cash"])), quantity=0, entry_price=None,
                    pending_signal=None, paused=False, pause_reason=None)
                if sequence != 1 or after != initial: raise ReplayError("replay_genesis_changed")
            elif state is None:
                raise ReplayError("replay_genesis_missing")
            if kind == "STEP_APPLIED":
                index = event["payload"]["outcome"]["index"]
                if index != state["cursor"] + 1 or after["cursor"] != index or state["dataset_id"] != after["dataset_id"]:
                    raise ReplayError("replay_cursor_changed")
                calculated, fill = self._opening(state, data["bars"][index])
                if fill != event["payload"]["outcome"]["fill"] or any(after[key] != calculated[key] for key in ("cash", "quantity", "entry_price")):
                    raise ReplayError("replay_fill_or_accounting_changed")
            elif state is not None and any(after[key] != state[key] for key in ("cash", "quantity", "entry_price")):
                raise ReplayError("non_step_event_changed_accounting")
            if kind == "SEED_APPLIED":
                outcome = event["payload"]["outcome"]
                if state["cursor"] is not None or after["cursor"] != outcome["index"] or outcome["fill"] is not None:
                    raise ReplayError("replay_seed_changed")
            if kind in {"STEP_APPLIED", "SEED_APPLIED"}:
                if event["payload"]["outcome"]["signal"] != after["pending_signal"]:
                    raise ReplayError("replay_signal_receipt_changed")
            elif kind in {"INTENT_RECORDED", "PAUSED", "RESUMED", "RECONCILED", "INPUT_ADOPTED"}:
                for key in ("cursor", "event_at", "pending_signal"):
                    if after[key] != state[key]: raise ReplayError("control_changed_replay_progress")
                if kind != "INPUT_ADOPTED" and after["dataset_id"] != state["dataset_id"]:
                    raise ReplayError("control_changed_replay_input")
                if kind == "INTENT_RECORDED" and after != state:
                    raise ReplayError("intent_changed_state_before_commit")
            elif kind != "CREATED":
                raise ReplayError("unknown_replay_event_kind")
            if after["cursor"] is not None:
                prefix = data["bars"][:after["cursor"] + 1]
                signal = after["pending_signal"]
                if (not prefix or after["event_at"] != prefix[-1]["close_at"] or signal["signal_at"] != after["event_at"]
                        or signal["prefix_hash"] != digest(prefix) or signal["signal_binding_hash"] != self.config["signal_binding_hash"]):
                    raise ReplayError("replay_signal_prefix_or_event_clock_changed")
            previous, state = row["hash"], after
            events[previous] = event
        for row in self.db.execute("SELECT * FROM requests"):
            if row["hash"] != digest(dict(action=row["action"], payload=json.loads(row["payload"]))):
                raise ReplayError("replay_request_changed")
            intent = events.get(row["intent_head"])
            if intent is None or intent["payload"].get("request_id") != row["id"]:
                raise ReplayError("request_intent_missing")
            stored_payload=json.loads(row['payload'])
            self._api_metadata(row['id'],row['action'],stored_payload)
            if row["action"] in {"SEED", "ADVANCE"}:
                if intent["kind"] != "INTENT_RECORDED" or intent["payload"]["request_hash"] != row["hash"]:
                    raise ReplayError("request_intent_binding_changed")
                stored_payload = json.loads(row["payload"])
                context = intent["payload"]
                data = self._data(context["dataset_id"])
                index = stored_payload["seed_count"] - 1 if row["action"] == "SEED" else intent["state_after"]["cursor"] + 1
                if (context["action"] != row["action"] or context["before_head"] != stored_payload["expected_head"]
                        or context["before_head"] != intent["previous_hash"] or context["index"] != index
                        or context["dataset_id"] != intent["state_after"]["dataset_id"]
                        or context["bar_hash"] != digest(data["bars"][index])):
                    raise ReplayError("request_frozen_bar_or_expected_head_changed")
            else:
                control=stored_payload
                direct=events.get(intent['previous_hash'])
                paused_pending=(row['action']=='PAUSED' and control.get('in_flight_request_id')
                    and direct and direct['kind']=='INTENT_RECORDED'
                    and direct['payload']['request_id']==control['in_flight_request_id']
                    and direct['previous_hash']==control['expected_head'])
                if intent['kind']!=row['action'] or (intent['previous_hash']!=control['expected_head'] and not paused_pending):
                    raise ReplayError('control_request_binding_changed')
                if ('request_hash' in intent['payload'] or '_api' in control) and intent['payload'].get('request_hash')!=row['hash']:
                    raise ReplayError('control_request_hash_changed')
            if row['receipt'] is not None:
                saved_receipt=json.loads(row['receipt'])
                if (type(saved_receipt) is not dict or set(saved_receipt)!={'request_id','head','outcome','automatic_next_step'}
                        or saved_receipt['request_id']!=row['id'] or saved_receipt['automatic_next_step'] is not False
                        or row['status']=='PENDING'):
                    raise ReplayError('request_receipt_changed')
            if row["status"] == "APPLIED":
                receipt = json.loads(row["receipt"])
                applied = events.get(receipt["head"])
                if not applied or applied["payload"].get("request_id") != row["id"] or applied["payload"].get("outcome") != receipt["outcome"]:
                    raise ReplayError("request_receipt_changed")
            elif row["status"] not in {"PENDING", "ABANDONED"}:
                raise ReplayError("request_status_invalid")
            elif row["status"] == "ABANDONED":
                receipt = json.loads(row["receipt"])
                if (receipt["request_id"] != row["id"] or receipt["outcome"] != {"status": "ABANDONED_NOT_APPLIED_AFTER_RECONCILIATION"}
                        or not any(e["kind"] == "RECONCILED" and row["id"] in e["payload"]["outcome"]["abandoned_request_ids"] for e in events.values())):
                    raise ReplayError("abandoned_intent_reconciliation_missing")
