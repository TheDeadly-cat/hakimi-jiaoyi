"""Single approved private process: actual r4 bytes + explicit new parent source."""
from hashlib import sha256
import json
import os
from pathlib import Path
import stat
import subprocess
import time

HERE = Path(__file__).resolve().parent
PARENT = Path(r'C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易')
PACKAGE = Path(r'C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029\HakimiTrade-0.7.0.dev3-candidate-r4')
MANIFEST_SHA = 'a8cfa662966720fe8d46dbcdd966c08f359dc2af591168f8b8652c96be9d198a'
OUT = HERE/'private-process-r1'
SOURCE_NAMES = ['exchange_terminal/__init__.py', 'exchange_terminal/services/__init__.py',
    'exchange_terminal/services/terminal_broker_candidate_service.py',
    'exchange_terminal/services/terminal_broker_execution_plan.py',
    'exchange_terminal/services/terminal_broker_wire_profile.py',
    'exchange_terminal/services/terminal_saved_results.py',
    'exchange_terminal/services/terminal_result_comparison.py',
    'exchange_terminal/adapters/futu_verified_protobuf_loader.py']

def digest(path):
    return sha256(path.read_bytes()).hexdigest()

assert not OUT.exists(), 'Do not reuse or overwrite probe results'
raw = (PACKAGE/'terminal-manifest.json').read_bytes()
assert sha256(raw).hexdigest() == MANIFEST_SHA
manifest = json.loads(raw)
assert manifest['source_provenance']['git']['commit'] == 'a235e8a2f1a303f72b99797105956bcd88cba399'
site = 'runtime/python/Lib/site-packages/'
verified = {}
for name, expected in manifest['files'].items():
    relevant = name.startswith('runtime/python/') and ('/Lib/site-packages/' not in name or name.startswith(
        tuple(site + family for family in ['futu/', 'futu_api-10.7.6708.dist-info/', 'google/protobuf/',
                                            'google/_upb/', 'protobuf-7.35.1.dist-info/'])))
    if relevant:
        path = PACKAGE/name
        for item in (path, *path.parents):
            info = item.lstat()
            assert not stat.S_ISLNK(info.st_mode) and not getattr(info,'st_file_attributes',0)&0x400
        info = path.stat()
        assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        assert digest(path) == expected, name
        verified[name] = expected
sources = {str(PARENT/'outputs/python_quant_bot'/name): digest(PARENT/'outputs/python_quant_bot'/name) for name in SOURCE_NAMES}
test = PARENT/'outputs/python_quant_bot/tests/test_futu_verified_protobuf_loader.py'
OUT.mkdir()
for directory in ['temp','profile']:
    (OUT/directory).mkdir()
spec = {'schema_version':'hakimi-private-protobuf-loader-probe-v1','package':str(PACKAGE),
    'package_manifest_sha256':MANIFEST_SHA,'package_source_commit':manifest['source_provenance']['git']['commit'],
    'package_bundle_id':manifest['bundle_id'],'parent':str(PARENT),'output':str(OUT),
    'source_hashes':sources,'test_sha256':digest(test),'runtime_preflight_files':verified,
    'child_sha256':digest(HERE/'private-child.py'),'runner_sha256':digest(Path(__file__)),
    'scope':'EXPLICIT_NEW_PARENT_LOADER_NOT_INSTALLED_IN_R4; LOCAL_GENERATED_CLASS_SOURCE_ONLY'}
(OUT/'invocation.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
environment = dict(os.environ)
for key in list(environment):
    if key.upper().startswith(('PYTHON','FUTU_','HAKIMI_','PROTOBUF_','PROTOCOL_BUFFERS_')):
        environment.pop(key)
environment.update(TEMP=str(OUT/'temp'),TMP=str(OUT/'temp'),HOME=str(OUT/'profile'),USERPROFILE=str(OUT/'profile'),
                   APPDATA=str(OUT/'profile'),LOCALAPPDATA=str(OUT/'profile'))
command=[str(PACKAGE/'runtime/python/python.exe'),'-I','-S','-B','-X','utf8',str(HERE/'private-child.py'),str(OUT/'invocation.json')]
started=time.monotonic(); result=None; failure=None
try:
    with (OUT/'stdout.log').open('xb') as stdout, (OUT/'stderr.log').open('xb') as stderr:
        result=subprocess.run(command,cwd=OUT,env=environment,stdout=stdout,stderr=stderr,timeout=60)
except Exception as error:
    failure={'type':type(error).__name__,'message':str(error)[:500]}
finally:
    receipt={'command':command,'exit_code':None if result is None else result.returncode,'failure':failure,
        'elapsed_seconds':time.monotonic()-started,'source_hashes_unchanged':all(digest(Path(p))==h for p,h in sources.items()),
        'manifest_unchanged':digest(PACKAGE/'terminal-manifest.json')==MANIFEST_SHA,
        'test_unchanged':digest(test)==spec['test_sha256'],
        'status':'PRIVATE_CHILD_PASS' if result is not None and result.returncode==0 else 'FAILED_PRESERVED'}
    (OUT/'runner-result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))
raise SystemExit(result.returncode if result is not None else 1)
