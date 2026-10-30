"""REVIEW BEFORE EXECUTION. Actual pinned protobuf/pack helper; no contexts or IO.

This is an explicit offline fixture, not bootstrap/loader or production adapter
admission. It reads the unchanged r4 private runtime and approved parent source.
"""
import argparse
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import threading

p = argparse.ArgumentParser()
p.add_argument('--input', required=True)
a = p.parse_args()
spec = json.loads(Path(a.input).read_text(encoding='utf-8'))
source, package, output = (Path(spec[k]).resolve(strict=True) for k in ('source', 'package', 'output'))
assert sys.flags.isolated and sys.flags.no_site and sys.dont_write_bytecode
assert Path(sys.executable).resolve() == package / 'runtime/python/python.exe'
assert Path.cwd().resolve() == output
assert all(Path(entry).resolve().is_relative_to(package / 'runtime/python') for entry in sys.path)
assert not (output / 'codec-result.json').exists()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
for path, expected in spec['source_hashes'].items(): assert sha(Path(path)) == expected, path
manifest = json.loads((package / 'terminal-manifest.json').read_bytes())
assert sha(package / 'terminal-manifest.json') == spec['manifest_sha256']
site = package / 'runtime/python/Lib/site-packages'
sys.path[:0] = [str(source / 'outputs/python_quant_bot'), str(site)]

attempts = {'socket': 0, 'thread': 0, 'database': 0, 'subprocess': 0, 'forbidden_constructor': 0}
local_host_identity_reads = [0]
def denied(kind):
    def block(*args, **kwargs):
        attempts[kind] += 1
        raise AssertionError('OFFLINE_PROBE_BLOCKED_' + kind)
    return block
socket.socket.connect = denied('socket')
socket.socket.connect_ex = denied('socket')
socket.create_connection = denied('socket')
socket.getaddrinfo = denied('socket')
threading.Thread.start = denied('thread')
sqlite3.connect = denied('database')
# Preserve the class so asyncio may declare its Windows Popen subclass.
# Constructing either class still reaches this denying initializer.
subprocess.Popen.__init__ = denied('subprocess')
def audit(event, args):
    if event == 'subprocess.Popen':
        attempts['subprocess'] += 1
        raise AssertionError('OFFLINE_PROBE_SUBPROCESS_AUDIT')
    if event == 'socket.gethostname':
        local_host_identity_reads[0] += 1
        return  # Local metadata only. Never record the hostname itself.
    if event.startswith('socket.'):
        attempts['socket'] += 1
        raise AssertionError('OFFLINE_PROBE_SOCKET_AUDIT')
    if event == 'open' and len(args) >= 3 and isinstance(args[0], (str, bytes)):
        flags = args[2]
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            assert Path(os.fsdecode(args[0])).resolve().is_relative_to(output), 'write outside fresh probe'
sys.addaudithook(audit)
forbidden = {'OpenContextBase', 'OpenQuoteContext', 'OpenSecTradeContext', 'OpenFutureTradeContext',
             'OpenCryptoTradeContext', 'NetManager', 'CallbackExecutor'}
def calls(frame, event, arg):
    if event == 'call' and frame.f_code.co_name == '__init__' and frame.f_globals.get('__name__', '').startswith('futu.'):
        instance = frame.f_locals.get('self')
        if instance is not None and any(cls.__name__ in forbidden for cls in type(instance).__mro__):
            attempts['forbidden_constructor'] += 1
            raise AssertionError('OFFLINE_PROBE_FORBIDDEN_CONSTRUCTOR')
sys.setprofile(calls)


