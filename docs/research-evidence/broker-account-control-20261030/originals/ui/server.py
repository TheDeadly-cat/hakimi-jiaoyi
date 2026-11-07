"""Offline UI harness: candidate/research fixtures, real account-control service."""
import json, sys, hashlib, re
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, unquote
REPO=Path(r'C:\Users\Administrator\.codex\worktrees\insights-github-20261022\哈基米v2交易')
QA=Path(__file__).parent
sys.path.insert(0,str(REPO/'outputs/python_quant_bot'))
def audit(event,args):
    if event=='socket.connect': raise RuntimeError('Outbound socket blocked by offline fixture')
sys.addaudithook(audit)
from exchange_terminal.services.terminal_broker_account_control import AccountControl, bind_host_root, PERMISSIONS, SCHEMA
ROOT=bind_host_root(QA/'synthetic-shared-control',program_root=REPO,record_domain='SYNTHETIC_TEST')
STATIC=REPO/'outputs/python_quant_bot/exchange_terminal/static'
SIM,LIVE='OFFICIAL_SIMULATION','LIVE_CANDIDATE'
candidate_permissions={key:False for key in ['external_connection_allowed','submit_allowed','query_allowed','cancel_allowed','unlock_allowed','adapter_installed','automatic_resume','automatic_retry']}
configs={};events=[];drop_next=False
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def control(p):
    config=configs[p['config_id']]
    assert p['mode']==config['mode']
    return AccountControl(ROOT,mode=p['mode'],account_id=config['config']['account_id'])
def account_read(p):return {**control(p).read(p.get('request_id')),'config_id':p['config_id']}
def page():
    css=re.search(r'<style>(.*?)</style>',(REPO/'outputs/python_quant_bot/vendor/research/hakimi_terminal_research/resources/desktop.html').read_text(encoding='utf-8'),re.S).group(1)
    return '''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>券商候选账户控制 · 离线测试夹具</title><style>'''+css+'''</style><main class="main" style="margin:0;max-width:1180px;padding:24px"><p class="notice">离线测试夹具：研究与候选为合成资料；账户控制使用独立临时目录，无券商连接。</p><div id="host"></div></main>
<script src="/terminal-broker-account-control-ui.js"></script><script src="/terminal-broker-plan-ui.js"></script><script src="/terminal-broker-candidate-ui.js"></script><script>
const params=new URLSearchParams(location.search);
async function api(resource,method='GET',payload){const response=await fetch('/api/quant/'+resource+(params.has('unavailable')?'?unavailable=1':''),{method,headers:{'Content-Type':'application/json'},...(payload?{body:JSON.stringify(payload)}:{})});const result=await response.json();if(!response.ok)throw Error(result.error);return result;}
async function perform(action,payload,callbacks){const result=await api('actions/'+action,'POST',payload);if(result)await callbacks.onSuccess(result);return result;}
const source={kind:'terminal_run',id:'a'.repeat(64),label:'合成测试研究 · 已完成'};
window.fixture=installTerminalBrokerCandidateUI({host:document.querySelector('#host'),api,perform,stopCandidate:payload=>api('broker-candidate/stop','POST',payload),stopAccount:payload=>api('broker-account/stop','POST',payload)});
fixture.setSources([source]);fixture.reveal();window.fixtureBusy=value=>{fixture.controller.state.busy=value;fixture.setSources([source]);};
</script></html>'''
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,value,status=200,kind='application/json'):
        data=(json.dumps(value,ensure_ascii=False) if kind=='application/json' else value).encode('utf-8')
        self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
    def do_GET(self):
        url=urlparse(self.path)
        if url.path=='/':return self.send(page(),kind='text/html')
        if url.path=='/favicon.ico':return self.send('',kind='text/plain')
        if url.path.endswith('.js') and (STATIC/url.path[1:]).is_file():return self.send((STATIC/url.path[1:]).read_text(encoding='utf-8'),kind='application/javascript')
        if url.path=='/qa/status':return self.send({'events':events,'db_files':[str(p.relative_to(QA)) for p in QA.rglob('*.sqlite3')],'configs':list(configs)})
        try:
            raw=url.path.removeprefix('/api/quant/');name,_,encoded=raw.partition('/');p=json.loads(unquote(encoded)) if encoded else None
            events.append({'method':'GET','resource':name,'payload':p})
            if name=='terminal_broker_status':return self.send({'schema_version':'hakimi-broker-candidate-v2','connection_state':'NOT_CONNECTED','permissions':candidate_permissions,'modes':[{'mode':mode,'connected':False,'permissions':candidate_permissions,'control':{'new_intents_blocked':False,'revision':0,'latest_control_receipt_id':None,'latest_stop_receipt_id':None,'resume_allowed':False}} for mode in [SIM,LIVE]]})
            if name=='terminal_broker_research':return self.send({'reference':p['reference'],'binding':{'status':'COMPLETED','report_id':p['reference']['id'],'report_hash':p['reference']['id'],'task_version':1},'display':{'symbol':'TEST','currency':'USD','asset_class':'US_EQUITY'},'permissions':candidate_permissions})
            if name=='terminal_broker_check':return self.send({'mode':p['mode'],'config_id':p['config_id'],'permissions':candidate_permissions,'connected':False,'account_verified':False,'asset_rules_verified':False,'fee_verified':False,'missing':[],'blockers':[],'status':'OFFLINE_PREVIEW_ONLY','security_binding':{'status':'MATCHED_SAVED_DECLARATION'}})
            if name in ['terminal_broker_account_control','terminal_broker_account_receipt']:
                if 'unavailable=1' in url.query:return self.send({'schema_version':SCHEMA,'service_available':False,'reason':'HOST_BINDING_UNAVAILABLE','config_id':p['config_id'],'permissions':PERMISSIONS,'read_only':True})
                return self.send(account_read(p))
            raise ValueError('fixture_resource_unexpected:'+name)
        except Exception as exc:return self.send({'error':str(exc)},400)
    def do_POST(self):
        global drop_next
        p=json.loads(self.rfile.read(int(self.headers.get('Content-Length','0'))));url=urlparse(self.path)
        if url.path=='/qa/drop-next-stop':drop_next=True;return self.send({'fixture':True})
        try:
            name=url.path.removeprefix('/api/quant/');events.append({'method':'POST','resource':name,'payload':p})
            if name=='actions/terminal_broker_save_candidate':
                config_id=digest({k:v for k,v in p.items() if k!='request_id'});configs[config_id]=p
                return self.send({'status':'SAVED_OFFLINE_CANDIDATE','mode':p['mode'],'config_id':config_id,'permissions':candidate_permissions})
            if name in ['broker-account/stop','actions/terminal_broker_account_resume']:
                body={k:v for k,v in p.items() if k not in ['mode','config_id']};service=control(p)
                result={**(service.stop(body) if name=='broker-account/stop' else service.resume(body)),'config_id':p['config_id']}
                if name=='broker-account/stop' and drop_next:drop_next=False;return self.send(None)
                return self.send(result)
            raise ValueError('fixture_write_unexpected:'+name)
        except Exception as exc:return self.send({'error':str(exc)},400)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
print(json.dumps({'url':'http://127.0.0.1:'+str(server.server_address[1]),'fixture':True,'account_control':'real SYNTHETIC_TEST temporary root'}),flush=True)
server.serve_forever()
