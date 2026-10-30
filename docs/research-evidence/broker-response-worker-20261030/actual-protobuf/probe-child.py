"""Actual pinned pb2 classes, synthetic bytes, no Futu top-level import or IO."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import importlib
import importlib.abc
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading
import types

spec = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
source, package, output = (Path(spec[key]).resolve(strict=True) for key in ('source', 'package', 'output'))
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert Path(sys.executable).resolve() == package/'runtime/python/python.exe'
assert Path.cwd().resolve() == output
assert all(Path(entry).resolve().is_relative_to(package/'runtime/python') for entry in sys.path)
manifest_path = package/'terminal-manifest.json'
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(manifest_path) == spec['package_manifest_sha256']
assert sha(Path(__file__)) == spec['child_sha256']
manifest = json.loads(manifest_path.read_bytes())
for path, expected in spec['source_hashes'].items():
    assert sha(Path(path)) == expected, path
site = package/'runtime/python/Lib/site-packages'
pb_root = site/'futu/common/pb'
attempts = {'socket': 0, 'database': 0, 'subprocess': 0, 'thread': 0, 'futu_import': 0}
local_hostname_reads = [0]
phase = ['SETUP']
checked_files = {}
checks, cases, failures = [], [], []

def verify_file(path):
    path = Path(path).resolve()
    if path.is_relative_to(package):
        # Modules inside the private stdlib ZIP are covered by that exact ZIP.
        if not path.is_file():
            path = next((ancestor for ancestor in path.parents if ancestor.suffix == '.zip' and ancestor.is_file()), None)
            assert path is not None, 'Unverified runtime module container'
        relative = path.relative_to(package).as_posix()
        expected = manifest['files'][relative]
    else:
        expected = spec['source_hashes'][str(path)]
    actual = sha(path)
    assert actual == expected, str(path)
    checked_files[str(path)] = actual

def deny(kind):
    def blocked(*args, **kwargs):
        attempts[kind] += 1
        raise AssertionError('OFFLINE_RESPONSE_PROBE_FORBIDDEN_' + kind)
    return blocked

socket.socket.connect = deny('socket')
socket.socket.connect_ex = deny('socket')
socket.create_connection = deny('socket')
socket.getaddrinfo = deny('socket')
sqlite3.connect = deny('database')
subprocess.Popen.__init__ = deny('subprocess')
threading.Thread.start = deny('thread')

def audit(event, args):
    if event == 'socket.gethostname':
        local_hostname_reads[0] += 1
        return
    if event.startswith('socket.'):
        deny('socket')()
    if event.startswith('sqlite3.connect'):
        deny('database')()
    if event == 'subprocess.Popen':
        deny('subprocess')()
    if event == 'open' and len(args) >= 3 and isinstance(args[0], (str, bytes)):
        path = Path(os.fsdecode(args[0])).resolve()
        flags = args[2]
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            assert path.is_relative_to(output), 'Write outside new probe output: ' + str(path)
        else:
            assert path.is_relative_to(package) or path.is_relative_to(output) or path == Path(__file__).resolve() or str(path) in spec['source_hashes'], 'Unapproved read: ' + str(path)
sys.addaudithook(audit)

class VerifiedSourceLoader(importlib.machinery.SourceFileLoader):
    def get_code(self, fullname):
        verify_file(self.path)
        # Compile the verified source bytes; never accept a sibling pyc cache.
        return compile(Path(self.path).read_bytes(), self.path, 'exec', dont_inherit=True)

class ScopedFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'futu' or fullname.startswith('futu.'):
            deny('futu_import')()
        short = fullname.rsplit('.', 1)[-1]
        if fullname.startswith('hakimi_probe_pb.') or '.' not in fullname and short.endswith('_pb2'):
            assert short in spec['allowed_pb'], 'Unapproved pb2 dependency: ' + fullname
            location = spec['allowed_pb'][short]['path']
            verify_file(location)
            return importlib.util.spec_from_file_location(fullname, location, loader=VerifiedSourceLoader(fullname, location))
        found = importlib.machinery.PathFinder.find_spec(fullname, path)
        if found is None or found.origin in (None, 'built-in', 'frozen'):
            return found
        verify_file(found.origin)
        if str(found.origin).endswith('.py') and Path(found.origin).is_file():
            found.loader = VerifiedSourceLoader(fullname, found.origin)
        return found

sys.meta_path.insert(0, ScopedFinder())
sys.path[:0] = [str(source/'outputs/python_quant_bot'), str(site)]
namespace = types.ModuleType('hakimi_probe_pb')
namespace.__path__ = [str(pb_root)]
sys.modules['hakimi_probe_pb'] = namespace

def exercise():
    phase[0] = 'IMPORT_VERIFIED_PROTOBUF_AND_PARENT_MODULES'
    from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
    from exchange_terminal.services import terminal_broker_wire_profile as wire
    from exchange_terminal.services import terminal_broker_execution_plan as contract
    from exchange_terminal.services import terminal_broker_execution_journal as journal
    from exchange_terminal.services import terminal_broker_response_facts as facts_module
    from tests.test_terminal_broker_wire_profile import fixture, NOW
    from tests.test_futu_us_equity_simulate_wire_v2 import request_payload
    names = {1001:'InitConnect', 1002:'GetGlobalState', 2001:'Trd_GetAccList', 2101:'Trd_GetFunds',
             2102:'Trd_GetPositionList', 3202:'Qot_GetStaticInfo', 3203:'Qot_GetSecuritySnapshot',
             2202:'Trd_PlaceOrder', 2201:'Trd_GetOrderList', 2205:'Trd_ModifyOrder', 2225:'Trd_GetOrderFee'}
    modules = {proto: importlib.import_module('hakimi_probe_pb.' + name + '_pb2') for proto, name in names.items()}
    profile = wire.prepare_wire_profile(**fixture())
    original_order = 'fictional-order-44'
    session = codec.bind_codec_session(profile, client_version=100, client_id='fictional-client',
        quote_connection_id=11, quote_user_id=22, trade_connection_id=33, trade_user_id=22,
        broker_order_id=original_order)
    subject = codec.SimulateCodec(profile, session,
        request_classes={proto: module.Request for proto, module in modules.items()},
        response_classes={proto: module.Response for proto, module in modules.items()})
    head = {'trdEnv': 0, 'accID': 900000000000001, 'trdMarket': 2}
    order = {'trdSide': 1, 'orderType': 1, 'orderStatus': 10, 'orderID': 0, 'orderIDEx': original_order,
             'code': 'TSLA', 'name': 'SYNTHETIC_TEST', 'qty': 3.0, 'price': 20.00000001,
             'createTime': '2026-10-30 08:00:00', 'updateTime': '2026-10-30 08:00:01',
             'fillQty': 2.0, 'fillAvgPrice': 19.0, 'secMarket': 2, 'currency': 2,
             'trdMarket': 2, 'timeInForce': 0, 'fillOutsideRTH': False, 'session': 1}
    funds = {'power': 3000.0, 'totalAssets': 2000.0, 'cash': 1000.0, 'marketVal': 500.0,
             'frozenCash': 100.0, 'debtCash': 50.0, 'avlWithdrawalCash': 900.0,
             'currency': 2, 'availableFunds': 800.0}
    position = {'positionID': 7, 'positionSide': 0, 'code': 'TSLA', 'name': 'SYNTHETIC_TEST',
                'qty': 3.0, 'canSellQty': 2.0, 'price': 20.0, 'val': 60.0, 'plVal': 0.0,
                'currency': 2, 'secMarket': 2, 'trdMarket': 2, 'accID': head['accID']}
    account = {'trdEnv': 0, 'accID': head['accID'], 'trdMarketAuthList': [2]}
    fee = {'orderIDEx': original_order, 'feeAmount': 0.25}
    bases = {
        'trade_submit': {'header': head, 'orderIDEx': original_order},
        'trade_cancel': {'header': head, 'orderID': 0, 'orderIDEx': original_order},
        'trade_observe': {'header': head, 'orderList': [order]},
        'trade_accounts': {'accList': [account]},
        'trade_funds': {'header': head, 'funds': funds},
        'trade_positions': {'header': head, 'positionList': [position]},
        'trade_fees': {'header': head, 'orderFeeList': [fee]},
    }
    serial = [100]
    def assign(message, values):
        for name, value in values.items():
            field = message.DESCRIPTOR.fields_by_name[name]
            repeated = field.is_repeated if hasattr(field, 'is_repeated') else field.label == field.LABEL_REPEATED
            if repeated:
                target = getattr(message, name)
                for element in value:
                    if field.message_type is not None:
                        assign(target.add(), element)
                    else:
                        target.append(element)
            elif field.message_type is not None:
                target = getattr(message, name)
                target.SetInParent()
                assign(target, value)
            else:
                setattr(message, name, value)

    def call(label, action, response_body, *, expected_status=None, expected_error=None, check=None,
             allow_partial=False, request_change=None, response_serial_delta=0, at=None):
        serial[0] += 1
        number, proto = serial[0], wire.WIRE_ACTIONS[action][1]
        request = modules[proto].Request()
        payload = request_payload(action, number)
        if request_change:
            request_change(payload)
        assign(request, payload)
        assert request.IsInitialized(), request.FindInitializationErrors()
        request_frame = codec.pack_plaintext_frame(proto, number, request.SerializeToString(deterministic=True))
        response = modules[proto].Response()
        assign(response, response_body)
        if not allow_partial:
            assert response.IsInitialized(), response.FindInitializationErrors()
        encoded = response.SerializePartialToString(deterministic=True) if allow_partial else response.SerializeToString(deterministic=True)
        response_frame = codec.pack_plaintext_frame(proto, number + response_serial_delta, encoded)
        operation = 'synthetic-facts-' + str(number)
        action_payload = {'profile': profile.as_dict(), 'action': action, 'operation_id': operation,
            'frame_sha256': hashlib.sha256(request_frame).hexdigest(), 'frame_bytes': len(request_frame),
            'authorization_id': '8'*64,
            'broker_order_id': original_order if action in ('trade_cancel','trade_observe','trade_fees') else None}
        event = {'schema_version': journal.SCHEMA, 'seq': 1, 'previous': '0'*64, 'at': NOW.isoformat(),
                 'kind': 'ACTION', 'payload': action_payload, 'request_id': operation,
                 'request_hash': contract.digest({'kind':'ACTION','payload':action_payload}),
                 'result': {'status':'DISPATCH_INTENT','operation_id':operation,'action':action,
                            'attempt_count':1,'dispatch_authorization_granted':False}}
        event = {**event, 'id':contract.digest(event)}
        row = {'label': label, 'action': action, 'request_frame_hex':request_frame.hex(),
               'response_frame_hex':response_frame.hex(), 'action_receipt_id':event['id'],
               'action_receipt_scope':'SYNTHETIC_SEALED_FIXTURE_NOT_A_DATABASE_OR_AUTHENTICATED_BROKER_RECORD'}
        try:
            result = facts_module.verify_response_facts(profile=profile, codec=subject, action_receipt=event,
                expected_action_receipt_id=event['id'], request_frame=request_frame, response_frame=response_frame,
                received_at=at or NOW+timedelta(seconds=1)).as_dict()
            row['result'] = result
            assert expected_error is None, 'Expected refusal: ' + str(expected_error)
            if expected_status is not None:
                assert result['status'] == expected_status, (result['status'],expected_status)
            assert result['source_authenticated'] is False and result['test_only'] is True
            assert result['journal_observation_ready'] is False and result['reservation_ready'] is False
            assert result['economic_acceptance'] == 'NOT_INFERRED'
            assert len(result['permissions']) == 9 and not any(result['permissions'].values())
            assert result['id'] == contract.digest({k:v for k,v in result.items() if k!='id'})
            assert result['request_frame']['sha256'] == hashlib.sha256(request_frame).hexdigest()
            assert result['response_frame']['sha256'] == hashlib.sha256(response_frame).hexdigest()
            if check:
                check(result)
        except facts_module.ResponseFactsError as error:
            row['error'] = str(error)
            assert expected_error is not None and expected_error in str(error), (str(error),expected_error)
        cases.append(row)
        checks.append(label)
        return row.get('result')

    def require(value, detail):
        assert value, detail

    phase[0] = 'ACTUAL_REQUEST_RESPONSE_FACTS'
    expected = {'trade_submit':'ACK_SCOPE_MATCHED','trade_cancel':'CANCEL_ACK_NOT_TERMINAL',
                **{action:'READ_FACTS_MATCHED' for action in bases if action not in ('trade_submit','trade_cancel')}}
    matched = {}
    for action, body in bases.items():
        matched[action] = call('matched-'+action, action, {'retType':0,'s2c':deepcopy(body)}, expected_status=expected[action])
        call('api-error-not-rejection-'+action, action, {'retType':-1,'retMsg':'SYNTHETIC_ERROR','errCode':42},
             expected_status='API_ERROR_RESPONSE', check=lambda result: require(result['facts']=={},'API error cannot become rejection/facts'))
    require(matched['trade_submit']['facts']['broker_order_id']==original_order,'Opaque ACK identity')
    require(matched['trade_cancel']['facts']['order_terminal_confirmed'] is False,'Cancel ACK is not terminal')
    observed = matched['trade_observe']
    require(observed['facts']['filled_quantity']=='2.0','Actual fill quantity')
    require(observed['derived']['fill_notional_estimate']=='38.00' and observed['derived']['exact_notional'] is False,'Estimate only')
    require(observed['facts']['filled_notional'] is None and observed['facts']['fees_final'] is None,'No invented exact economics')
    cash = matched['trade_funds']['facts']
    require((cash['cash'],cash['available_funds'],cash['power'])==('1000.0','800.0','3000.0'),'Cash/available/power separation')
    require(cash['cash_available_for_reservation'] is None,'No cash snapshot inferred')
    positions = matched['trade_positions']['facts']
    require(positions['owner_positions'] is None and positions['owner_allocation_verified'] is False,'No strategy owner inferred')
    require(positions['broker_positions'][0]['owner_scope_id'] is None,'No broker owner mapping')
    fees = matched['trade_fees']['facts']
    require(fees['fee_amount']=='0.25' and fees['currency'] is None and fees['fees_final'] is None,'Fee lacks currency/finality')

    for action in bases:
        if action == 'trade_accounts':
            continue
        for field, replacement in (('trdEnv',1),('accID',900000000000002),('trdMarket',1)):
            body = deepcopy(bases[action]); body['header'][field]=replacement
            call('wrong-'+field+'-'+action, action, {'retType':0,'s2c':body}, expected_error='response_scope_mismatch')
    body = deepcopy(bases['trade_accounts']); body['accList'][0]['trdEnv']=1
    call('wrong-account-environment','trade_accounts',{'retType':0,'s2c':body},expected_error='response_scope_mismatch')
    body = deepcopy(bases['trade_accounts']); body['accList'][0]['accID']=900000000000002
    call('target-account-not-found','trade_accounts',{'retType':0,'s2c':body},expected_status='NOT_FOUND_UNCONFIRMED')
    for action, field in (('trade_observe','orderList'),('trade_positions','positionList'),
                          ('trade_accounts','accList'),('trade_fees','orderFeeList')):
        body = deepcopy(bases[action]); body[field]=[]
        call('empty-'+action,action,{'retType':0,'s2c':body},expected_status='NOT_FOUND_UNCONFIRMED')
        body = deepcopy(bases[action]); body[field].append(deepcopy(body[field][0]))
        call('duplicate-'+action,action,{'retType':0,'s2c':body},expected_error='duplicate')
    for action in ('trade_cancel','trade_observe','trade_fees'):
        body = deepcopy(bases[action])
        if action=='trade_cancel':body['orderIDEx']='OTHER-ORDER'
        else:body['orderList' if action=='trade_observe' else 'orderFeeList'][0]['orderIDEx']='OTHER-ORDER'
        call('wrong-order-'+action,action,{'retType':0,'s2c':body},expected_error='response_original_order_id_mismatch')

    def presence(field, expected_value):
        return lambda result: require(result['facts'][field] == expected_value,'Missing field must not be synthesized: '+field)
    body = deepcopy(bases['trade_funds']); del body['funds']['availableFunds']
    absent = call('available-funds-absent','trade_funds',{'retType':0,'s2c':body},check=presence('available_funds',None))
    require(absent['presence']['s2c']['value']['funds']['value']['availableFunds']=={'present':False,'value':None},'Actual optional field absent')
    body['funds']['availableFunds']=0.0
    present = call('available-funds-explicit-zero','trade_funds',{'retType':0,'s2c':body},check=presence('available_funds','0.0'))
    require(present['presence']['s2c']['value']['funds']['value']['availableFunds']=={'present':True,'value':0.0},'Explicit zero presence')
    body = deepcopy(bases['trade_fees']); del body['orderFeeList'][0]['feeAmount']
    call('fee-amount-absent','trade_fees',{'retType':0,'s2c':body},check=presence('fee_amount',None))
    body['orderFeeList'][0]['feeAmount']=0.0
    zero = call('fee-amount-explicit-zero','trade_fees',{'retType':0,'s2c':body},check=presence('fee_amount','0.0'))
    require(zero['facts']['fees_final'] is None,'Zero amount is not final fee evidence')
    body = deepcopy(bases['trade_observe']); del body['orderList'][0]['fillQty']; del body['orderList'][0]['fillAvgPrice']
    absent = call('fill-fields-absent','trade_observe',{'retType':0,'s2c':body},check=presence('filled_quantity',None))
    require(absent['derived']=={},'No missing fill multiplication')
    body = deepcopy(bases['trade_observe']); body['orderList'][0].update(orderStatus=11,fillQty=3.0,fillAvgPrice=19.0)
    terminal = call('terminal-status-not-final-economics','trade_observe',{'retType':0,'s2c':body},expected_status='READ_FACTS_MATCHED')
    require(terminal['facts']['fees_final'] is None and terminal['facts']['filled_notional'] is None,'Terminal status does not complete economics')
    call('missing-s2c','trade_submit',{'retType':0},expected_status='INCOMPLETE_EVIDENCE')
    call('missing-required-retType','trade_submit',{'retMsg':'SYNTHETIC_MISSING_REQUIRED'},allow_partial=True,expected_error='protobuf_required_fields_missing')
    call('wrong-response-serial','trade_submit',{'retType':0,'s2c':deepcopy(bases['trade_submit'])},
         response_serial_delta=1,expected_error='header_request_binding_invalid')
    call('late-read-keeps-expired-fact','trade_submit',{'retType':0,'s2c':deepcopy(bases['trade_submit'])},
         at=NOW+timedelta(minutes=11),expected_status='ACK_SCOPE_MATCHED',
         check=lambda result: require(result['received_after_profile_expiry'] is True,'Late response is retained as fact'))
    require(not any(name=='futu' or name.startswith('futu.') for name in sys.modules),'Futu top-level must never load')
    require(not any(name=='exchange_terminal.server' for name in sys.modules),'No server import')
    require(len(threading.enumerate())==1,'No background threads')
    for name, module in list(sys.modules.items()):
        filename = getattr(module,'__file__',None)
        if filename and name!='__main__' and getattr(getattr(module,'__spec__',None),'origin',None)!='frozen':
            verify_file(filename)
    for path, expected_hash in spec['source_hashes'].items():
        assert sha(Path(path))==expected_hash,path
    assert all(value==0 for value in attempts.values()),attempts
    result = {'status':'PASS_ACTUAL_PINNED_PROTOBUF_SYNTHETIC_RESPONSE_FACTS', 'checks':checks,
              'action_count':len(bases),'check_count':len(checks),'source_hashes':spec['source_hashes'],
              'package_manifest_sha256':spec['package_manifest_sha256'],'wheel_sha256':spec['wheel_sha256'],
              'source_scope':spec['source_scope'],'package_source_commit':spec['package_source_commit'],
              'parent_git_head':spec['parent_git_head'],'permissions':profile.as_dict()['permissions'],
              'attempts':attempts,'local_hostname_reads':local_hostname_reads[0],'futu_top_level_imported':False,
              'contexts_constructed':0,'database_connections':0,'business_runs':0,
              'private_runtime':sys.executable,'flags':{'isolated':sys.flags.isolated,'no_site':sys.flags.no_site,'dont_write_bytecode':sys.dont_write_bytecode},
              'checked_package_and_source_files':checked_files,'facts_authenticated':False,
              'production_transport_available':False,'native_opend_market_or_authorization_acceptance':'NOT_PERFORMED',
              'action_receipts':'Explicit synthetic sealed ACTION fixtures; no journal database provenance asserted',
              'fixtures':'All protobuf scalar and row values are synthetic; fixture manifest metadata is not actual account evidence'}
    with (output/'response-cases.json').open('x',encoding='utf-8') as stream:
        json.dump(cases,stream,indent=2)
    with (output/'probe-result.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps({'status':result['status'],'checks':len(checks),'actions':len(bases),'attempts':attempts}))

failure = None
try:
    exercise()
except BaseException as error:
    failure = {'type':type(error).__name__,'message':str(error)[:1000]}
    if cases:
        with (output/'partial-response-cases.json').open('x',encoding='utf-8') as stream:
            json.dump(cases,stream,indent=2)
    raise
finally:
    guard = {'phase':phase[0],'exception':failure,'completed_checks':checks,'attempts':attempts,
             'local_hostname_reads':local_hostname_reads[0],
             'futu_top_level_imported':any(name=='futu' or name.startswith('futu.') for name in sys.modules),
             'source_hashes_unchanged':all(sha(Path(path))==digest for path,digest in spec['source_hashes'].items()),
             'checked_package_and_source_files':checked_files}
    with (output/'guard-final.json').open('x',encoding='utf-8') as stream:
        json.dump(guard,stream,indent=2)
