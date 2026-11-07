/* A saved-record guide. Refresh only reads; every import needs an explicit click. */
(function(root){
  "use strict";
  const ACTION="terminal_prepare_teaching_input",SCHEMA="terminal-teaching-input-v1",REF="terminal-first-use-reference-v1";
  const params={fast_window:2,slow_window:4,position_pct:.25,stop_loss_pct:.03,take_profit_pct:.06};
  const copy=v=>JSON.parse(JSON.stringify(v)),plain=v=>Boolean(v&&typeof v==="object"&&!Array.isArray(v));
  const validId=v=>typeof v==="string"&&v.length>0&&v.length<=160&&!/[\x00-\x1f]/.test(v);
  const jobId=v=>typeof v==="string"&&/^[A-Za-z0-9_-]{8,80}$/.test(v);
  const fail=(v,message)=>{if(!v)throw Error(message);};
  const message=e=>String(e?.info?.message||e?.message||e||"操作尚未确认");
  function validTeaching(v){return plain(v)&&v.schema_version===SCHEMA&&v.status==="READY"&&/^[a-f0-9]{24}$/.test(v.input_id||"")
    &&/^[a-f0-9]{64}$/.test(v.snapshot_id||"")&&v.evidence_kind==="SYNTHETIC_TEST"&&v.currency==="USD"&&v.sessions===22
    &&v.strategy_key==="price.dual_ma@1"&&plain(v.params)&&Object.keys(v.params).length===Object.keys(params).length&&Object.keys(params).every(k=>v.params[k]===params[k])
    &&v.input?.id===v.input_id&&v.input?.input_id===v.snapshot_id&&v.input?.evidence_kind==="SYNTHETIC_TEST"&&v.input?.security?.currency==="USD"
    &&v.new_tasks===0&&v.new_economic_runs===0&&v.source_truth_verified===false&&v.permissions?.research_only===true
    &&["paper_allowed","live_allowed","order_allowed"].every(k=>v.permissions[k]===false);}
  function records(value){
    const result=[];
    for(const [key,kind] of [["coreRuns","core-run"],["runs","terminal-run"],["coreTasks","core-task"],["tasks","terminal-task"]]){
      for(const row of Array.isArray(value?.[key])?value[key]:[]){
        const id=row.id||row.task_id||row.run_id;if(!validId(id))continue;
        const dataKind=row.data_kind||row.input_summary?.evidence_kind||row.inputs?.snapshot?.evidence_kind;
        const time=Date.parse(row.updated_at||row.started_at||row.created_at||"");
        result.push({key:kind+":"+id,kind,id,label:String(row.title||row.task_display_name||row.name||row.label||row.strategy_name||"已保存策略"),
          version:row.task_version_label||row.version_label||(row.version!==undefined?"版本 "+row.version:"已保存版本"),
          stage:kind.endsWith("run")?"历史结果":"策略与本金",status:row.status||row.state||"未记录",
          dataLabel:dataKind==="SYNTHETIC_TEST"?"虚构教学资料":dataKind==="IMPORTED_UNVERIFIED"?"导入资料，来源待核对":"资料性质以原记录为准",time:Number.isFinite(time)?time:null});
      }
    }
    return result.sort((a,b)=>(b.time??-Infinity)-(a.time??-Infinity));
  }
  function createController({getState,api,onTeaching,onChooseTeaching,onOwnData,onContinue,onAdvanced,onOperations,storage,changed=()=>{}}){
    const state={workspace:null,reference:null,prepared:null,pending:false,pendingChoices:[],busy:false,recovering:false,recoveryAttempted:false,error:"",notice:"",selection:null,storageReady:false};
    const emit=()=>{try{changed(state);}catch(_){state.error="页面更新未完成；已保留原操作编号与保存事实。";}},scope=()=>{const s=getState?.()?.coreOverview?.workspace;return typeof s==="string"&&s.length>0&&s.length<=4096&&!s.includes("\0")?s:null;};
    const key=workspace=>"hakimi-first-use-v1:"+encodeURIComponent(workspace);
    const readReference=workspace=>{const text=storage?.getItem(key(workspace));if(!text)return null;fail(text.length<=4096,"首用记录过长，请查看原操作记录。");const v=JSON.parse(text);
      fail(plain(v)&&v.schema_version===REF&&v.workspace===workspace&&["PENDING","PREPARED","CONTINUATION"].includes(v.phase)
        &&(v.job_id===null||jobId(v.job_id))&&(v.phase==="CONTINUATION"||jobId(v.job_id)),"首用记录与当前工作区不一致，请查看原操作记录。");return v;};
    function persist(reference){fail(storage&&typeof storage.setItem==="function","无法保留原操作编号，本次尚未提交。");
      storage.setItem(key(state.workspace),JSON.stringify(reference));state.reference=copy(reference);}
    function sync(){const workspace=scope();if(workspace===state.workspace)return;
      Object.assign(state,{workspace,reference:null,prepared:null,pending:false,pendingChoices:[],busy:false,recovering:false,recoveryAttempted:false,error:"",notice:"",selection:null,storageReady:false});
      if(!workspace)return;
      try{fail(storage&&typeof storage.getItem==="function","无法读取本机首用记录；准备示例前需要能够保留原操作编号。");state.reference=readReference(workspace);state.storageReady=true;
        state.pending=Boolean(state.reference?.job_id);if(state.reference?.continuation)state.selection=state.reference.continuation.kind+":"+state.reference.continuation.id;
      }catch(e){state.pending=true;state.error=message(e);}
    }
    function acceptTeaching(value,{restoring=false}={}){fail(validTeaching(value),"教学资料回执的身份或限制不完整，请查询原操作记录。");
      fail(state.workspace===scope()&&jobId(state.reference?.job_id),"工作区已变化，原操作保留在原工作区。");
      const continuation=restoring?state.reference.continuation:null;
      state.prepared=copy(value);state.pending=false;state.pendingChoices=[];state.error="";
      state.notice=continuation?"已保留原任务或结果，可继续查看；读取不会重复运行。":"22个交易日的虚构资料已准备好。下一步选择策略与本金；尚未创建任务或运行研究。";
      try{persist({...state.reference,phase:continuation?"CONTINUATION":"PREPARED",input_id:value.input_id,snapshot_id:value.snapshot_id,continuation});}
      catch(e){state.notice+=" 本机提示保存未完成，原操作编号仍可查询。";}
      emit();return value;
    }
    async function recover(){sync();if(!state.reference?.job_id||state.recovering)return;const workspace=state.workspace,id=state.reference.job_id;
      state.recoveryAttempted=true;state.recovering=true;emit();
      try{fail(typeof api==="function","原操作读取入口尚未连接。");const job=await api("jobs/"+encodeURIComponent(id));
        if(scope()!==workspace||state.reference?.job_id!==id)return;
        fail(job?.job_id===id&&job.action===ACTION,"原操作身份不匹配，请从操作记录核对。");
        if(job.status!=="succeeded"){state.pending=true;state.notice="原准备操作仍待核对；只读取这个编号，不重复提交。";return;}
        fail(validTeaching(job.result),"原操作没有完整的教学资料回执。");
        const input=await api("inputs/"+encodeURIComponent(job.result.input_id));
        if(scope()!==workspace||state.reference?.job_id!==id)return;
        fail(input?.id===job.result.input_id&&input?.input_id===job.result.snapshot_id&&input?.evidence_kind==="SYNTHETIC_TEST"&&input?.status==="READY","已保存资料当前未通过读取核对；保留原编号，不重新准备。");
        acceptTeaching(job.result,{restoring:true});
      }catch(e){if(scope()===workspace){state.pending=true;state.error=message(e);}}
      finally{if(scope()===workspace){state.recovering=false;emit();}}
    }
    function refresh(){sync();emit();if(state.reference?.job_id&&!state.recoveryAttempted&&!state.busy)recover();}
    function selectPending(id){const found=state.pendingChoices.find(row=>row.job_id===id);fail(found,"请先选择这次读到的原操作编号。");
      persist({schema_version:REF,workspace:state.workspace,job_id:id,phase:"PENDING",input_id:null,snapshot_id:null,continuation:null});state.recoveryAttempted=true;emit();}
    async function prepare(){sync();fail(state.workspace&&state.storageReady,"尚未读到可保留原操作的当前工作区。");fail(!state.pending&&!state.busy,"请先查询原准备操作，不重复提交。");
      fail(getState?.()?.coreOverview?.session?.read_only!==true,"当前是只读模式，尚未准备新资料。");
      fail(typeof onTeaching==="function","教学准备入口尚未连接。");const workspace=state.workspace;let submitted=false,request=null;state.busy=true;state.error="";emit();
      const onRequest=id=>{fail(scope()===workspace&&jobId(id),"工作区或操作编号无效，本次尚未提交。");
        const previous=readReference(workspace);fail(previous?.phase!=="PENDING","此工作区已有待核对的准备操作，请先读取原记录。");
        persist({schema_version:REF,workspace,job_id:id,phase:"PENDING",input_id:null,snapshot_id:null,continuation:null});
        submitted=true;request=id;state.pending=true;state.prepared=null;state.recoveryAttempted=true;emit();};
      const committed=value=>{if(scope()===workspace&&state.reference?.job_id===request)return acceptTeaching(value);};
      try{fail(typeof api==="function","原操作列表读取入口尚未连接，本次尚未提交。");const jobs=await api("jobs");
        if(scope()!==workspace)return;fail(Array.isArray(jobs?.items),"原操作列表未完整读到，本次尚未提交。");
        const unresolved=jobs.items.filter(row=>row?.action===ACTION&&["queued","running","unknown"].includes(row.status));
        fail(unresolved.every(row=>jobId(row.job_id)),"原准备记录的编号无效，请查看操作记录。");
        if(unresolved.length){state.pending=true;state.pendingChoices=unresolved.map(row=>({job_id:row.job_id,status:row.status,created_at:row.created_at||"时间未记录"}));
          state.notice=unresolved.length===1?"发现上次准备仍待核对，请先读取原准备结果。":"有多份准备记录待核对，请按原操作编号选择；不会另建准备请求。";
          if(unresolved.length===1)selectPending(unresolved[0].job_id);emit();return;}
        const result=await onTeaching({onRequest,onCommitted:committed});if(scope()!==workspace||state.reference?.job_id!==request)return;
        if(result&&!state.prepared)acceptTeaching(result);
        if(!state.prepared){state.pending=submitted;state.error=submitted?"准备结果尚未确认，请读取原操作记录，不重复提交。":"本次尚未提交，请先核对提示。";}
      }catch(e){if(scope()===workspace){state.pending=(submitted&&!state.prepared)||state.pendingChoices.length>0;state.error=state.prepared?"资料已保存，但后续显示未完成；可以继续选择策略与本金。":message(e);}}
      finally{if(scope()===workspace){state.busy=false;emit();}}
      return state.prepared;
    }
    async function chooseTeaching(){sync();fail(state.prepared&&!state.pending&&!state.busy,"请先核对原准备结果。");fail(typeof onChooseTeaching==="function","策略与本金入口尚未连接。");
      const workspace=state.workspace,selection=state.selection,job=state.reference?.job_id;
      const current=()=>scope()===workspace&&state.workspace===workspace&&state.selection===selection&&state.reference?.job_id===job;
      state.error="";try{await onChooseTeaching(copy(state.prepared));if(current())state.notice="正在选择策略与本金；关闭设置后可回到这里继续，资料不会重新准备。";}
      catch(e){if(current())state.error="教学资料已保存，设置暂未打开："+message(e);}if(current())emit();}
    function selected(){const items=records(getState?.());return items.find(r=>r.key===state.selection)||items[0]||null;}
    function select(value){const item=records(getState?.()).find(r=>r.key===value);if(item){state.selection=item.key;emit();}}
    function markContinuation(value){sync();const item=records(getState?.()).find(r=>r.kind===value?.kind&&r.id===value?.id);if(!item)return;
      state.selection=item.key;if(!state.pending)state.notice="已选中保存的原任务或结果，可继续查看；读取不会重复运行。";
      if(!state.pending&&state.storageReady){try{persist({schema_version:REF,workspace:state.workspace,phase:"CONTINUATION",job_id:state.reference?.job_id||null,
        input_id:state.reference?.input_id||null,snapshot_id:state.reference?.snapshot_id||null,continuation:{kind:item.kind,id:item.id}});}catch(e){state.error=message(e);}}emit();}
    async function continueSaved(){const item=selected();fail(item&&typeof onContinue==="function","尚未读到可继续的原记录。");await onContinue(copy(item));markContinuation(item);}
    function model(){const current=getState?.()||{},items=records(current),item=selected();
      const prepared=state.prepared&&!state.reference?.continuation&&!state.pending;
      const action=prepared?"choose":item?"continue":state.pending?"recover":"prepare";
      return {items,item,action,stage:prepared?2:item?.kind.endsWith("run")?3:item?2:1,
        title:prepared?"资料已准备，选择策略与本金":item?"继续上次策略":"先用示例体验一次",
        primary:{prepare:"用示例体验一次",choose:"选择策略与本金",continue:"继续上次策略",recover:"读取原准备结果"}[action],
        detail:prepared?"虚构教学资料 · 22个交易日 · 双均线2/4教学设置":item?`${item.label} · ${item.version} · ${item.stage} · ${item.dataLabel}`:"只使用程序内的虚构资料。先看懂一次历史结果，再决定使用哪些自己的资料。",
        disabled:state.busy||state.recovering||current.loaded===false||!state.workspace||(action==="recover"&&!state.reference?.job_id)||(action==="prepare"&&(!state.storageReady||current.coreOverview?.session?.read_only===true)),
        teachingDisabled:state.pending||state.busy||state.recovering||!state.storageReady||current.loaded===false||current.coreOverview?.session?.read_only===true};}
    return {state,refresh,recover,prepare,acceptTeaching,chooseTeaching,select,selectPending,markContinuation,model,
      primary:()=>({prepare,choose:chooseTeaching,continue:continueSaved,recover}[model().action])(),
      ownData:async()=>{if(typeof onOwnData==="function")await onOwnData();},
      advanced:async()=>{if(typeof onAdvanced==="function")await onAdvanced();},
      operations:async()=>{if(typeof onOperations==="function")await onOperations();}};
  }
  function installTerminalFirstUseUI(options){
    const host=options.host,document=host.ownerDocument;const section=document.createElement("section");section.className="panel section-gap";section.setAttribute("aria-label","开始或继续策略");
    section.innerHTML='<div class="panel-body"><h2 data-first-use="title" tabindex="-1"></h2><p data-first-use="detail" style="margin:8px 0 16px;overflow-wrap:anywhere"></p><ol class="tq-first-steps" aria-label="三步研究流程"><li data-step="1"><span aria-hidden="true">1</span>选择资料</li><li data-step="2"><span aria-hidden="true">2</span>选择策略与本金</li><li data-step="3"><span aria-hidden="true">3</span>看历史结果</li></ol><div data-first-use="record-field" class="field" hidden><label>选择已有策略记录<select data-first-use="record"></select></label></div><div class="actions section-gap"><button type="button" class="btn primary" data-first-action="primary" style="min-height:44px"></button><button type="button" class="btn outline" data-first-action="own" style="min-height:44px">使用自己的资料</button><button type="button" class="btn ghost" data-first-action="teaching" style="min-height:44px" hidden>用示例体验一次</button></div><p data-first-use="notice" role="status" aria-live="polite" style="margin:12px 0" hidden></p><p data-first-use="error" role="alert" hidden></p><div data-first-use="pending" hidden><p>原准备操作需要核对，不会自动再次提交。</p><button type="button" class="btn" data-first-action="operations" style="min-height:44px">查看原操作记录</button><button type="button" class="btn" data-first-action="recover" style="min-height:44px">重新读取原准备结果</button></div><details class="section-gap"><summary style="min-height:44px;padding:10px 0">更多资料与设置</summary><p>专业导入、已有本地缓存、旧报告和身份信息均保留。展开或返回不会清空已填写内容。</p><button type="button" class="btn" data-first-action="advanced" style="min-height:44px">打开专业资料工具</button></details></div>';
    const pendingChoice=document.createElement("label");pendingChoice.textContent="选择待核对的原准备记录";pendingChoice.hidden=true;pendingChoice.className="field";
    const pendingSelect=document.createElement("select");pendingSelect.setAttribute("aria-label","选择待核对的原准备记录");pendingChoice.append(pendingSelect);section.querySelector('[data-first-use="pending"]').prepend(pendingChoice);
    const style=document.createElement("style");style.textContent='.tq-first-steps{display:flex;gap:12px;flex-wrap:wrap;list-style:none;padding:0;margin:16px 0 20px}.tq-first-steps li{display:flex;align-items:center;gap:8px;padding:8px 12px;border:1px solid var(--line);border-radius:8px;color:var(--muted)}.tq-first-steps li span{display:inline-grid;place-items:center;min-width:24px;min-height:24px;border-radius:50%;background:var(--surface)}.tq-first-steps li[aria-current="step"]{color:var(--text);border-color:var(--accent,#176bc1);font-weight:600}@media(max-width:600px){.tq-first-steps{display:grid;gap:8px}.tq-first-steps li{padding:6px 10px}}';host.append(style);
    host.append(section);const find=name=>section.querySelector('[data-first-use="'+name+'"]'),button=name=>section.querySelector('[data-first-action="'+name+'"]');
    let storage=options.storage;try{if(storage===undefined)storage=root.localStorage;}catch(_){storage=null;}
    const controller=createController({...options,storage,changed:render});let optionSignature="",pendingSignature="";
    function render(){const model=controller.model(),s=controller.state;find("title").textContent=model.title;find("detail").textContent=model.detail;
      button("primary").textContent=s.busy?"正在准备资料…":s.recovering?"正在读取原记录…":model.primary;button("primary").disabled=model.disabled;
      button("teaching").hidden=model.action==="prepare"||model.action==="choose";button("teaching").disabled=model.teachingDisabled;
      button("recover").disabled=s.recovering||!s.reference?.job_id;find("pending").hidden=!s.pending;
      pendingChoice.hidden=s.pendingChoices.length<2;const pending=JSON.stringify(s.pendingChoices);
      if(pending!==pendingSignature){const placeholder=document.createElement("option");placeholder.value="";placeholder.textContent="请选择原操作编号";pendingSelect.replaceChildren(placeholder,...s.pendingChoices.map(row=>{const option=document.createElement("option");option.value=row.job_id;option.textContent=`${row.created_at} · ${row.job_id}`;return option;}));pendingSignature=pending;}
      pendingSelect.value=s.reference?.job_id||"";
      find("notice").textContent=s.notice;find("notice").hidden=!s.notice;find("error").textContent=s.error;find("error").hidden=!s.error;
      for(const item of section.querySelectorAll('[data-step]')){if(Number(item.dataset.step)===model.stage)item.setAttribute("aria-current","step");else item.removeAttribute("aria-current");}
      find("record-field").hidden=model.items.length<2;const signature=JSON.stringify(model.items.map(i=>[i.key,i.label,i.version,i.stage]));
      if(signature!==optionSignature){find("record").replaceChildren(...model.items.map(item=>{const option=document.createElement("option");option.value=item.key;option.textContent=`${item.label} · ${item.version} · ${item.stage}`;return option;}));optionSignature=signature;}
      if(model.item)find("record").value=model.item.key;
    }
    section.addEventListener("click",async event=>{const target=event.target.closest("[data-first-action]");if(!target||!section.contains(target)||target.disabled)return;
      const action={primary:"primary",own:"ownData",teaching:"prepare",recover:"recover",operations:"operations",advanced:"advanced"}[target.dataset.firstAction];
      try{await controller[action]();}catch(e){controller.state.error=message(e);render();}});
    find("record").addEventListener("change",()=>controller.select(find("record").value));
    pendingSelect.addEventListener("change",()=>{try{controller.selectPending(pendingSelect.value);}catch(e){controller.state.error=message(e);render();}});
    controller.refresh();return {...controller,element:section};
  }
  const api={ACTION,validTeaching,records,createController,installTerminalFirstUseUI};
  if(typeof module!=="undefined"&&module.exports)module.exports=api;
  root.installTerminalFirstUseUI=installTerminalFirstUseUI;
})(typeof globalThis!=="undefined"?globalThis:this);
