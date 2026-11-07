"""Trusted saved-native-report admission for the isolated historical replay.

No client report, path, calendar, completion assertion or executable callback is
accepted. Root integration owns the service and runtime source guard. No shared
route or UI is installed by this draft.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
import re

from . import terminal_continuous_replay as replay
from exchange_terminal.services import strategy_signals as signals, indicator_math
from exchange_terminal.services.terminal_research import ENGINE_ID, _engine_source_identity, validate_terminal_strategy_params
from exchange_terminal.services.terminal_saved_results import verified_saved_result, resolve_execution_research
from exchange_terminal.services.terminal_strategy_candidates import CATALOG_ORDER
from hakimi_research.documents import parse_document
from hakimi_research.equity_dataset import verify_equity_snapshot


LOADED_ADAPTER_SHA256 = sha256(Path(__file__).read_bytes()).hexdigest()
HASH = re.compile(r"[a-f0-9]{64}\Z")
ACCOUNT = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{7,79}\Z")


class AdmissionError(ValueError):
    pass


def require(condition, message):
    if not condition: raise AdmissionError(message)


def stamp(value):
    require(type(value) is str, "explicit_saved_session_clock_required")
    try: parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: raise AdmissionError("saved_session_clock_invalid") from None
    require(parsed.tzinfo is not None and parsed.microsecond % 1000 == 0, "explicit_millisecond_session_timezone_required")
    return int(parsed.timestamp() * 1000)


def decimal_value(value):
    require(type(value) in (int,float), "verified_numeric_candle_required")
    return format(Decimal(str(value)), "f")


def model_descriptor():
    return dict(id=replay.MODEL, implementation_sha256=replay.LOADED_IMPLEMENTATION_SHA256,
        adapter_sha256=LOADED_ADAPTER_SHA256, quantity_policy="WHOLE_SHARE_FIXED_UNIT_LONG_ONLY",
        fill_policy="PREVIOUS_CLOSE_SIGNAL_NEXT_COMPLETE_SESSION_OPEN",
        event_clock="ORIGINAL_SNAPSHOT_SESSION_UTC", intrabar_stop_loss=False, intrabar_take_profit=False,
        native_execution_equivalent=False, broker_execution=False)


def seed_selection(minimum_count, dataset):
    """Project only verified saved configuration and the current saved input."""
    rows=dataset['bars'];available=len(rows);sufficient=available>=minimum_count
    return dict(minimum_count=minimum_count,maximum_count=available,available_rows=available,
        data_sufficient=sufficient,missing_rows=max(0,minimum_count-available),
        recommended_count=minimum_count if sufficient else None,
        recommended_session=rows[minimum_count-1]['date'] if sufficient else None,
        next_session=rows[minimum_count]['date'] if sufficient and available>minimum_count else None)


def request_metadata(action, payload):
    return dict(account_id=payload['settings']['account_id'] if action=='create' else payload['account_id'],
        request_id=payload['request_id'],request_action=action,request_hash=replay.digest(payload))


class TrustedReplayAdapter:
    def __init__(self, service, *, runtime_guard, clock=None):
        require(callable(runtime_guard), "current_runtime_source_guard_required")
        self.service, self.runtime_guard, self.clock = service, runtime_guard, clock

    def _runtime_current(self):
        state = self.runtime_guard()
        require(type(state) is dict and state.get("schema_version") == "hakimi-runtime-build-v1"
                and state.get("status") == "PASS" and state.get("restart_required") is False,
                "runtime_source_changed_restart_required")
        require(sha256(Path(__file__).read_bytes()).hexdigest() == LOADED_ADAPTER_SHA256,
                "replay_adapter_source_changed")
        require(sha256(Path(replay.__file__).read_bytes()).hexdigest() == replay.LOADED_IMPLEMENTATION_SHA256,
                "replay_implementation_source_changed")
        indicator_math.assert_loaded_source_current()

    def _settings(self, value):
        expected = {"account_id","initial_cash","unit_quantity","fee_rate","slippage_bps","limits"}
        require(type(value) is dict and expected<=set(value)<=expected|{'display_name'}, "explicit_replay_settings_required")
        require(type(value["account_id"]) is str and ACCOUNT.fullmatch(value["account_id"]), "new_replay_account_id_required")
        replay.money(value["initial_cash"]); replay.positive_int(value["unit_quantity"])
        require(replay.money(value["fee_rate"],zero=True) <= Decimal("0.05")
                and replay.money(value["slippage_bps"],zero=True) <= Decimal("1000"), "replay_costs_out_of_bounds")
        checked = deepcopy(value); checked["limits"] = replay.validate_limits(value["limits"])
        if 'display_name' in value:
            name=value['display_name']
            require(type(name) is str and 1<=len(name)<=64 and name.isprintable() and bool(name.strip()),
                    'printable_replay_display_name_required')
            checked['display_name']=name.strip()
        return checked

    def _reference(self, value):
        require(type(value) is dict and set(value) == {"kind","id"} and value.get("kind") == "terminal_run"
                and type(value.get("id")) is str and HASH.fullmatch(value["id"]), "completed_native_report_reference_required")
        return deepcopy(value)

    def _input(self, input_id):
        require(type(input_id) is str and HASH.fullmatch(input_id), "native_saved_input_id_required")
        native = self.service._input(input_id)
        keys = [name for name in ("daily_reference","core_reference") if name in native]
        require(len(keys) == 1, "canonical_original_required_native_cache_not_supported")
        key = keys[0]; reference = native[key]
        require(type(reference) is dict and type(reference.get("file_sha256")) is str
                and HASH.fullmatch(reference["file_sha256"]), "retained_original_hash_required")
        original_hash = reference["file_sha256"]
        folder = "daily-originals" if key == "daily_reference" else "core-originals"
        path = self.service._safe(self.service.workspace / "terminal-inputs" / folder / (original_hash + ".json"))
        with path.open("rb") as stream: raw = stream.read(64*1024*1024+1)
        require(len(raw) <= 64*1024*1024 and sha256(raw).hexdigest() == original_hash, "retained_original_bytes_changed")
        snapshot = verify_equity_snapshot(parse_document(raw))
        require(snapshot["snapshot_id"] == reference["snapshot_hash"], "native_canonical_snapshot_identity_conflict")
        meta, security = native["meta"], snapshot["security"]
        require(meta.get("asset_class") == "US_EQUITY" and meta.get("currency") == security.get("currency") == "USD"
                and snapshot.get("quote_unit") == "USD" and snapshot.get("market") == "us_equity",
                "explicit_us_equity_usd_required")
        require(snapshot.get("price_basis") == meta.get("price_basis") == "RAW_UNADJUSTED"
                and snapshot.get("timeframe") == "1d" and native.get("bar") == "1D"
                and snapshot.get("volume_unit") == "shares", "raw_complete_daily_equity_required")
        require(all(type(security.get(name)) is str and security[name] for name in ("security_id","symbol","exchange","currency","instrument_type"))
                and security["exchange"] in {"XNYS","XNAS"} and meta.get("security_id") == security["security_id"],
                "explicit_verified_security_identity_required")
        require(native["quality"].get("status") == "REVIEW" and not native["quality"].get("blockers")
                and snapshot["research_admission"].get("allowed") is True
                and snapshot["research_admission"].get("scope") == "ACTION_FREE_FIXED_WINDOW_ONLY",
                "verified_action_free_admission_required")
        calendar, sessions = snapshot["calendar"], snapshot["sessions"]
        require(type(calendar) is dict and calendar.get("timezone") == snapshot.get("timezone") == "America/New_York"
                and type(calendar.get("source")) is dict and all(calendar["source"].get(k) for k in ("name","reference","raw_sha256")),
                "explicit_calendar_source_identity_required")
        require(type(sessions) is list and sessions and len(sessions) == len(snapshot["candles"]) == len(native["rows"]),
                "complete_snapshot_sessions_required")
        actions = snapshot["corporate_actions"]
        first, last = sessions[0]["date"], sessions[-1]["date"]
        require(actions.get("coverage_status") == "DECLARED_COMPLETE" and actions.get("coverage_start", "~") <= first
                and actions.get("coverage_end", "") >= last
                and not any(first <= action["effective_date"] <= last for action in actions["actions"]),
                "explicit_no_corporate_action_window_required")
        lag = snapshot["bar_availability_lag_seconds"]
        require(type(lag) is int and lag >= 0 and snapshot["availability_policy"] == "SESSION_CLOSE_PLUS_DECLARED_LAG_NOT_HISTORICAL_RECEIPT",
                "explicit_saved_availability_policy_required")
        observed = stamp(snapshot["as_of"])
        bars = []
        for index,(session,candle,row) in enumerate(zip(sessions,snapshot["candles"],native["rows"])):
            opened, closed = stamp(session.get("open_utc")), stamp(session.get("close_utc"))
            require(opened < closed and closed + lag*1000 <= observed and stamp(candle[0]) == opened,
                    "session_clock_or_availability_conflict")
            if index:
                require(bars[-1]["close_at"] + lag*1000 < opened, "previous_close_not_available_before_next_open")
            require(row.get("date") == session["date"] and row.get("ts_ms") == opened and row.get("complete") is True
                    and row.get("provisional") is False, "native_saved_session_binding_conflict")
            require(all(Decimal(str(row.get(field))) == Decimal(str(candle[n])) for n,field in enumerate(("open","high","low","close","volume"),1)),
                    "native_saved_prices_conflict")
            bars.append(dict(date=session["date"],open_at=opened,close_at=closed,complete=True,
                **{field:decimal_value(candle[n]) for n,field in enumerate(("open","high","low","close","volume"),1)}))
        calendar_identity = {"exchange":security["exchange"],"timezone":calendar["timezone"],
                             "source_name":calendar["source"]["name"],"source_reference":calendar["source"]["reference"]}
        binding = dict(native_input_id=input_id,source_namespace=key,canonical_snapshot_id=snapshot["snapshot_id"],
            retained_original_sha256=original_hash,raw_manifest_sha256=snapshot["raw_input"]["manifest_sha256"],
            calendar_identity=calendar_identity,calendar_sha256=replay.digest(calendar),
            calendar_source_sha256=calendar["source"]["raw_sha256"],security=deepcopy(security),
            action_window_sha256=replay.digest(actions),availability_policy=snapshot["availability_policy"],
            bar_availability_lag_seconds=lag,source_truth_verified=False,source_authentication=snapshot["source_authentication"])
        dataset = dict(security_id=security["security_id"],price_basis="RAW_UNADJUSTED",calendar_id=replay.digest(calendar_identity),
            observed_at=observed,corporate_actions=[],evidence_kind="SAVED_MARKET_INPUT",bars=bars,input_binding=binding)
        return replay.validate_data(dataset), binding

    def _admission(self, reference, settings):
        self._runtime_current()
        reference, settings = self._reference(reference), self._settings(settings)
        envelope = verified_saved_result(self.service, reference)
        resolved = resolve_execution_research(self.service, reference)
        report, binding = envelope["report"], resolved["binding"]
        require(envelope["verification_status"] == "VERIFIED_RECORD" and report.get("status") == "COMPLETED"
                and report.get("engine_id") == ENGINE_ID and binding.get("engine_id") == ENGINE_ID,
                "completed_current_native_engine_required")
        strategy_id = report["strategy_id"]
        require(strategy_id in CATALOG_ORDER, "only_current_nine_native_strategies_supported")
        strategy = self.service._strategy(strategy_id,new_work=True)
        task = self.service._task_record(report["task_id"])
        params = validate_terminal_strategy_params(strategy,task["strategy_params"])
        require(replay.encoded(params) == replay.encoded(task["strategy_params"]) == replay.encoded(binding["strategy_params"]),
                "saved_native_parameters_changed")
        sources = _engine_source_identity()
        current = self.service.fingerprint(strategy_id,deepcopy(params))
        require(task["engine_source_identity"] == sources and task["fingerprint"] == current,
                "native_saved_source_or_fingerprint_changed")
        dataset,input_binding = self._input(task["input_id"])
        if 'display_name' not in settings:
            settings['display_name']=input_binding['security']['symbol'][:36]+' · '+strategy_id
        require(binding.get("security_id") == dataset["security_id"] and binding["input_id"] == task["input_id"]
                and binding["report_hash"] == report["id"], "saved_research_input_binding_conflict")
        signal_fingerprint = signals.strategy_signal_fingerprint(strategy_id,params)
        admitted = dict(reference=reference,research_binding=deepcopy(binding),owner_id=resolved["owner_id"],
            native_fingerprint=current,engine_source_identity=sources,signal_fingerprint=signal_fingerprint,
            initial_input_binding=input_binding,model=model_descriptor(),settings=settings,
            minimum_seed_count=max(30,signals.strategy_startup_candles_for_params(strategy_id,params)),
            workspace_context=sha256(str(self.service.workspace.resolve()).casefold().encode()).hexdigest())
        self._runtime_current()
        require(_engine_source_identity() == sources and self.service.fingerprint(strategy_id,deepcopy(params)) == current,
                "native_source_changed_during_admission")
        return admitted,dataset

    def preview(self, reference, settings):
        admitted,dataset = self._admission(reference,settings)
        return dict(status="REPLAY_MODEL_CONFIRMATION_REQUIRED",admission_id=replay.digest(admitted),
            reference=admitted["reference"],research_binding=admitted["research_binding"],input_binding=admitted["initial_input_binding"],
            model=admitted["model"],settings=admitted["settings"],session_count=len(dataset["bars"]),
            first_session=dataset["bars"][0]["date"],last_session=dataset["bars"][-1]["date"],
            seed_selection=seed_selection(admitted['minimum_seed_count'],dataset),
            warnings=["新回放使用整股固定数量、下一完整日线开盘合成成交，不等同原回测。",
                      "新模型没有柱内止盈或止损；原报告的止盈止损参数只作来源展示，不会在新模型中执行。",
                      "使用保存快照的日历时间，不代表该时点实际收到过行情；来源真实性仍未独立认证。"],
            new_research_runs=0,permissions=dict(replay.PERMISSIONS))

    def _callbacks(self, admitted):
        strategy_id = admitted["research_binding"]["strategy_id"]
        params = admitted["research_binding"]["strategy_params"]
        fn = signals.build_strategy_signal_fn(strategy_id,deepcopy(params))
        def guard():
            self._runtime_current()
            require(_engine_source_identity() == admitted["engine_source_identity"]
                    and self.service.fingerprint(strategy_id,deepcopy(params)) == admitted["native_fingerprint"]
                    and signals.strategy_signal_fingerprint(strategy_id,params) == admitted["signal_fingerprint"]
                    and model_descriptor() == admitted["model"], "replay_current_source_binding_changed")
            return replay.digest(admitted)
        def signal(prefix,position):
            guard()
            if signals.strategy_signal_input(strategy_id) == "BARS":
                history=[dict(date=row["date"],ts_ms=row["open_at"],complete=True,provisional=False,
                    **{key:float(row[key]) for key in ("open","high","low","close","volume")}) for row in prefix]
            else: history=[float(row["close"]) for row in prefix]
            result=fn(history,float(prefix[-1]["close"]),position["has_position"],float(position["entry_price"] or 0),0.0)
            guard(); return result
        return signal,guard

    def _path(self, account_id):
        require(type(account_id) is str and ACCOUNT.fullmatch(account_id), "new_replay_account_id_required")
        return self.service._safe(self.service.workspace/'historical-replay'/account_id/'replay.sqlite')

    def create_new(self, reference, settings, confirmation, *, creation_request=None):
        admitted,dataset = self._admission(reference,settings)
        expected=dict(admission_id=replay.digest(admitted),model_id=replay.MODEL,
            whole_share_next_open_is_different=True,no_intrabar_stop_or_take_profit=True)
        require(type(confirmation) is dict and replay.encoded(confirmation)==replay.encoded(expected),
                "explicit_exact_replay_model_confirmation_required")
        signal,guard=self._callbacks(admitted)
        ledger=replay.HistoricalReplay.create(self._path(settings['account_id']),strategy_binding=admitted,dataset=dataset,
            signal_fn=signal,source_guard=guard,clock=self.clock,creation_request=creation_request,
            **{key:value for key,value in admitted['settings'].items() if key!='display_name'})
        return ReplaySession(self,ledger)

    def open_for_steps(self, account_id):
        def denied(*args,**kwargs): raise AdmissionError('bound_replay_session_not_verified')
        ledger=replay.HistoricalReplay(self._path(account_id),signal_fn=denied,source_guard=denied,clock=self.clock)
        try:
            old=ledger.config['strategy_binding']
            admitted,_=self._admission(old['reference'],old['settings'])
            require(replay.encoded(admitted)==replay.encoded(old), 'saved_replay_admission_changed')
            # Any adopted input must still be a current, verified retained input.
            stored=ledger._data(ledger.snapshot()['state']['dataset_id'])
            current,_=self._input(stored['input_binding']['native_input_id'])
            require(replay.encoded(stored)==replay.encoded(current),'saved_replay_input_changed')
            ledger.signal_fn,ledger.source_guard=self._callbacks(admitted)
            return ReplaySession(self,ledger)
        except BaseException:
            ledger.close();raise

    def activate(self, session):
        """Rebind current code without clearing the ledger's recovery gate."""
        old=session.ledger.config['strategy_binding']
        admitted,_=self._admission(old['reference'],old['settings'])
        require(replay.encoded(old)==replay.encoded(admitted),'saved_replay_admission_changed')
        stored=session.ledger._data(session.snapshot()['state']['dataset_id'])
        current,_=self._input(stored['input_binding']['native_input_id'])
        require(replay.encoded(stored)==replay.encoded(current),'saved_replay_input_changed')
        session.ledger.signal_fn,session.ledger.source_guard=self._callbacks(admitted)

    def open_for_control(self, account_id, *, readonly=False):
        def denied(*args,**kwargs):raise AdmissionError('bound_replay_session_not_verified')
        ledger=replay.HistoricalReplay(self._path(account_id),signal_fn=denied,source_guard=denied,clock=self.clock,readonly=readonly)
        return ReplaySession(self,ledger)

    def inspect(self, account_id, *, after_sequence=0, limit=None):
        def denied(*args,**kwargs): raise AdmissionError('read_cannot_calculate')
        ledger=replay.HistoricalReplay(self._path(account_id),signal_fn=denied,source_guard=denied,clock=self.clock,readonly=True)
        try:return dict(snapshot=ledger.snapshot(),history=ledger.history(after_sequence=after_sequence,limit=limit))
        finally:ledger.close()


