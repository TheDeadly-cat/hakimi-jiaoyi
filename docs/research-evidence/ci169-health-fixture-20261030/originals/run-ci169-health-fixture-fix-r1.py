from pathlib import Path
from hashlib import sha256
import json
import os
import re
import subprocess
import sys
import time

P=Path(r'C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易')
E=Path(r'C:\Users\Administrator\Downloads\Hakimi-Astra-Delivery-20261029')
O=E/'ci169-health-fixture-fix-20261030-r1'
assert not O.exists(); O.mkdir()
workflow=(P/'.github/workflows/research-contracts.yml').read_text(encoding='utf-8')
block=workflow.split('- name: Run complete research-only Python contracts',1)[1].split('- name:',1)[0]
modules=re.findall(r'^\s+(tests\.[A-Za-z0-9_]+)\s*$',block,re.M)
assert len(modules)==31 and 'tests.test_research_management_boundary' in modules
name='outputs/python_quant_bot/tests/test_research_management_boundary.py'
before=sha256((P/name).read_bytes()).hexdigest()
env={k:v for k,v in os.environ.items() if not k.upper().startswith(('PYTHON','HAKIMI_'))}
env.update(PYTHONIOENCODING='utf-8',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',
    PYTHON=sys.executable,HAKIMI_TEST_PYTHON=sys.executable,HAKIMI_SKIP_LOCAL_AI_ENV='1',HAKIMI_LOAD_LOCAL_AI_ENV='0',
    HAKIMI_LOCAL_ONLY='1',HAKIMI_RUNTIME_READ_ONLY='1',HAKIMI_RUNTIME_DIR=str(O/'new-runtime'),
    HAKIMI_QUANT_WORKSPACE_DIR=str(O/'new-quant'),HAKIMI_RESEARCH_HOME=str(O/'new-research'),
    PATH=str(E/'CI147-node22-crash-20261029/portable/node-v22.23.4-win-x64')+os.pathsep+env.get('PATH',''))
command=[sys.executable,'-B','-m','unittest',*modules,'-v']
start=time.monotonic()
with (O/'complete-research-contracts.log').open('xb') as f:
    result=subprocess.run(command,cwd=P/'outputs/python_quant_bot',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180)
log=(O/'complete-research-contracts.log').read_text(encoding='utf-8')
match=re.search(r'^Ran (\d+) tests in ([0-9.]+)s',log,re.M)
after=sha256((P/name).read_bytes()).hexdigest()
passed=result.returncode==0 and match and int(match[1])==273 and re.search(r'^OK\s*$',log,re.M) and before==after
report={'status':'PASS' if passed else 'FAIL','head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=P).decode().strip(),
    'source_scope':'ONLY_HEALTH_AST_TEST_FIXTURE_CHANGED_NO_PRODUCTION_CHANGE','test_file':name,
    'sha256_before':before,'sha256_after':after,'command':command,'exit_code':result.returncode,
    'tests_run':int(match[1]) if match else None,'inner_seconds':float(match[2]) if match else None,
    'outer_seconds':time.monotonic()-start,'modules_from_workflow':modules,
    'original_failure_run':40989174236,'original_failure_head':'a0356e09da9dd493c1dc035624366b64eb2fc1c8',
    'new_bound_unbound_health_checks':True,'native_or_broker_execution':False}
with (O/'result.json').open('x',encoding='utf-8') as f: json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k not in ('command','modules_from_workflow')}),flush=True)
raise SystemExit(0 if passed else 1)