phase = ["BEFORE_IMPORT"]
def exercise():
    phase[0] = "IMPORT_PANDAS"
    import pandas
    phase[0] = "IMPORT_FUTU"
    import futu
    from futu.common import utils, constant
    from futu.common.sys_config import SysConfig
    from futu.quote import quote_query
    from futu.trade import trade_query
    from exchange_terminal.adapters import futu_us_equity_simulate_wire_v2 as codec
    from exchange_terminal.services import terminal_broker_wire_profile as wire
    from tests.test_terminal_broker_wire_profile import fixture
    from tests.test_futu_us_equity_simulate_wire_v2 import request_payload

    distribution_version = importlib.metadata.version('futu-api')
    phase[0] = 'CODEC_CHECKS'
    assert distribution_version == spec['distribution_version']
    assert futu.__version__ == spec['internal_module_version']
    assert (site/'futu/VERSION.txt').read_text(encoding='ascii').strip() == futu.__version__
    assert constant.MESSAGE_HEAD_FMT == '<1s1sI2B2I20s8s'
    assert constant.ProtoFMT.Protobuf == 0 and constant.API_PROTO_VER == 0
    # Memory-only explicit test policy. No configuration file or key is read.
    SysConfig.set_proto_fmt(constant.ProtoFMT.Protobuf)
    SysConfig.set_client_info('fictional-client', 100)
    SysConfig.set_init_rsa_file('')
    SysConfig.enable_proto_encrypt(False)
    profile = wire.prepare_wire_profile(**fixture())
    session = codec.bind_codec_session(profile, client_version=100, client_id='fictional-client',
        broker_order_id='fictional-order-44')
    names = {1001:'InitConnect', 1002:'GetGlobalState', 2001:'Trd_GetAccList', 2101:'Trd_GetFunds',
        2102:'Trd_GetPositionList', 3202:'Qot_GetStaticInfo', 3203:'Qot_GetSecuritySnapshot',
        2202:'Trd_PlaceOrder', 2201:'Trd_GetOrderList', 2205:'Trd_ModifyOrder', 2225:'Trd_GetOrderFee'}
    modules = {proto: importlib.import_module('futu.common.pb.' + name + '_pb2') for proto,name in names.items()}
    subject = codec.SimulateCodec(profile, session,
        request_classes={proto: m.Request for proto,m in modules.items()},
        response_classes={proto: m.Response for proto,m in modules.items()})
    def assign(message, values):
        for name, value in values.items():
            field = message.DESCRIPTOR.fields_by_name[name]
            if field.is_repeated:
                target = getattr(message, name)
                for element in value:
                    if field.message_type is not None: assign(target.add(), element)
                    else: target.append(element)
            elif field.message_type is not None: assign(getattr(message,name),value)
            else: setattr(message,name,value)
    def sdk_frame(proto, serial, message):
        status, text, raw = utils._joint_head(proto, 0, message.ByteSize(), message, 33, serial, False)
        assert status == 0 and not text and type(raw) is bytes
        assert raw == codec.pack_plaintext_frame(proto, serial, message.SerializeToString())
        return raw
    checks, frames = [], {}
    acc, conn, env, market = 900000000000001, 33, constant.TrdEnv.SIMULATE, constant.TrdMarket.US
    # These are the actual pinned SDK request constructors, with an explicit,
    # narrowly fixed parameter set. They only serialize in this isolated process.
    packers = {
     'quote_init': lambda: quote_query.InitConnect.pack_req(100,'fictional-client',False,False,0,0),
     'trade_init': lambda: quote_query.InitConnect.pack_req(100,'fictional-client',False,False,0,0),
     'quote_runtime': lambda: quote_query.GlobalStateQuery.pack_req(22,11),
     'trade_accounts': lambda: trade_query.GetAccountList.pack_req(22,conn,constant.TrdCategory.SECURITY,False),
     'trade_funds': lambda: trade_query.AccInfoQuery.pack_req(acc,market,env,conn,True,constant.Currency.USD,constant.AssetCategory.US),
     'trade_positions': lambda: trade_query.PositionListQuery.pack_req('TSLA',None,None,env,acc,market,conn,
                          True,market,constant.AssetCategory.US,constant.Currency.USD,False),
     'quote_security': lambda: quote_query.StockBasicInfoQuery.pack_req(constant.Market.US,11,
                          constant.SecurityType.STOCK,['US.TSLA'],constant.SecurityFirm.NONE),
     'quote_snapshot': lambda: quote_query.MarketSnapshotQuery.pack_req(['US.TSLA'],11,constant.SecurityFirm.NONE),
     'trade_submit': lambda: trade_query.PlaceOrder.pack_req(constant.TrdSide.BUY,constant.OrderType.NORMAL,
                          20.00000001,3,'TSLA',0,env,constant.Market.US,acc,market,conn,None,
                          constant.TimeInForce.DAY,False,constant.Session.RTH,None,None,None,None,
                          constant.SubAccType.NONE,None,None),
     'trade_observe': lambda: trade_query.OrderListQuery.pack_req('fictional-order-44',[],'TSLA',None,None,
                          env,acc,market,conn,True,market),
     'trade_cancel': lambda: trade_query.ModifyOrder.pack_req(constant.ModifyOrderOp.CANCEL,'fictional-order-44',
                          0,0,0,env,acc,market,conn,None,None,None,None),
     'trade_fees': lambda: trade_query.OrderFeeQuery.pack_req(['fictional-order-44'],env,acc,market,conn),
    }
    for action, (channel, proto) in wire.WIRE_ACTIONS.items():
        if proto not in modules or wire.PROTOCOL_LIMITS[action] == 0: continue
        status, text, raw, actual_proto, serial = packers[action]()
        assert status == 0 and not text and actual_proto == proto
        request = modules[proto].Request(); request.ParseFromString(raw[44:])
        assert request.IsInitialized()
        assert raw == sdk_frame(proto,serial,request)
        result = subject.validate_request(profile, action, raw)
        assert result.serial == serial
        frames[action] = {'request_hex': raw.hex(), 'request_sha256': result.frame_sha256,
                          'protobuf_class': request.DESCRIPTOR.full_name}
        checks.append(action + ':ACTUAL_SDK_PACK_REQ_REQUEST_BYTES_MATCH')
        if action.endswith('_init'):
            response = modules[1001].Response(); response.retType=0
            assign(response.s2c,dict(serverVer=100,loginUserID=22,connID=11 if channel=='quote' else 33,
                                   connAESKey='FICTIONAL_NOT_A_REAL_KEY',keepAliveInterval=30))
            assert response.IsInitialized()
            binding = subject.accept_handshake(profile,channel,serial,sdk_frame(1001,serial,response)).as_dict()
            assert binding[channel+'_connection_id'] == (11 if channel=='quote' else 33)
            assert 'connAESKey' not in binding
            checks.append(action+':ACTUAL_RESPONSE_REBINDS_NONE_SESSION_ONLY')

    for field, value in [('trdSide',3), ('qty',3.5), ('price',20.00000002), ('adjustPrice',True),
                         ('timeInForce',1), ('session',3), ('fillOutsideRTH',True)]:
        request = modules[2202].Request(); assign(request, request_payload('trade_submit',77))
        setattr(request.c2s,field,value)
        try: subject.validate_request(profile,'trade_submit',sdk_frame(2202,77,request))
        except codec.CodecError: checks.append('REJECT_' + field)
        else: raise AssertionError('scope escape: ' + field)
    request = modules[2202].Request(); assign(request,request_payload('trade_submit',77));request.c2s.header.trdEnv=1
    try: subject.validate_request(profile,'trade_submit',sdk_frame(2202,77,request))
    except codec.CodecError: checks.append('REJECT_REAL_BYTES')
    else: raise AssertionError('REAL accepted')

    response = modules[1002].Response(); response.retType=0
    assign(response.s2c,dict(marketHK=0,marketUS=0,marketSH=0,marketSZ=0,marketHKFuture=0,
                           qotLogined=False,trdLogined=False,serverVer=100,serverBuildNo=0,time=0))
    assert response.IsInitialized()
    raw = sdk_frame(1002,77,response)
    decoded = subject.decode_response(profile,'quote_runtime',77,raw)
    fields = decoded.fields()['s2c']['value']
    assert fields['localTime'] == {'present':False,'value':None}
    assert fields['time'] == {'present':True,'value':0}
    assert decoded.raw_frame == raw
    checks.append('ACTUAL_OPTIONAL_LOCALTIME_ABSENT_REQUIRED_TIME_EXPLICIT_ZERO')
    response.s2c.localTime=0
    decoded = subject.decode_response(profile,'quote_runtime',77,sdk_frame(1002,77,response))
    assert decoded.fields()['s2c']['value']['localTime'] == {'present':True,'value':0.0}
    checks.append('ACTUAL_OPTIONAL_LOCALTIME_EXPLICIT_ZERO_DISTINCT')

    loaded = {}
    for name, module in list(sys.modules.items()):
        filename = getattr(module,'__file__',None)
        if not filename: continue
        path = Path(filename).resolve()
        if name == 'futu' or name.startswith('futu.'):
            assert path.is_relative_to(site/'futu'), name
        if path.is_relative_to(package) and path.is_file():
            rel = path.relative_to(package).as_posix()
            assert sha(path) == manifest['files'][rel], rel
            loaded[name] = {'path':str(path),'sha256':sha(path)}
        if path.is_relative_to(source/'outputs/python_quant_bot'):
            assert str(path) in spec['source_hashes'], str(path)
    for path, expected in spec['source_hashes'].items(): assert sha(Path(path)) == expected, path
    assert all(value == 0 for value in attempts.values()), attempts
    assert not any(name == 'exchange_terminal.server' for name in sys.modules)
    assert len(threading.enumerate()) == 1
    sys.setprofile(None)
    result = {'status':'PASS_OFFLINE_PINNED_PROTOBUF_AND_PLAINTEXT_PACK_ONLY',
     'production_adapter_available':False,'native_or_opend_compatibility':'NOT_TESTED',
     'encrypted_transport':'NOT_IMPLEMENTED','source_scope':'EXPLICIT_HASH_BOUND_SOURCE_BYTES_OFFLINE_TEST',
     'package_manifest_sha256':spec['manifest_sha256'],'wheel_sha256':spec['wheel_sha256'],
     'source_hashes':spec['source_hashes'],'sdk_distribution_version':distribution_version,
     'sdk_module_version':futu.__version__,'checks':checks,
     'attempts':attempts,'local_host_identity_reads':local_host_identity_reads[0],'private_runtime':str(sys.executable),'flags':{'isolated':sys.flags.isolated,
     'no_site':sys.flags.no_site,'dont_write_bytecode':sys.dont_write_bytecode},
     'loaded_package_files':loaded,'permissions':profile.as_dict()['permissions'],
     'business_runs':0,'contexts_constructed':0,'frames_file':'request-frames.json'}
    with (output/'request-frames.json').open('x',encoding='utf-8') as f:json.dump(frames,f,indent=2)
    with (output/'codec-result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps({'status':result['status'],'checks':len(checks),'sdk_version':futu.__version__,
                      'attempts':attempts,'production_adapter_available':False}))


failure = None
try:
    exercise()
except BaseException as error:
    failure = {"type": type(error).__name__, "message": str(error)[:512]}
    raise
finally:
    sys.setprofile(None)
    guard = {"phase": phase[0], "attempts": attempts, "exception": failure,
             "local_host_identity_reads": local_host_identity_reads[0],
             "source_hashes_unchanged": all(sha(Path(path)) == digest for path, digest in spec["source_hashes"].items()),
             "scope": "OFFLINE_CODEC_PROBE_GUARDS_NOT_PRODUCTION_ACCEPTANCE"}
    with (output/"guard-final.json").open("x", encoding="utf-8") as stream:
        json.dump(guard, stream, indent=2)
