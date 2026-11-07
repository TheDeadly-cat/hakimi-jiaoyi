/* Workspace navigation only. No research, simulation, account or order writes. */
(function(root){
  'use strict';
  const SCHEMA='hakimi-terminal-journey-v1',views=['results','continuous','execution','broker'];
  const copy=v=>JSON.parse(JSON.stringify(v)),plain=v=>!!v&&typeof v==='object'&&!Array.isArray(v);
  const hash=v=>typeof v==='string'&&/^[a-f0-9]{64}$/.test(v),opaque=v=>typeof v==='string'&&/^[A-Za-z0-9][A-Za-z0-9_-]{0,199}$/.test(v);
  const exact=(v,keys)=>plain(v)&&Object.keys(v).length===keys.length&&keys.every(k=>Object.hasOwn(v,k));
  const ordered=v=>Array.isArray(v)?v.map(ordered):plain(v)?Object.fromEntries(Object.keys(v).sort().map(k=>[k,ordered(v[k])])):v;
  const same=(a,b)=>JSON.stringify(ordered(a))===JSON.stringify(ordered(b));
  const empty=()=>({task:null,research:null,view:'results',replay:null,manual:null,broker:null});
  function validSelection(s){
    if(!exact(s,['task','research','view','replay','manual','broker'])||!views.includes(s.view))return false;
    const fields={task:['kind','id','task_id'],research:['kind','id'],replay:['account_id'],manual:['account_id','plan_id'],broker:['mode','config_id','intent_id','plan_id']};
    for(const [name,keys] of Object.entries(fields)){const v=s[name];if(v===null)continue;if(!exact(v,keys))return false;
      if(keys.some(k=>!['kind','mode'].includes(k)&&!(v[k]===null&&['plan_id','intent_id'].includes(k))&&!opaque(v[k])))return false;
      if(name==='task'&&!['terminal_task','core_task'].includes(v.kind)||name==='research'&&!['terminal_run','core_run'].includes(v.kind))return false;
      if(name==='broker'&&(!['OFFICIAL_SIMULATION','LIVE_CANDIDATE'].includes(v.mode)||v.plan_id!==null&&v.intent_id===null))return false;}
    return JSON.stringify(s).length<=4096;
  }
  function createController({api,saveSelection,execution,continuous,broker,plan,onRestore=()=>{},uuid=()=>root.crypto.randomUUID(),changed=()=>{}}){
    const state={snapshot:null,selection:null,loading:false,saving:false,restoring:false,pending:null,error:'',diagnostics:[]};let epoch=0;
    const emit=()=>{try{changed(state);}catch(_){}};
    function envelope(v){if(v?.schema_version!==SCHEMA||!hash(v.workspace_context)||!Number.isSafeInteger(v.revision)||v.revision<0||v.selection!==null&&!validSelection(v.selection)||v.new_economic_runs!==0||v.external_calls!==0||v.permissions?.order_allowed!==false||v.permissions?.paper_allowed!==false||v.permissions?.live_allowed!==false||state.snapshot&&state.snapshot.workspace_context!==v.workspace_context)throw Error('继续位置的工作区或记录身份未通过核对。');return v;}
    async function load({restore=true}={}){if(state.saving)throw Error('正在保存本次选择，请等待原回执。');const sequence=++epoch;state.loading=true;emit();try{const value=envelope(await api('terminal_journey'));if(sequence!==epoch)return;
      if(value.read_only!==true||!['EMPTY','SAVED'].includes(value.status))throw Error('继续位置读取未完成。');state.snapshot=copy(value);state.selection=copy(value.selection);state.error='';emit();if(restore)await restoreCurrent(sequence);return value;
    }catch(e){if(sequence===epoch){state.error='继续位置未核对：'+String(e.message||e);emit();}}finally{if(sequence===epoch){state.loading=false;emit();}}}
    async function select(patch){if(state.saving||state.pending)throw Error('继续位置的原保存请求尚待核对，请先重新读取。');if(!state.snapshot)await load({restore:false});if(!state.snapshot)throw Error('尚未取得工作区身份，无法记住这次选择。');
      let value={...(state.selection||empty()),...copy(patch)};
      if(Object.hasOwn(patch,'research')&&!same(patch.research,state.selection?.research??null))value={...empty(),...copy(patch)};
      if(!validSelection(value))throw Error('继续位置只能保存原记录编号。');
      if(value.view==='continuous'&&value.research?.kind!=='terminal_run')throw Error('这份研究使用本地合成订单练习；逐日模拟仅支持对应原策略。');
      if(same(value,state.selection))return state.snapshot;
      if(typeof saveSelection!=='function')throw Error('继续位置保存入口未配置。');
      const sequence=++epoch,payload={request_id:'journey-'+uuid(),workspace_context:state.snapshot.workspace_context,expected_revision:state.snapshot.revision,selection:copy(value)};state.loading=false;state.restoring=false;state.pending=copy(payload);state.saving=true;state.error='';emit();
      try{const reply=envelope(await saveSelection(copy(payload)));if(sequence!==epoch)return;
        if(reply.request_id!==payload.request_id||!['SAVED','UNCHANGED','REVISION_CONFLICT'].includes(reply.status))throw Error('未取得原选择的保存回执。');
        if(reply.status==='REVISION_CONFLICT'){state.pending=null;state.snapshot=copy(reply);state.selection=copy(reply.selection);throw Error('另一窗口已更新继续位置，请重新读取后明确选择。');}
        if(reply.saved!==true||!same(reply.selection,payload.selection))throw Error('保存回执与这次选择不一致。');state.snapshot=copy(reply);state.selection=copy(reply.selection);state.pending=null;emit();return reply;
      }catch(e){if(sequence===epoch){state.error='继续位置保存未确认：'+String(e.message||e)+'；已有业务记录保留。';emit();}throw e;}
      finally{if(sequence===epoch){state.saving=false;emit();}}
    }
    async function reconcileSelection(){const pending=state.pending;const result=await load({restore:false});if(result&&pending&&same(result.selection,pending.selection)&&result.revision>=pending.expected_revision+1){state.pending=null;state.error='已读取同一继续位置；没有重复保存。';emit();}return result;}
    async function restoreCurrent(sequence=++epoch){const s=state.selection&&copy(state.selection);if(!s)return;state.loading=false;state.restoring=true;state.diagnostics=[];emit();
      const run=async(name,fn)=>{if(sequence!==epoch)return;try{await fn();}catch(e){if(sequence===epoch)state.diagnostics.push({stage:name,message:String(e.message||e),reference:copy(s[name]||s.research)});}};
      try{
        if(execution&&(s.manual||s.view==='execution'))await run('manual',()=>execution.restoreSelection(s));
        if(continuous&&(s.replay||s.view==='continuous'))await run('replay',()=>continuous.restoreSelection(s));
        if(broker&&(s.broker||s.view==='broker'))await run('broker',()=>broker.restoreSelection(s));
        if(plan&&s.broker?.plan_id)await run('broker',()=>plan.restoreSelection(s,broker?.state.research?.binding));
        if(sequence===epoch)await onRestore(s.view,copy(state.snapshot));
      }finally{if(sequence===epoch){state.restoring=false;emit();}}
    }
    async function continueAt(view){if(!views.includes(view))throw Error('请选择已有页面。');await select({view});return restoreCurrent();}
    return {state,load,select,restore:()=>restoreCurrent(),continueAt,reconcileSelection};
  }
  function installTerminalJourneyUI({host,...options}){const view=host.ownerDocument.createElement('section');view.className='panel terminal-journey';host.appendChild(view);
    view.innerHTML='<style>.terminal-journey{min-width:0}.terminal-journey p{line-height:1.65}.terminal-journey button,.terminal-journey summary{min-height:44px}.terminal-journey button{margin:4px 8px 4px 0;white-space:normal}.terminal-journey summary{cursor:pointer;align-content:center}.terminal-journey pre{white-space:pre-wrap;overflow-wrap:anywhere}</style><div style="padding:16px;overflow-wrap:anywhere"><strong>继续这次策略</strong><p data-journey-status role="status"></p><div data-journey-steps></div><button type="button" class="btn" data-journey-continue>继续查看原记录</button><button type="button" class="btn" data-journey-read>重新核对位置</button><details><summary>核对原记录编号</summary><pre data-journey-identities></pre></details></div>';
    const labels={task:'已保存任务',research:'已完成历史研究',replay:'逐日模拟（每次明确推进）',manual:'本地合成订单练习',broker:'未发送意图与离线计划（券商未连接）'};
    const controller=createController({...options,changed:s=>{view.querySelector('[data-journey-status]').textContent=s.error||s.diagnostics.map(v=>v.message).join('；')||(s.selection?'已保留同一组原记录；查看不会推进模拟或发送订单。':'选择策略后，会记住这次查看的位置。');
      const items=view.querySelector('[data-journey-steps]');items.replaceChildren();for(const [key,label] of Object.entries(labels)){if(!s.selection?.[key])continue;const p=host.ownerDocument.createElement('p'),verified=s.snapshot?.resolution?.[key];let stage=label;
        if(key==='broker')stage=(s.selection.broker.plan_id?'离线计划已保存':s.selection.broker.intent_id?'未发送意图已记录':'候选资料已保存')+'（券商未连接）';
        const display=verified?.data?.display||verified?.data?.display_summary,version=verified?.data?.binding?.task_version;
        p.textContent=stage+(display?.symbol?' · '+display.symbol:'')+(version!==undefined?' · 原版本 '+version:'')+(verified?.status!=='VERIFIED'?' · 未核对，原编号保留':'');items.appendChild(p);}
      view.querySelector('[data-journey-identities]').textContent=s.selection?JSON.stringify(s.selection,null,2):'尚未选择';
      view.querySelector('[data-journey-continue]').disabled=!s.selection||s.loading||s.saving||s.restoring||!!s.pending;options.changed?.(s);}});
    view.querySelector('[data-journey-read]').addEventListener('click',()=>controller.reconcileSelection().catch(()=>{}));view.querySelector('[data-journey-continue]').addEventListener('click',()=>controller.continueAt(controller.state.selection.view).catch(()=>{}));
    return {controller,element:view};
  }
  const exports={SCHEMA,validSelection,createController,installTerminalJourneyUI};if(typeof module!=='undefined'&&module.exports)module.exports=exports;root.HakimiTerminalJourneyUI=exports;root.installTerminalJourneyUI=installTerminalJourneyUI;
})(typeof globalThis!=='undefined'?globalThis:this);
