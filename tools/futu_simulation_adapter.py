"""Futu SIMULATE transport around the existing durable intent state machine.

Not installed by the research wheel. The CLI is read-only. Order methods require
an explicit, expiring operator declaration bound to an exact account and intent.
Futu simulation has no deal/fee API: an order observation alone never supplies a
zero fee, a completed accounting observation, or an atomic account snapshot.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import queue
import re
import time

_spec = importlib.util.spec_from_file_location("futu_execution_core", Path(__file__).with_name("execution_state_lab.py"))
core = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(core)
Error = core.StateError
MODE = "FUTU_OFFICIAL_SIMULATE"
SDK_VERSION = "10.7.6708"
ORDER_FIELDS = ("order_id", "code", "trd_side", "order_type", "order_status", "qty", "price",
                "dealt_qty", "dealt_avg_price", "remark", "updated_time", "time_in_force")
STATES = {"SUBMITTED": "WORKING", "FILLED_PART": "PARTIAL", "FILLED_ALL": "FILLED",
          "CANCELLED_PART": "CANCELLED", "CANCELLED_ALL": "CANCELLED", "FAILED": "REJECTED", "SUBMIT_FAILED": "REJECTED", "DISABLED": "EXPIRED"}


def stamp():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def exact_id(value):
    if type(value) is not str or not re.fullmatch(r"[1-9][0-9]{0,19}", value) or int(value)>=2**64:
        raise Error("explicit_nonzero_account_or_order_id_required")
    return value


def decimal_text(value):
    if type(value) not in (str, int, float) or isinstance(value, bool):
        raise Error("provider_numeric_type_invalid")
    try:number = Decimal(str(value))
    except InvalidOperation as exc:raise Error('provider_numeric_value_invalid') from exc
    if not number.is_finite() or abs(number)>Decimal('1e20') or number.as_tuple().exponent < -16:
        raise Error("provider_finite_value_required")
    return core.formatted(number)


def whole(value, *, zero=False):
    number = Decimal(decimal_text(value))
    if number != number.to_integral_value():
        raise Error("provider_fractional_quantity_not_supported")
    return core.quantity(int(number), zero=zero)


def binding(value):
    if (type(value) is not dict or set(value) != {"schema_version", "account_id", "market", "symbol", "host", "port", "history_start"}
            or value["schema_version"] != "futu-simulation-binding-v1" or value["market"] != "US"
            or value["symbol"] != "US.AMD" or value["host"] != "127.0.0.1"
            or type(value["port"]) is not int or value["port"] != 11111):
        raise Error("explicit_local_us_amd_simulation_binding_required")
    exact_id(value["account_id"])
    try:
        day = datetime.strptime(value["history_start"], "%Y-%m-%d").date()
    except (TypeError, ValueError) as exc:
        raise Error("explicit_history_start_required") from exc
    if not 0 <= (datetime.now(timezone.utc).date() - day).days <= 30:
        raise Error("bounded_simulation_history_window_required")
    return dict(value)


def rows(data):
    if type(data) is list:  # deterministic contract fixtures, never live acceptance
        result = data
    elif hasattr(data, "to_json"):
        result = json.loads(data.to_json(orient="records", double_precision=15))
    else:
        raise Error("provider_dataframe_required")
    if len(result) >= 10000 or any(type(row) is not dict for row in result):
        raise Error("provider_result_completeness_not_established")
    return result


def order_projection(row):
    if any(key not in row for key in ORDER_FIELDS):
        raise Error("provider_order_fields_missing")
    value = {key: row[key] for key in ORDER_FIELDS}
    value["order_id"] = exact_id(str(value["order_id"]))
    value["qty"], value["dealt_qty"] = whole(value["qty"]), whole(value["dealt_qty"], zero=True)
    value["price"], value["dealt_avg_price"] = decimal_text(value["price"]), decimal_text(value["dealt_avg_price"])
    if value["dealt_qty"] > value["qty"] or Decimal(value["price"]) <= 0:
        raise Error("provider_order_quantity_or_price_invalid")
    return value


class SimulationStore(core.ExecutionStore):
    mode = MODE
    application_id = 0x48465331
    reconciliation_scope = "FUTU_STABLE_SCOPED_READS_NOT_ATOMIC"
    rule_authority = "EXPLICIT_FUTU_SIMULATION_INSTRUMENT_RULES"
    allow_untradable_seed_positions = True

    def __init__(self,path):
        super().__init__(path)
        self.path=Path(path).resolve(strict=True)

    @classmethod
    def create_bound(cls, path, *, profile, cash, holdings, max_order_notional, fee_reserve, anchor):
        profile = binding(profile)
        if (type(anchor) is not dict or anchor.get('scope')!='REPEATED_SCOPED_READS_NOT_ATOMIC'
                or anchor.get('binding_sha256')!=core.fingerprint(profile)
                or anchor.get('projection_sha256')!=core.fingerprint(anchor.get('value'))
                or anchor['value']!={'cash':cash,'positions':holdings,'orders':[]}):
            raise Error('fresh_bound_empty_order_account_anchor_required')
        anchored_at=datetime.fromisoformat(anchor['checked_at'].replace('Z','+00:00'))
        if not 0 <= (datetime.now(timezone.utc)-anchored_at).total_seconds() <= 60:
            raise Error('stale_account_anchor')
        # Retain pre-existing holdings as the explicit starting account anchor;
        # only the bound AMD symbol is permitted for newly prepared intents.
        symbols = {profile["symbol"]: "0.01"}
        if any(not re.fullmatch(r"US\.[A-Z][A-Z0-9.]{0,15}", symbol) for symbol in holdings):
            raise Error("unrecognized_initial_instrument")
        store = cls.create(path, cash=cash, holdings=holdings, symbols=symbols,
                           max_order_notional=max_order_notional, fee_reserve=fee_reserve)
        with core.transaction(store.db):
            store.config["futu_binding"] = profile
            store.config['futu_store_id']=core.uuid.uuid4().hex
            store.config['futu_anchor']=anchor
            store.db.execute("UPDATE meta SET config=?", (core.encoded(store.config),))
            store.db.execute("CREATE TABLE futu_orders(order_id TEXT PRIMARY KEY, projection TEXT NOT NULL, evidence TEXT NOT NULL, admitted_projection_hash TEXT)")
            store.db.execute('CREATE TABLE futu_statement_sources(sha256 TEXT PRIMARY KEY, content BLOB NOT NULL)')
            store._event("FUTU_ACCOUNT_BOUND", {"binding_hash": core.fingerprint(profile), "anchor_receipt_hash":core.fingerprint(anchor),
                "anchor_scope":"REPEATED_READS_NOT_ATOMIC_OR_AUTHENTICATED_BY_HASH"})
        return store

    @property
    def profile(self):
        return binding(self.config.get("futu_binding"))

    def prepare(self, intent_id, *, symbol, side, quantity_value, limit_price):
        if symbol != self.profile["symbol"] or quantity_value != 1 or type(quantity_value) is not int:
            raise Error("first_official_cycle_requires_one_bound_amd_share")
        if core.amount(limit_price) < 1:
            raise Error("first_cycle_price_at_least_one_usd_required")
        return super().prepare(intent_id, symbol=symbol, side=side, quantity_value=quantity_value, limit_price=limit_price)

    def observe_order(self, raw, *, origin):
        try:
            return self._observe_order(raw, origin=origin)
        except (Error, core.sqlite3.IntegrityError) as exc:
            # Persist the stop outside the rolled-back observation transaction.
            with core.transaction(self.db):
                try:self._event('FUTU_ORDER_REJECTED',{'origin':origin,'raw':raw,'error_type':type(exc).__name__})
                except (TypeError,ValueError):self._event('FUTU_ORDER_REJECTED',{'origin':origin,'raw_unserializable':True})
                self._halt("futu_order_evidence_conflict",raw)
            raise

    def _observe_order(self, raw, *, origin):
        """Persist identity/status immediately; leave accounting UNKNOWN."""
        value = order_projection(raw)
        with core.transaction(self.db):
            row = self.db.execute("SELECT * FROM orders WHERE client_id=?", (value["remark"],)).fetchone()
            if row is None or row["claim_id"] is None:
                self._halt("unrecognized_futu_order", raw)
                raise Error("unrecognized_futu_order")
            payload = json.loads(row["payload"])
            if (value["code"] != payload["symbol"] or value["trd_side"] != payload["side"]
                    or value["qty"] != payload["quantity"] or Decimal(value["price"]) != core.amount(payload["limit_price"])
                    or value["order_type"] != "NORMAL" or value["time_in_force"] != "DAY"
                    or row["broker_id"] not in (None, value["order_id"])):
                raise Error("futu_order_binding_or_terms_conflict")
            old = self.db.execute("SELECT projection FROM futu_orders WHERE order_id=?", (value["order_id"],)).fetchone()
            self._event("FUTU_ORDER_RAW", {"origin": origin, "raw": raw, "fee": None, "deal_evidence": None})
            if old:
                previous = json.loads(old[0])
                if value["dealt_qty"] < previous["dealt_qty"]:
                    return "STALE_RETAINED"
                if value["updated_time"] < previous["updated_time"]:
                    return "STALE_RETAINED"
                if value == previous:
                    return "DUPLICATE_RETAINED"
                if value["updated_time"] == previous["updated_time"] and value["dealt_qty"] == previous["dealt_qty"] and value["dealt_avg_price"] != previous["dealt_avg_price"]:
                    raise Error("futu_same_version_cumulative_value_conflict")
            self.db.execute("UPDATE orders SET broker_id=? WHERE intent_id=?", (value["order_id"], row["intent_id"]))
            self.db.execute("INSERT INTO futu_orders VALUES(?,?,?,NULL) ON CONFLICT(order_id) DO UPDATE SET projection=excluded.projection,evidence=excluded.evidence,admitted_projection_hash=NULL",
                            (value["order_id"], core.encoded(value), core.encoded(raw)))
            self._halt("futu_accounting_evidence_unknown")
        return "ORDER_RECORDED_ACCOUNTING_UNKNOWN"

    def admit_statement(self, order_id, *, statement, source_bytes):
        """Operator-supplied actual statement is a separate evidence channel.

        This method validates correspondence, not the statement's authenticity.
        API order average * quantity is not substituted for a transaction ledger.
        """
        if (type(source_bytes) is not bytes or not 0<len(source_bytes)<=4*1024*1024
                or type(statement) is not dict or set(statement) != {"source_kind", "source_sha256", "operator_verified", "order_id", "cumulative_quantity", "cumulative_notional", "cumulative_fee"}
                or statement["source_kind"] != "OWNER_PROVIDED_SIMULATION_STATEMENT" or statement["operator_verified"] is not True
                or type(statement["cumulative_quantity"]) is not int
                or hashlib.sha256(source_bytes).hexdigest()!=statement['source_sha256'] or statement["order_id"] != order_id):
            raise Error("actual_separate_statement_evidence_required")
        row = self.db.execute("SELECT projection FROM futu_orders WHERE order_id=?", (exact_id(order_id),)).fetchone()
        if row is None:
            raise Error("observed_order_required")
        value = json.loads(row[0])
        if value["order_status"] not in STATES or statement["cumulative_quantity"] != value["dealt_qty"]:
            raise Error("statement_order_version_mismatch")
        observation = dict(evidence_id=core.fingerprint({"projection": value, "statement": statement}), client_id=value["remark"],
            broker_order_id=order_id, symbol=value["code"], side=value["trd_side"], quantity=value["qty"], limit_price=value["price"],
            state=STATES[value["order_status"]], cumulative_quantity=value["dealt_qty"],
            cumulative_notional=statement["cumulative_notional"], cumulative_fee=statement["cumulative_fee"])
        with core.transaction(self.db):
            saved=self.db.execute('SELECT content FROM futu_statement_sources WHERE sha256=?',(statement['source_sha256'],)).fetchone()
            if saved is not None and saved[0]!=source_bytes:raise Error('statement_source_identity_conflict')
            self.db.execute('INSERT OR IGNORE INTO futu_statement_sources VALUES(?,?)',(statement['source_sha256'],source_bytes))
        result = self.ingest(observation)
        with core.transaction(self.db):
            self._event("FUTU_STATEMENT_ADMITTED", statement)
            self.db.execute("UPDATE futu_orders SET admitted_projection_hash=? WHERE order_id=?", (core.fingerprint(value), order_id))
        return result

    def accounting_pending(self):
        return [row[0] for row in self.db.execute("SELECT order_id FROM futu_orders WHERE admitted_projection_hash IS NULL")]

    def inspect(self):
        result=super().inspect()
        pending=self.accounting_pending()
        result.update(accounting_pending_order_ids=pending,atomic_account_snapshot_claimed=False)
        if pending:
            result['unreconciled_local_projection']={k:result.pop(k) for k in ('cash','positions')}
            result.update(cash=None,positions=None,accounting_status='UNKNOWN_PENDING_ACTUAL_STATEMENT')
        return result


class FutuAdapter:
    def __init__(self, context, profile, *, quote_context=None, _lease_root=None):
        self.context, self.profile = context, binding(profile)
        self.quote_context=quote_context
        self.callbacks = queue.SimpleQueue()
        self.query_evidence = []
        self._lease = None
        self._lease_root = Path(_lease_root) if _lease_root else Path.home()/'.hakimi'/'execution-account-locks'
        self.validate_account()

    def acquire_authority(self):
        if self._lease is not None:return
        self._lease_root.mkdir(parents=True,exist_ok=True)
        key=core.fingerprint({'provider':'FUTU','env':'SIMULATE','account':self.profile['account_id']})
        lease=(self._lease_root/(key+'.lock')).open('a+b')
        if lease.seek(0,2)==0:lease.write(b'0');lease.flush()
        lease.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(lease.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(lease.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError as exc:
            lease.close();raise Error('simulation_account_owned_by_another_local_process') from exc
        self._lease=lease

    def close(self):
        try:
            try:self.context.close()
            finally:
                if self.quote_context is not None:self.quote_context.close()
        finally:
            if self._lease is not None:
                self._lease.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(self._lease.fileno(),msvcrt.LK_UNLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self._lease.fileno(),fcntl.LOCK_UN)
                self._lease.close();self._lease=None

    def bind_authority(self, store):
        self.acquire_authority()
        stat=store.path.stat()
        expected={'store_id':store.config['futu_store_id'],'database_path':str(store.path).casefold() if os.name=='nt' else str(store.path),
                  'file_identity':[stat.st_dev,stat.st_ino]}
        self._lease.seek(1)
        raw=self._lease.read()
        if raw:
            try:registered=json.loads(raw)
            except (ValueError,UnicodeError) as exc:raise Error('account_authority_registry_invalid') from exc
            if registered!=expected:raise Error('account_authority_bound_to_different_database')
        else:
            self._lease.write(core.encoded(expected).encode('utf-8'));self._lease.flush();os.fsync(self._lease.fileno())

    def query(self, method, *, _context=None, **kwargs):
        started = stamp()
        reply = getattr(_context if _context is not None else self.context, method)(**kwargs)
        record = dict(method=method,started_at=started,completed_at=stamp(),ret=reply[0])
        if type(reply[0]) is not int:raise Error('provider_return_code_type_invalid')
        if reply[0] != 0:
            record["error"] = str(reply[1]); self.query_evidence.append(record)
            raise Error("futu_query_rejected:" + method)
        if len(reply) != 2:
            raise Error("unhandled_futu_pagination")
        result = rows(reply[1])
        record["rows"] = [r for r in result if str(r.get('acc_id'))==self.profile['account_id'] and r.get('trd_env')=='SIMULATE'] if method=='get_acc_list' else result
        self.query_evidence.append(record)
        return result

    def validate_account(self):
        account_id = self.profile["account_id"]
        matches = [r for r in self.query("get_acc_list") if str(r.get("acc_id")) == account_id]
        if (len(matches) != 1 or matches[0].get("trd_env") != "SIMULATE" or matches[0].get("acc_status") != "ACTIVE"
                or matches[0].get("sim_acc_type") != "STOCK_AND_OPTION" or "US" not in matches[0].get("trdmarket_auth", [])):
            raise Error("exact_active_us_simulation_account_required")

    def _kwargs(self):
        return {"trd_env": "SIMULATE", "acc_id": int(self.profile["account_id"])}

    def instrument(self, *, require_open=False):
        if self.quote_context is None:raise Error('quote_context_required_for_instrument_rules')
        kwargs={'_context':self.quote_context}
        basic=self.query('get_stock_basicinfo',**kwargs,market='US',stock_type='STOCK',code_list=[self.profile['symbol']])
        snapshot=self.query('get_market_snapshot',**kwargs,code_list=[self.profile['symbol']])
        market=self.query('get_market_state',**kwargs,code_list=[self.profile['symbol']])
        if (len(basic)!=1 or len(snapshot)!=1 or len(market)!=1 or basic[0].get('code')!='US.AMD'
                or basic[0].get('stock_id')!=205816 or basic[0].get('exchange_type')!='US_NASDAQ'
                or basic[0].get('stock_type')!='STOCK' or whole(basic[0].get('lot_size'))!=1
                or snapshot[0].get('code')!='US.AMD' or snapshot[0].get('equity_valid') is not True
                or Decimal(decimal_text(snapshot[0].get('price_spread')))!=Decimal('0.01')
                or market[0].get('code')!='US.AMD'):
            raise Error('futu_instrument_identity_or_rules_not_verified')
        if require_open and (snapshot[0].get('suspension') is not False or market[0].get('market_state')!='AFTERNOON'):
            raise Error('futu_us_regular_session_not_open_or_suspended')
        return dict(symbol='US.AMD',stock_id=205816,lot_size=1,price_increment='0.01',market_state=market[0]['market_state'],
            observed_at=stamp(),order_scope='ONE_WHOLE_SHARE_LIMIT_PRICE_AT_LEAST_ONE_USD_DAY_RTH')

    def scan(self):
        kwargs = self._kwargs()
        current = self.query("order_list_query", **kwargs, refresh_cache=True)
        history = self.query("history_order_list_query", **kwargs, start=self.profile["history_start"], end=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
        orders = {}
        for raw in current + history:
            item = order_projection(raw)
            if item["order_id"] in orders and item != orders[item["order_id"]]:
                raise Error("current_history_order_conflict")
            orders[item["order_id"]] = item
        cash = self.query("accinfo_query", **kwargs, refresh_cache=True, currency="USD")
        held = self.query("position_list_query", **kwargs, refresh_cache=True, currency="USD")
        if len(cash) != 1:
            raise Error("single_scoped_balance_required")
        # US cash is native USD; 'power' may include leverage and is never cash.
        # The display currency field can be N/A for US paper accounts. Futu
        # documents us_cash as native USD independent of that display field.
        usd_cash = decimal_text(cash[0].get("us_cash"))
        if Decimal(usd_cash) < 0:
            raise Error("negative_usd_cash")
        positions = {}
        for row in held:
            if str(row.get("acc_id")) != self.profile["account_id"] or row.get("currency") != "USD" or row.get("position_side") != "LONG":
                raise Error("unsupported_position_account_currency_or_side")
            symbol = row["code"]
            if symbol in positions:
                raise Error("ambiguous_position_identity")
            count = whole(row["qty"], zero=True)
            if count: positions[symbol] = count
        return {"cash": usd_cash, "positions": positions, "orders": sorted(orders.values(), key=lambda row: row["order_id"])}

    def stable_reads(self):
        started = time.monotonic()
        left, right = self.scan(), self.scan()
        if left != right or time.monotonic() - started > 5 or not self.callbacks.empty():
            raise Error("futu_account_reads_changed_stale_or_callback_pending")
        return dict(scope="REPEATED_SCOPED_READS_NOT_ATOMIC", value=right, checked_at=stamp(),
                    elapsed_seconds=time.monotonic()-started, projection_sha256=core.fingerprint(right),binding_sha256=core.fingerprint(self.profile))

    def order_limits(self, payload):
        result=self.query('acctradinginfo_query',**self._kwargs(),order_type='NORMAL',code=payload['symbol'],
            price=float(payload['limit_price']),adjust_limit=0,session='RTH')
        if len(result)!=1:raise Error('single_pretrade_limits_required')
        field='max_cash_buy' if payload['side']=='BUY' else 'max_position_sell'
        if whole(result[0].get(field),zero=True)<payload['quantity']:
            raise Error('cash_only_or_existing_position_limit_exceeded')
        return {'checked_at':stamp(),'field':field,'sufficient':True,'margin_or_short_capacity_used':False}

    def drain_callbacks(self, store):
        while not self.callbacks.empty():
            raw = self.callbacks.get_nowait()
            if str(raw.get("acc_id")) != self.profile["account_id"] or raw.get("trd_env") != "SIMULATE":
                store.stop("callback_account_or_environment_mismatch")
                raise Error("callback_account_or_environment_mismatch")
            store.observe_order(raw, origin="SDK_ORDER_CALLBACK")

    def reconcile(self, store):
        if store.profile != self.profile:
            raise Error("store_transport_binding_mismatch")
        self.drain_callbacks(store)
        token = store.begin_reconcile()
        read = self.stable_reads()
        for row in read['value']['orders']:
            known=store.db.execute('SELECT projection FROM futu_orders WHERE order_id=?',(row['order_id'],)).fetchone()
            if known is None or json.loads(known[0])!=row:
                store.observe_order(row,origin='SDK_ORDER_QUERY')
        if store.accounting_pending():
            raise Error("futu_fee_or_gross_notional_evidence_unknown")
        observations = []
        for row in read["value"]["orders"]:
            known = store.db.execute("SELECT projection,admitted_projection_hash FROM futu_orders WHERE order_id=?", (row["order_id"],)).fetchone()
            if known is None or known[1] != core.fingerprint(row):
                raise Error("unadmitted_or_changed_futu_order")
            event = store.db.execute("SELECT payload FROM events WHERE kind='OBSERVATION_APPLIED' ORDER BY sequence DESC").fetchall()
            matching = [json.loads(e[0])["observation"] for e in event if json.loads(e[0])["observation"]["broker_order_id"] == row["order_id"]]
            if not matching: raise Error("futu_accounting_observation_missing")
            observations.append(matching[0])
        result = store.complete_reconcile(dict(mode=MODE,scope=store.reconciliation_scope,query_token=token,
            orders=observations,cash=read["value"]["cash"],positions=read["value"]["positions"]))
        return {"state": result, "read_barrier": read, "atomic_snapshot_claimed": False}

    def _authorize(self, store, intent_id, authorization, *, for_cancel=False):
        if (type(authorization) is not dict or set(authorization) != {"mode", "account_id", "intent_id", "payload_sha256", "expires_at", "exclusive_account_control", "operations"}
                or authorization["mode"] != MODE or authorization["account_id"] != self.profile["account_id"]
                or authorization["intent_id"] != intent_id or authorization["exclusive_account_control"] is not True
                or authorization["operations"] != ["SUBMIT_ONCE", "CANCEL_OWN_ORDER"]):
            raise Error("explicit_bound_operator_authorization_required")
        expiry = datetime.fromisoformat(authorization["expires_at"].replace("Z", "+00:00"))
        remaining = (expiry-datetime.now(timezone.utc)).total_seconds()
        if not 0 < remaining <= 86400:
            raise Error("current_bounded_authorization_required")
        payload = json.loads(store._row(intent_id)["payload"])
        if authorization["payload_sha256"] != core.fingerprint(payload) or store.profile != self.profile:
            raise Error("authorization_payload_or_account_mismatch")
        self.validate_account()
        if not for_cancel:self.instrument(require_open=True)
        self.bind_authority(store)

    def submit_once(self, store, intent_id, *, authorization, discard_sync_response=False):
        if type(discard_sync_response) is not bool:raise Error('explicit_fault_injection_bool_required')
        self._authorize(store, intent_id, authorization)
        # A durable existing attempt never gets another order send.
        if store._row(intent_id)["state"] != "PREPARED":
            return "ALREADY_ATTEMPTED_NO_SEND"
        self.reconcile(store)
        self.order_limits(json.loads(store._row(intent_id)['payload']))
        if not self.callbacks.empty():
            self.drain_callbacks(store)
            raise Error('callback_invalidated_submit_reconciliation')
        command = store.claim_submit(intent_id)
        if command is None: return "ALREADY_ATTEMPTED_NO_SEND"
        try:
            reply = self.context.place_order(price=float(command["limit_price"]),qty=command["quantity"],code=command["symbol"],
                trd_side=command["side"],order_type="NORMAL",adjust_limit=0,trd_env="SIMULATE",acc_id=int(self.profile["account_id"]),
                remark=command["client_id"],time_in_force="DAY",fill_outside_rth=False,session="RTH")
        except (TimeoutError,ConnectionError,OSError):
            return "SUBMIT_UNKNOWN_NO_RESEND"
        self.drain_callbacks(store)
        with core.transaction(store.db):
            store._event("FUTU_SYNC_RESPONSE", {"ret": reply[0],"rows": rows(reply[1]) if reply[0]==0 else None,
                "error": str(reply[1]) if reply[0]!=0 else None,"discarded_for_fault_test":discard_sync_response})
        if discard_sync_response or reply[0] != 0:
            return "SUBMIT_UNKNOWN_NO_RESEND"
        for row in rows(reply[1]):store.observe_order(row,origin="SDK_SUBMIT_RESPONSE")
        return "ORDER_RECORDED_ACCOUNTING_UNKNOWN"

    def cancel(self, store, intent_id, *, authorization):
        self._authorize(store,intent_id,authorization,for_cancel=True)
        command=store.begin_cancel(intent_id)
        if command is None:return "NO_CANCEL_SEND"
        try:
            reply=self.context.modify_order(modify_order_op="CANCEL",order_id=command["broker_order_id"],qty=0,price=0,
                trd_env="SIMULATE",acc_id=int(self.profile["account_id"]))
        except (TimeoutError,ConnectionError,OSError):return "CANCEL_UNKNOWN"
        self.drain_callbacks(store)
        if reply[0] != 0:return "CANCEL_UNKNOWN"
        store.cancel_response(intent_id,command["cancel_id"],True)
        return "CANCEL_ACK_NOT_TERMINAL"


def open_sdk(profile):
    profile=binding(profile)
    if importlib.metadata.version("futu-api") != SDK_VERSION:
        raise Error("reviewed_futu_sdk_version_required")
    from futu import OpenSecTradeContext,OpenQuoteContext,SecurityFirm,TrdMarket,TradeOrderHandlerBase,RET_OK
    context=OpenSecTradeContext(filter_trdmarket=TrdMarket.US,host=profile["host"],port=profile["port"],security_firm=SecurityFirm.NONE)
    context.set_sync_query_connect_timeout(15)
    quote=None
    try:
        quote=OpenQuoteContext(host=profile['host'],port=profile['port'],is_async_connect=True,security_firm=SecurityFirm.NONE)
        quote.set_sync_query_connect_timeout(15)
        adapter=FutuAdapter(context,profile,quote_context=quote)
        class Handler(TradeOrderHandlerBase):
            def on_recv_rsp(self, response):
                ret,data=super().on_recv_rsp(response)
                if ret==RET_OK:
                    for row in rows(data):adapter.callbacks.put(row)
                return ret,data
        context.set_handler(Handler())
        return adapter
    except BaseException:
        if quote is not None:quote.close()
        context.close();raise


def main():
    parser=argparse.ArgumentParser(description="Explicit-account Futu simulation read-only preflight; no order CLI.")
    parser.add_argument("--profile",type=Path,required=True)
    parser.add_argument("--output-dir",type=Path,required=True)
    parser.add_argument('--capacity-price',help='Optional read-only cash capacity query for one AMD share at this limit; never submits an order.')
    args=parser.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=False)
    adapter=None
    result=dict(status='PREFLIGHT_INCOMPLETE',orders_sent=0,accounting_verified=False)
    source_paths=[Path(__file__),Path(__file__).with_name('execution_state_lab.py')]
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    try:
        adapter=open_sdk(json.loads(args.profile.read_text(encoding="utf-8-sig")))
        result.update(adapter.stable_reads())
        result['instrument']=adapter.instrument()
        if args.capacity_price is not None:
            price=core.amount(args.capacity_price)
            if price<1 or price%Decimal('0.01')!=0:raise Error('capacity_price_rule_invalid')
            result['capacity_check']=adapter.order_limits(dict(symbol='US.AMD',side='BUY',quantity=1,limit_price=core.formatted(price)))
            result['capacity_check']['query_limit_price']=core.formatted(price)
        result.update(status="READ_ONLY_STABLE_SCOPED_READS",orders_sent=0,accounting_verified=False,sdk=SDK_VERSION,fee_query_supported=False)
    except Exception as exc:
        result.update(status="PREFLIGHT_INCOMPLETE",error_type=type(exc).__name__,error=str(exc),orders_sent=0,accounting_verified=False)
    finally:
        if adapter is not None:
            result["query_evidence"]=adapter.query_evidence
            adapter.close()
    result['source_file_sha256']=source_hashes
    if source_hashes!={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}:
        result.update(status='PREFLIGHT_INCOMPLETE',error='source_changed_during_preflight')
    target=args.output_dir/"preflight.private.json"
    with target.open("x",encoding="utf-8") as f:json.dump(result,f,indent=2,ensure_ascii=True,allow_nan=False)
    print(json.dumps({k:result[k] for k in ("status","orders_sent","accounting_verified")},ensure_ascii=True))
    return 0 if result["status"]=="READ_ONLY_STABLE_SCOPED_READS" else 1


if __name__=="__main__":
    raise SystemExit(main())