class ReplaySession:
    """Trusted internal object; routes expose only the explicit methods below."""
    def __init__(self, adapter, ledger): self.adapter,self.ledger=adapter,ledger
    def snapshot(self):
        snapshot=self.ledger.snapshot()
        config=self.ledger.config
        binding=config['strategy_binding']
        research=binding['research_binding'];security=binding['initial_input_binding']['security']
        created=self.ledger.db.execute('SELECT document FROM events WHERE sequence=1').fetchone()[0]
        import json
        snapshot['display_summary']=dict(
            display_name=binding['settings'].get('display_name') or security['symbol'][:36]+' · '+research['strategy_id'],
            symbol=security['symbol'],security_id=security['security_id'],strategy_id=research['strategy_id'],
            task_version=research['task_version'],reference=deepcopy(binding['reference']),
            initial_cash=config['initial_cash'],unit_quantity=config['unit_quantity'],fee_rate=config['fee_rate'],
            slippage_bps=config['slippage_bps'],created_at=json.loads(created)['recorded_at'],model=deepcopy(binding['model']))
        snapshot['seed_selection']=seed_selection(binding['minimum_seed_count'],self.ledger._data(snapshot['state']['dataset_id']))
        return snapshot
    def history(self, **kwargs): return self.ledger.history(**kwargs)
    def receipt(self, request_id): return self.ledger.receipt(request_id)
    def seed_close(self, request_id, **kwargs):
        count=kwargs.get('seed_count')
        require(type(count) is int and count>=self.ledger.config['strategy_binding']['minimum_seed_count'],'verified_minimum_seed_count_required')
        return self.ledger.seed_close(request_id,**kwargs)
    def advance_next(self, request_id, **kwargs): return self.ledger.advance_next(request_id,**kwargs)
    def pause(self, request_id, **kwargs): return self.ledger.pause(request_id,**kwargs)
    def reconcile(self, request_id, **kwargs): return self.ledger.reconcile(request_id,**kwargs)
    def resume(self, request_id, **kwargs): return self.ledger.resume(request_id,**kwargs)
    def close(self): self.ledger.close()
    def adopt_input(self, request_id, *, expected_head, input_id, api_request=None):
        self.adapter._runtime_current()
        dataset,binding=self.adapter._input(input_id)
        original=self.ledger.config['strategy_binding']['initial_input_binding']
        require(binding['security']==original['security'] and binding['calendar_identity']==original['calendar_identity'],
                'new_input_security_or_calendar_identity_changed')
        return self.ledger.adopt_input(request_id,expected_head=expected_head,dataset=dataset,api_request=api_request)


