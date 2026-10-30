"""PREPARED ONLY: execute once after root review, with new output paths."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from email.parser import BytesParser
from zipfile import ZipFile

p=argparse.ArgumentParser()
p.add_argument('--source',required=True)
p.add_argument('--package',required=True)
p.add_argument('--output',required=True)
a=p.parse_args()
source,package=Path(a.source).resolve(strict=True),Path(a.package).resolve(strict=True)
output=Path(a.output).resolve()
assert not output.exists(), 'fresh output required'
assert not output.is_relative_to(source) and not output.is_relative_to(package)
manifest_hash='a8cfa662966720fe8d46dbcdd966c08f359dc2af591168f8b8652c96be9d198a'
wheel_hash='a3bc7609fc7b60c0ca3cd2971bc8b81819338d3c88ad25d1bd3f647d781554b5'
wheel=Path(r'C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029\terminal-wheelhouse-r1\futu_api-10.7.6708-py3-none-any.whl')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(wheel)==wheel_hash
with ZipFile(wheel) as archive:
    internal_version=archive.read('futu/VERSION.txt').decode('ascii').strip()
    metadata=BytesParser().parsebytes(archive.read('futu_api-10.7.6708.dist-info/METADATA'))
    distribution_version=metadata['Version']
assert distribution_version=='10.7.6708' and internal_version=='10.07.6708'
assert sha(package/'terminal-manifest.json')==manifest_hash
relative=['exchange_terminal/__init__.py','exchange_terminal/services/__init__.py',
 'exchange_terminal/services/terminal_broker_candidate_service.py',
 'exchange_terminal/services/terminal_broker_execution_plan.py',
 'exchange_terminal/services/terminal_broker_wire_profile.py',
 'exchange_terminal/services/terminal_saved_results.py',
 'exchange_terminal/services/terminal_result_comparison.py',
 'exchange_terminal/adapters/futu_us_equity_simulate_wire_v2.py',
 'tests/__init__.py','tests/test_terminal_broker_execution_plan.py',
 'tests/test_terminal_broker_wire_profile.py','tests/test_futu_us_equity_simulate_wire_v2.py']
hashes={str(source/'outputs/python_quant_bot'/name):sha(source/'outputs/python_quant_bot'/name) for name in relative}
child=Path(__file__).with_name('pinned-codec-probe-child-r5.py').resolve(strict=True)
status=subprocess.check_output(['git','status','--porcelain=v1'],cwd=source).decode('utf-8')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source).decode().strip()
output.mkdir()
for name in ('temp','profile','sdk-appdata','test-runtime'):(output/name).mkdir()
spec={'source':str(source),'package':str(package),'output':str(output),'manifest_sha256':manifest_hash,
      'wheel_sha256':wheel_hash,'source_hashes':hashes,'git_head':commit,'git_status':status,
      'distribution_version':distribution_version,'internal_module_version':internal_version,
      'source_claim':'OFFLINE_TEST_FIXTURE_NOT_CLEAN_PRODUCTION','child_sha256':sha(child),
      'runner_sha256':sha(Path(__file__))}
with (output/'invocation.json').open('x',encoding='utf-8') as f:json.dump(spec,f,indent=2)
env=dict(os.environ)
for key in list(env):
 if key.upper().startswith(('PYTHON','HAKIMI_','FUTU_')):env.pop(key)
env.update(PYTHONIOENCODING='utf-8',TEMP=str(output/'temp'),TMP=str(output/'temp'),
 HOME=str(output/'profile'),USERPROFILE=str(output/'profile'),APPDATA=str(output/'profile'),
 LOCALAPPDATA=str(output/'profile'),FUTU_PY_APPDATA=str(output/'sdk-appdata'),
 HAKIMI_TEST_RUNTIME_DIR=str(output/'test-runtime'),HAKIMI_RUNTIME_DIR=str(output/'test-runtime'),
 HAKIMI_QUANT_WORKSPACE_DIR=str(output/'test-runtime'))
cmd=[str(package/'runtime/python/python.exe'),'-I','-S','-B','-X','utf8',str(child),
     '--input',str(output/'invocation.json')]
start=time.monotonic()
completed=None
failure=None
try:
    with (output/'stdout.log').open('xb') as out,(output/'stderr.log').open('xb') as err:
        completed=subprocess.run(cmd,cwd=output,env=env,stdout=out,stderr=err,timeout=60)
except BaseException as error:
    failure={'type':type(error).__name(),'message':str(error)[:512]}
    raise
finally:
    result={'command':cmd,'exit_code':completed.returncode if completed else None,
            'elapsed_seconds':time.monotonic()-start,'exception':failure,
            'source_hashes_unchanged':all(sha(Path(path))==digest for path,digest in hashes.items()),
            'status':'CHILD_EXIT_ZERO' if completed and completed.returncode==0 else 'FAILED_PRESERVED',
            'scope':'PINNED_CODEC_OFFLINE_PROBE_NOT_CANDIDATE_OR_NATIVE_ACCEPTANCE'}
    with (output/'runner-result.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    print(json.dumps(result))
raise SystemExit(completed.returncode)
