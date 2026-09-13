"""Bounded, explicit phases for one official simulation acceptance cycle.

Prepare/recover/duplicate-probe never send an order. Submit and cancel require
the separate operator authorization consumed by the existing adapter. Every CLI
invocation owns a fresh process; no scheduler, automatic retry or order loop.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


adapter_module = module('futu_cycle_adapter', Path(__file__).with_name('futu_simulation_adapter.py'))
core, Error = adapter_module.core, adapter_module.Error
INTENT = 'amd-official-simulation-cycle-v1'
PAYLOAD = dict(symbol='US.AMD', side='BUY', quantity=1, limit_price='1')
PHASES = ('prepare', 'submit', 'recover', 'duplicate-probe', 'cancel', 'admit-statement')


def source_hashes():
    return {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ('futu_simulation_cycle.py', 'futu_simulation_adapter.py', 'execution_state_lab.py', 'observation_job.py')}


class ScopedTransport:
    """Limit this acceptance driver to the already prepared account and intent."""
    READS = {'get_acc_list', 'order_list_query', 'history_order_list_query',
             'accinfo_query', 'position_list_query', 'acctradinginfo_query', 'close'}

    def __init__(self, context, phase, store):
        self.context, self.phase, self.store = context, phase, store
        self.calls = {'place_order': 0, 'modify_order': 0}

    def __getattr__(self, name):
        if name not in self.READS:raise Error('cycle_transport_method_not_allowed')
        return getattr(self.context, name)

    def _write(self, name, kwargs):
        allowed = {'submit': 'place_order', 'cancel': 'modify_order'}.get(self.phase)
        if name != allowed or self.calls[name] != 0:
            raise Error('cycle_phase_or_single_dispatch_limit')
        if kwargs.get('trd_env') != 'SIMULATE' or kwargs.get('acc_id') != int(self.store.profile['account_id']):
            raise Error('cycle_explicit_simulation_account_required')
        row = self.store._row(INTENT)
        if name == 'place_order':
            expected = dict(code='US.AMD', qty=1, price=1.0, trd_side='BUY', order_type='NORMAL',
                time_in_force='DAY', session='RTH', fill_outside_rth=False, adjust_limit=0, remark=row['client_id'])
        else:
            expected = dict(modify_order_op='CANCEL', order_id=row['broker_id'], qty=0, price=0)
            if not row['broker_id']:raise Error('cycle_cancel_requires_bound_broker_id')
        if set(kwargs) != set(expected) | {'trd_env', 'acc_id'} or any(kwargs[k] != v for k, v in expected.items()):
            raise Error('cycle_frozen_order_terms_changed')
        with core.transaction(self.store.db):
            self.store._event('FUTU_CYCLE_DISPATCH_STARTED', {'method': name, 'kwargs': kwargs})
        self.calls[name] += 1
        return getattr(self.context, name)(**kwargs)

    def place_order(self, **kwargs):return self._write('place_order', kwargs)
    def modify_order(self, **kwargs):return self._write('modify_order', kwargs)


def run_phase(phase, database, *, profile=None, authorization=None, statement=None,
              statement_bytes=None, _sdk_factory=adapter_module.open_sdk):
    if phase not in PHASES:raise Error('cycle_phase_required')
    if phase in ('submit', 'cancel') and authorization is None:
        raise Error('separate_official_simulation_order_authorization_required')
    adapter = store = transport = None
    receipt = dict(phase=phase, status='INCOMPLETE', order_dispatch_attempts=0, cancel_dispatch_attempts=0,
                   source_file_sha256=source_hashes(), official_cycle_complete=False)
    try:
        if phase == 'prepare':
            if Path(database).exists():raise Error('cycle_database_already_exists')
            profile = adapter_module.binding(profile)
            adapter = _sdk_factory(profile)
            anchor = adapter.stable_reads()
            instrument = adapter.instrument()
            store = adapter_module.SimulationStore.create_bound(database, profile=profile,
                cash=anchor['value']['cash'], holdings=anchor['value']['positions'],
                max_order_notional='1', fee_reserve='3', anchor=anchor)
            store.prepare(INTENT, symbol='US.AMD', side='BUY', quantity_value=1, limit_price='1')
            with core.transaction(store.db):
                store.config['futu_cycle_source_sha256'] = receipt['source_file_sha256']
                store.db.execute('UPDATE meta SET config=?', (core.encoded(store.config),))
            receipt.update(status='PREPARED_AWAITING_SEPARATE_AUTHORIZATION', instrument=instrument,
                proposal=dict(account_binding_sha256=core.fingerprint(profile), intent_id=INTENT,
                    payload=PAYLOAD, payload_sha256=core.fingerprint(PAYLOAD),
                    order_type='NORMAL', time_in_force='DAY', session='RTH',
                    max_submit_attempts=1, max_cancel_attempts=1, automatic_price_change=False,
                    fault_injection='DISCARD_SYNC_RESPONSE_THEN_EXIT_PROCESS',
                    fee_reserve='3', fee_reserve_is_actual_fee_or_guaranteed_fee_cap=False))
        else:
            store = adapter_module.SimulationStore(database)
            if (store.config.get('futu_cycle_source_sha256') != receipt['source_file_sha256']
                    or json.loads(store._row(INTENT)['payload']) != PAYLOAD
                    or store.db.execute('SELECT COUNT(*) FROM orders').fetchone()[0] != 1
                    or store.config['max_order_notional'] != '1' or store.config['fee_reserve'] != '3'):
                raise Error('cycle_source_or_frozen_terms_changed')
            if phase == 'duplicate-probe':
                if store._row(INTENT)['claim_id'] is None:raise Error('prior_durable_submit_attempt_required')
                if store.claim_submit(INTENT) is not None:raise Error('duplicate_claim_not_refused')
                receipt['status'] = 'DUPLICATE_DURABLE_CLAIM_REFUSED_NO_TRANSPORT'
            elif phase == 'admit-statement':
                receipt['statement_result'] = store.admit_statement(store._row(INTENT)['broker_id'],
                    statement=statement, source_bytes=statement_bytes)
                receipt['status'] = 'STATEMENT_ADMITTED_FRESH_RECONCILIATION_STILL_REQUIRED'
            else:
                adapter = _sdk_factory(store.profile)
                transport = ScopedTransport(adapter.context, phase, store)
                adapter.context = transport
                if phase == 'submit':
                    receipt['status'] = adapter.submit_once(store, INTENT, authorization=authorization, discard_sync_response=True)
                elif phase == 'cancel':
                    receipt['status'] = adapter.cancel(store, INTENT, authorization=authorization)
                else:
                    receipt['reconciliation'] = adapter.reconcile(store)
                    receipt['status'] = 'SCOPED_RECONCILIATION_COMPLETED'
                    # Completion still needs actual terminal/callback/statement
                    # and restart evidence across the separate phase receipts.
    except Error as exc:
        receipt.update(status='INCOMPLETE', error=str(exc))
    finally:
        if adapter is not None:
            receipt['query_evidence'] = adapter.query_evidence
            adapter.close()
        if store is not None:
            receipt['state'] = store.inspect()
            receipt['durable_dispatch_counts'] = {
                name: store.db.execute("SELECT COUNT(*) FROM events WHERE kind=?", (name,)).fetchone()[0]
                for name in ('SUBMISSION_MAY_REACH_VENUE', 'CANCEL_MAY_REACH_VENUE', 'FUTU_CYCLE_DISPATCH_STARTED')}
            store.close()
        if transport is not None:
            receipt.update(order_dispatch_attempts=transport.calls['place_order'], cancel_dispatch_attempts=transport.calls['modify_order'])
        if source_hashes() != receipt['source_file_sha256']:
            receipt.update(status='INCOMPLETE', error='cycle_source_changed_during_run')
        receipt['checked_at'] = adapter_module.stamp()
    return receipt


def install_network_guard():
    owned_listeners = []
    def guard(event, args):
        if event == 'socket.bind' and args[1] == ('127.0.0.1', 0):owned_listeners.append(args[0])
        if event == 'socket.connect' and args[1] != ('127.0.0.1', 11111):
            owned = False
            for listener in owned_listeners:
                try:
                    owned |= (listener.fileno() >= 0 and listener.getsockname() == args[1]
                              and bool(listener.getsockopt(socket.SOL_SOCKET, socket.SO_ACCEPTCONN)))
                except OSError:pass
            if not owned:raise Error('only_opend_and_owned_sdk_listener_allowed')
        if event == 'socket.getaddrinfo' and (args[0] != '127.0.0.1' or args[1] != 11111):
            raise Error('only_declared_opend_resolution_allowed')
    sys.addaudithook(guard)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=PHASES)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--profile', type=Path)
    parser.add_argument('--authorization', type=Path)
    parser.add_argument('--statement', type=Path)
    parser.add_argument('--statement-source', type=Path)
    parser.add_argument('--owned-worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.phase in ('submit', 'cancel') and args.authorization is None:
        parser.error('submit/cancel require a separately approved authorization file')
    if not args.owned_worker:
        args.output_dir.mkdir(parents=True, exist_ok=False)
        job = module('futu_cycle_job', Path(__file__).with_name('observation_job.py'))
        result = job.execute([sys.executable, '-B', str(Path(__file__).resolve()), *sys.argv[1:], '--owned-worker'],
            Path.cwd(), timeout_seconds=180, output_limit_bytes=131072, cleanup_seconds=5)
        for name in ('stdout', 'stderr'):
            (args.output_dir/(name+'.private.log')).write_text(getattr(result, name), encoding='utf-8')
        (args.output_dir/'process.private.json').write_text(json.dumps(dict(returncode=result.returncode, bounds=result.bounds), indent=2), encoding='utf-8')
        print(json.dumps(dict(phase=args.phase, returncode=result.returncode, outcome=result.bounds['outcome'], cleanup_confirmed=result.bounds['cleanup_confirmed'])))
        return result.returncode or (0 if result.bounds['outcome']=='EXITED' and result.bounds['cleanup_confirmed'] else 1)
    os.environ['APPDATA'] = str(args.output_dir.resolve()/'private-sdk-logs')
    install_network_guard()
    def read(path):return json.loads(path.read_text(encoding='utf-8-sig')) if path else None
    result = run_phase(args.phase, args.database, profile=read(args.profile), authorization=read(args.authorization),
        statement=read(args.statement), statement_bytes=args.statement_source.read_bytes() if args.statement_source else None)
    with (args.output_dir/'receipt.private.json').open('x', encoding='utf-8') as f:json.dump(result, f, indent=2, allow_nan=False)
    print(json.dumps({k:result[k] for k in ('phase','status','order_dispatch_attempts','cancel_dispatch_attempts')}))
    return 1 if result['status']=='INCOMPLETE' else 0


if __name__ == '__main__':raise SystemExit(main())
