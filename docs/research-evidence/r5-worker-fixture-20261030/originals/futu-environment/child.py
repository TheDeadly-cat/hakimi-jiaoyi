
import importlib.util,importlib.metadata,json,sys,socket,sqlite3,subprocess,threading,unittest
from pathlib import Path
output=Path(sys.argv[1]);source=Path(sys.argv[2]);venv=Path(sys.argv[3])
attempts={name:0 for name in ('socket','database','subprocess','thread','futu_import')}
def deny(kind):
 def blocked(*args,**kwargs):
  attempts[kind]+=1
  raise RuntimeError('futu_status_probe_forbidden:'+kind)
 return blocked
socket.socket.connect=deny('socket');socket.socket.connect_ex=deny('socket');socket.create_connection=deny('socket');socket.getaddrinfo=deny('socket')
sqlite3.connect=deny('database');subprocess.Popen.__init__=deny('subprocess');threading.Thread.start=deny('thread')
def audit(event,args):
 if event.startswith('socket.'):deny('socket')()
 if event.startswith('sqlite3.connect'):deny('database')()
 if event=='subprocess.Popen':deny('subprocess')()
 if event=='import' and args and (args[0]=='futu' or args[0].startswith('futu.')):deny('futu_import')()
sys.addaudithook(audit)
try:
 spec=importlib.util.find_spec('futu')
 assert spec is not None and Path(spec.origin).resolve().is_relative_to(venv)
 assert importlib.metadata.version('futu-api')=='10.7.6708'
 import hakimi_research
 from hakimi_research import source_layout
 assert Path(hakimi_research.__file__).resolve()==source/'src/hakimi_research/__init__.py'
 assert Path(source_layout.REPOSITORY_ROOT).resolve()==source
 sys.path[:0]=[str(source/'outputs/python_quant_bot')]
 suite=unittest.defaultTestLoader.loadTestsFromName('tests.test_futu_connection_status')
 result=unittest.TextTestRunner(verbosity=2).run(suite)
 passed=result.testsRun==32 and result.wasSuccessful() and not result.skipped and not any(attempts.values())
 proof=dict(status='PASS' if passed else 'FAIL',tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),attempts=attempts,
  sdk_imported=any(n=='futu' or n.startswith('futu.') for n in sys.modules),sdk_spec_origin=spec.origin,
  sdk_version=importlib.metadata.version('futu-api'),canonical_origin=hakimi_research.__file__,scope='LOCKED_LOCAL_SDK_SOURCE_AST_AND_FAKE_CONTEXTS_ONLY')
 with (output/'result.json').open('x',encoding='utf-8') as stream:json.dump(proof,stream,indent=2)
 raise SystemExit(0 if passed else 1)
finally:
 with (output/'guard-final.json').open('x',encoding='utf-8') as stream:json.dump(dict(attempts=attempts),stream,indent=2)