class ReplayAPI:
    """Bounded in-process API, with no job queue or background stepping.

    Host integration keeps one instance per current workspace and sends pause
    directly to mutate. The source/report resolver is never supplied by clients.
    Exceptions remain explicit refusals; this wrapper never retries mutations.
    """
    def __init__(self, adapter):
        from threading import RLock
        self.adapter=adapter;self._sessions={};self._creating=set();self._lock=RLock()

    @staticmethod
    def _fields(payload, required, optional=()):
        require(type(payload) is dict and set(required)<=set(payload)<=set(required)|set(optional),'replay_api_fields_invalid')
        require(len(replay.encoded(payload))<=16384,'bounded_replay_request_required')

    def _session(self, account_id):
        # This lock protects only handle lookup/open. No signal work holds it.
        known=self._sessions.get(account_id)
        if known:return known
        with self._lock:require(len(self._sessions)+len(self._creating)<16,'open_replay_capacity_reached_close_an_idle_session')
        opened=self.adapter.open_for_control(account_id)
        with self._lock:
            known=self._sessions.setdefault(account_id,opened)
        if known is not opened:opened.close()
        return known

    def _read_session(self, account_id):
        with self._lock:
            known=self._sessions.get(account_id)
        return (known,False) if known else (self.adapter.open_for_control(account_id,readonly=True),True)

    def read(self, resource, payload):
        if resource=='preview':
            self._fields(payload,{'reference','settings'})
            return self.adapter.preview(payload['reference'],payload['settings'])
        if resource=='accounts':
            self._fields(payload,set(),{'after_account_id','limit'})
            limit=payload.get('limit',25);after=payload.get('after_account_id','')
            require(type(limit) is int and 1<=limit<=100 and type(after) is str and len(after)<=80,'bounded_account_cursor_required')
            root=self.adapter.service._safe(self.adapter.service.workspace/'historical-replay')
            if not root.exists():return dict(items=[],has_more=False,next_after=after)
            paths=[]
            for path in root.iterdir():
                require(len(paths)<1000,'account_inventory_capacity_exceeded')
                if ACCOUNT.fullmatch(path.name):paths.append(self.adapter.service._safe(path))
            names=sorted(p.name for p in paths if p.name>after)
            items=[]
            for name in names[:limit]:
                try:
                    status=self.read('status',{'account_id':name})
                    items.append(dict(account_id=name,phase=status['phase'],last_session=status['last_session'],head=status['head'],
                                      display_summary=status['display_summary']))
                except (ValueError,OSError):items.append(dict(account_id=name,phase='STORE_REVIEW_REQUIRED',automatic_retry=False))
            return dict(items=items,has_more=len(names)>limit,next_after=items[-1]['account_id'] if items else after)
        options={'status':set(),'history':{'after_sequence','limit','expected_head'},'receipt':{'request_id'},'creation_receipt':{'request_id'}}
        require(resource in options,'read_only_replay_resource_required')
        self._fields(payload,{'account_id'}|({'request_id'} if resource in {'receipt','creation_receipt'} else set()),options[resource])
        session,temporary=self._read_session(payload['account_id'])
        try:
            if resource=='status':return session.snapshot()
            if resource=='history':return session.history(**{k:v for k,v in payload.items() if k!='account_id'})
            if resource=='receipt':
                result=session.receipt(payload['request_id'])
                if 'request_hash' not in result:result['request_metadata_status']='UNAVAILABLE_LEGACY_PAYLOAD'
                return result
            creation=session.ledger.config.get('creation_request')
            require(creation and creation['request_id']==payload['request_id'],'creation_request_not_found')
            return dict(request_id=creation['request_id'],request_hash=creation['request_hash'],account_id=payload['account_id'],
                request_action='create',status='CREATED',head=session.ledger.db.execute('SELECT hash FROM events WHERE sequence=1').fetchone()[0],automatic_next_step=False)
        finally:
            if temporary:session.close()

    def mutate(self, action, payload):
        payload=deepcopy(payload)
        if action=='create':
            self._fields(payload,{'request_id','reference','settings','confirmation'})
            request_id=payload['request_id']
            require(type(request_id) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{7,99}',request_id),'bounded_request_id_required')
            account_id=self.adapter._settings(payload['settings'])['account_id']
            creation=dict(request_id=request_id,request_hash=replay.digest(payload))
            if self.adapter._path(account_id).exists():
                old=self.read('creation_receipt',{'account_id':account_id,'request_id':request_id})
                require(old['request_hash']==creation['request_hash'],'creation_request_conflict')
                return old
            with self._lock:
                require(len(self._sessions)+len(self._creating)<16,'open_replay_capacity_reached_close_an_idle_session')
                require(account_id not in self._creating,'creation_in_progress_query_original_request')
                self._creating.add(account_id)
            try:
                session=self.adapter.create_new(payload['reference'],payload['settings'],payload['confirmation'],creation_request=creation)
                with self._lock:self._sessions[account_id]=session
            finally:
                with self._lock:self._creating.discard(account_id)
            return dict(status='CREATED',head=session.ledger.creation_head,automatic_next_step=False,
                        **request_metadata('create',payload))
        extra={'seed':{'seed_count'},'step':set(),'pause':{'reason'},'reconcile':set(),'resume':set(),'adopt':{'input_id'}}
        require(action in extra,'explicit_replay_action_required')
        self._fields(payload,{'request_id','account_id','expected_head'}|extra[action],{'in_flight_request_id'} if action=='pause' else set())
        if 'in_flight_request_id' in payload:
            require(type(payload['in_flight_request_id']) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{7,119}',payload['in_flight_request_id']),
                    'bounded_in_flight_request_id_required')
        session=self._session(payload['account_id'])
        if action in {'seed','step','resume','adopt'}:self.adapter.activate(session)
        # Pause/reconcile intentionally bypass current-code calculations so a
        # source-change refusal cannot take away the stop/recovery exit.
        method={'seed':session.seed_close,'step':session.advance_next,'pause':session.pause,
                'reconcile':session.reconcile,'resume':session.resume,'adopt':session.adopt_input}[action]
        metadata=request_metadata(action,payload)
        context=dict(action=action,payload=deepcopy(payload),hash=metadata['request_hash'])
        try:
            result=method(payload['request_id'],api_request=context,
                          **{k:v for k,v in payload.items() if k not in {'request_id','account_id'}})
        except replay.ReplayRefusedNotApplied as error:
            if error.metadata!=metadata:raise replay.ReplayError('refusal_request_binding_invalid') from error
            return dict(status='REFUSED_NOT_APPLIED',reason=error.reason,automatic_retry=False,automatic_next_step=False,**metadata)
        # No post-commit read: a failed display/read must not obscure this ack.
        return dict(result,**metadata)

    def close_session(self, account_id):
        with self._lock:
            session=self._sessions.get(account_id)
            if session:
                session.close();del self._sessions[account_id]

    def close(self):
        for account_id in list(self._sessions):self.close_session(account_id)
