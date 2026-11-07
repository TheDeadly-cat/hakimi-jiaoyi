/* Local review of retained source originals. Never requests a provider or runs research. */
(function(root){
  "use strict";
  const SCHEMA="terminal-stock-supplement-view-v2",FORMAT="futu-retained-sdk-v1",PREFIX="terminal_daily_",REASON="SOURCE_CORPORATE_ACTION_COVERAGE_UNKNOWN";
  const keys=["security_request","security_response","actions_request","actions_response"];
  const titles={security_request:"证券资料查询请求原件",security_response:"证券资料查询响应原件",actions_request:"公司行为查询请求原件",actions_response:"公司行为查询响应原件"};
  const plain=v=>Boolean(v&&typeof v==="object"&&!Array.isArray(v)),copy=v=>JSON.parse(JSON.stringify(v));
  const hash=v=>typeof v==="string"&&/^[a-f0-9]{64}$/.test(v),inputId=v=>typeof v==="string"&&/^canon-[a-f0-9]{32}$/.test(v),supplementId=v=>typeof v==="string"&&/^supplement-[a-f0-9]{64}$/.test(v);
  const ordered=v=>v&&typeof v==="object"?(Array.isArray(v)?v.map(ordered):Object.fromEntries(Object.keys(v).sort().map(k=>[k,ordered(v[k])]))):v;
  const canonical=v=>JSON.stringify(ordered(v)).replace(/[\u007f-\uffff]/g,c=>"\\u"+c.charCodeAt(0).toString(16).padStart(4,"0"));
  const equal=(a,b)=>canonical(a)===canonical(b),esc=v=>String(v??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const require=(v,message)=>{if(!v)throw Error(message);},errorText=e=>String(e?.info?.message||e?.message||e||"读取未完成");
  const permissions=v=>plain(v)&&v.research_only===true&&["order_allowed","live_allowed","paper_allowed"].every(k=>v[k]===false);
  const eligible=v=>inputId(v?.id)&&hash(v?.check_hash)&&v.status==="BLOCKED"&&v.reason===REASON&&v.can_save===false&&plain(v.security)
    &&["security_id","symbol","exchange","currency","instrument_type"].every(key=>typeof v.security[key]==="string"&&v.security[key].length>0)
    &&typeof v.coverage_start==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v.coverage_start)&&typeof v.coverage_end==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(v.coverage_end)&&v.coverage_start<=v.coverage_end;
  const same=(a,b)=>Boolean(a&&b&&a.id===b.id&&a.check_hash===b.check_hash);
  async function digest(v){return Array.from(new Uint8Array(await root.crypto.subtle.digest("SHA-256",new TextEncoder().encode(canonical(v)))),n=>n.toString(16).padStart(2,"0")).join("");}
  function envelope(value,context){
    require(plain(value)&&value.schema_version===SCHEMA&&value.original_intake_id===context.id&&value.original_check_hash===context.check_hash
      &&permissions(value.permissions)&&value.source_truth_verified===false,"补证身份或研究权限与原检查不一致。");
    require(plain(value.security)&&equal(value.security,context.security)&&plain(value.window)&&value.window.start===context.coverage_start&&value.window.end===context.coverage_end,"补证的证券或固定日期区间不一致。");
    return value;
  }
  function checkedView(value,context){envelope(value,context);
    require(supplementId(value.id)&&hash(value.check_hash)&&["BLOCKED","REVIEW_REQUIRED","UNKNOWN"].includes(value.status)&&typeof value.can_save==="boolean"
      &&(!value.can_save||value.status==="REVIEW_REQUIRED")&&(value.saved_input_id===null||inputId(value.saved_input_id)),"补证记录的保存状态不完整。");
    if(value.saved_input_id){const input=value.saved_input;
      require(input?.id===value.saved_input_id&&input.record_namespace==="canonical-daily-v1"&&input.record_resource===PREFIX+"inputs"&&input.kind==="PRICE_SNAPSHOT"&&input.status==="READY"
        &&equal(input.security,value.security)&&input.coverage_start===value.window.start&&input.coverage_end===value.window.end&&permissions(input.permissions),"已保存输入与补证的证券、区间或权限不一致。");}
    return value;
  }
  function createController({api,perform,onInputSaved,uuid=()=>root.crypto.randomUUID(),changed=()=>{}}){
    const state={context:null,requirements:null,files:{},readingFiles:{},items:[],selected:null,confirmed:false,confirmationHash:null,busy:false,loading:false,listLoading:false,pending:null,querying:false,fact:null,error:"",readError:""};
    let contextSequence=0,listSequence=0,detailSequence=0;
    const delivered=new Set(),emit=()=>{try{changed(state);}catch(_){state.readError="页面展示未完成；原请求和已保存事实仍保留。";}};
    const unconfirm=()=>{state.confirmed=false;state.confirmationHash=null;};
    const current=()=>{require(eligible(state.context),"请先选择公司行为覆盖未知的原检查记录。");return copy(state.context);};
    const idle=()=>require(!state.busy&&!state.pending,"请先查询原请求回执，不重复提交。");
    function setContext(value){const next=eligible(value)?copy(value):null;if(same(next,state.context)||!next&&!state.context)return;
      contextSequence++;listSequence++;detailSequence++;state.context=next;state.requirements=null;state.files={};state.readingFiles={};state.items=[];state.selected=null;state.loading=false;state.listLoading=false;state.error="";state.readError="";unconfirm();emit();}
    async function readContext(){const context=current(),sequence=++contextSequence;state.loading=true;state.requirements=null;unconfirm();state.readError="";emit();
      try{const value=await api(PREFIX+"supplement_context/"+context.id);envelope(value,context);
        require(value.read_only===true&&Array.isArray(value.supported_formats)&&plain(value.limits)&&Number.isSafeInteger(value.limits.file_bytes)&&value.limits.file_bytes>0&&value.limits.file_bytes<=1048576&&Number.isSafeInteger(value.limits.total_bytes)&&value.limits.total_bytes>0&&value.limits.total_bytes<=4194304,"补证原件要求或大小限制不完整。");
        require(value.supported_formats.every(f=>f.id===FORMAT&&Array.isArray(f.required_artifacts)&&equal(f.required_artifacts.map(r=>r.key).sort(),[...keys].sort()))&&value.supported_formats.length<=1,"当前来源格式尚未获支持。");
        if(sequence!==contextSequence||!same(context,state.context))return;state.requirements=copy(value);emit();return value;
      }catch(error){if(sequence===contextSequence)state.readError="补证要求读取未完成："+errorText(error);}
      finally{if(sequence===contextSequence){state.loading=false;emit();}}
    }
    async function readList(){const context=current(),sequence=++listSequence;state.listLoading=true;state.readError="";emit();
      try{const value=await api(PREFIX+"supplements");require(Array.isArray(value?.items),"补证记录列表不完整。");const items=value.items.filter(row=>row.original_intake_id===context.id);
        for(const row of items)checkedView(row,context);if(sequence!==listSequence||!same(context,state.context))return;state.items=copy(items);return items;
      }catch(error){if(sequence===listSequence)state.readError="已有补证记录读取未完成；当前事实仍保留："+errorText(error);}
      finally{if(sequence===listSequence){state.listLoading=false;emit();}}
    }
    async function openRecord(id){const context=current(),sequence=++detailSequence;require(supplementId(id),"请选择已保存的补证记录。");unconfirm();state.readError="";emit();
      try{const value=await api(PREFIX+"supplements/"+id);checkedView(value,context);require(value.id===id,"返回了另一份补证记录。");if(sequence!==detailSequence||!same(context,state.context))return;
        state.selected=copy(value);emit();return value;
      }catch(error){if(sequence===detailSequence){state.readError="原补证详情读取未完成："+errorText(error);emit();}}
    }
    function clearArtifact(key){idle();require(keys.includes(key),"原件类别不正确。");delete state.files[key];state.selected=null;unconfirm();emit();}
    function setFileLoading(key,value){state.readingFiles[key]=value===true;emit();}
    function setArtifact(key,{name,bytes}){idle();current();require(keys.includes(key)&&state.requirements?.supported_formats.some(f=>f.id===FORMAT),"请先读取当前补证要求。");
      const data=bytes instanceof Uint8Array?bytes:new Uint8Array(bytes),limit=state.requirements.limits;
      require(typeof name==="string"&&name.length>0&&name.length<=240&&/\.json$/i.test(name),"请选择已保存的 JSON 原件。");
      require(data.byteLength>0&&data.byteLength<=limit.file_bytes,"原件不能为空，单份最多 1 MiB。");
      require(data.byteLength+Object.entries(state.files).filter(([k])=>k!==key).reduce((n,[,file])=>n+file.size,0)<=limit.total_bytes,"四份原件合计不能超过 4 MiB。");
      let binary="";for(let offset=0;offset<data.length;offset+=32768)binary+=String.fromCharCode(...data.subarray(offset,offset+32768));
      state.files[key]={name,size:data.byteLength,raw_base64:root.btoa(binary)};state.selected=null;state.error="";unconfirm();emit();}
    function setConfirmation(value){state.confirmed=value===true&&state.selected?.can_save===true&&!state.selected.saved_input_id;state.confirmationHash=state.confirmed?state.selected.check_hash:null;emit();}
    async function deliver(input,explicit=false){if(typeof onInputSaved!=="function"||!explicit&&delivered.has(input.id))return;const alreadyDelivered=delivered.has(input.id);delivered.add(input.id);
      try{await onInputSaved(copy(input));}catch(error){if(!alreadyDelivered)delivered.delete(input.id);state.readError="新输入已保存，页面选择未完成；可从已保存行情重新读取："+errorText(error);emit();}}
    async function accept(value,operation){checkedView(value,operation.context);
      if(operation.action===PREFIX+"save_supplement")require(value.id===operation.payload.supplement_id&&value.check_hash===operation.payload.expected_check_hash&&inputId(value.saved_input_id),"保存回执不属于原补证或没有完整新输入。");
      state.fact={action:operation.action,operation_id:operation.payload.operation_id,context:copy(operation.context),view:copy(value)};
      if(same(operation.context,state.context)){detailSequence++;state.selected=copy(value);state.items=[copy(value),...state.items.filter(row=>row.id!==value.id)];unconfirm();}
      if(value.status==="UNKNOWN"){state.error="原补证结果仍待核对；保留原请求，只查询回执。";emit();return false;}
      if(state.pending===operation)state.pending=null;state.error="";emit();
      if(value.saved_input&&same(operation.context,state.context))await deliver(value.saved_input);
      return true;
    }
    async function execute(action,payload,context){idle();const operation={action,payload:{operation_id:uuid(),...copy(payload)},context,request_hash:null};state.pending=operation;state.busy=true;state.error="";state.readError="";unconfirm();emit();
      let completion=null,acknowledged=false,submitted=false;
      const receive=value=>{if(!completion){completion=accept(value,operation).then(ok=>{acknowledged=ok;return ok;});completion.catch(()=>{});}return completion;};
      try{operation.request_hash=await digest({action,payload:operation.payload});require(same(context,state.context),"资料选择已变化，本次尚未提交。");submitted=true;
        const value=await perform(action,copy(operation.payload),{onSuccess:receive});if(value&&!completion)receive(value);if(completion)await completion;
        if(!acknowledged)state.error="提交结果尚未确认；保留原请求，只查询回执，不重复提交。";
      }catch(error){if(completion){try{await completion;}catch(_){}}
        if(acknowledged)state.readError="保存事实已确认，后续页面读取未完成："+errorText(error);
        else{if(!submitted&&state.pending===operation)state.pending=null;state.error=(submitted?"原请求结果待核对：":"尚未提交：")+errorText(error);}
      }finally{state.busy=false;emit();}
      return acknowledged?state.fact:null;
    }
    async function check(){idle();const context=current();require(state.requirements?.supported_formats.some(f=>f.id===FORMAT)&&!state.loading,"请先读取当前补证要求。");
      require(keys.every(k=>state.files[k])&&!Object.values(state.readingFiles).some(Boolean),"请完整选择四份已保存的查询原件，等待本机读取完成。");
      return execute(PREFIX+"check_supplement",{intake_id:context.id,expected_check_hash:context.check_hash,source_format:FORMAT,artifacts:Object.fromEntries(keys.map(key=>[key,state.files[key].raw_base64]))},context);
    }
    async function save(){idle();const context=current(),value=state.selected;require(value?.can_save===true&&value.status==="REVIEW_REQUIRED"&&!value.saved_input_id&&state.confirmed&&state.confirmationHash===value.check_hash,"请核对补证结果，并明确承认来源限制后另存新输入。");
      return execute(PREFIX+"save_supplement",{supplement_id:value.id,expected_check_hash:value.check_hash,confirmed_security:copy(value.security),acknowledge_source_limits:true},context);
    }
    async function queryPending(){const operation=state.pending;if(!operation||state.querying||!operation.request_hash)return;state.querying=true;state.readError="";emit();
      try{const value=await api(PREFIX+"supplement_requests/"+operation.payload.operation_id);if(state.pending!==operation)return;
        require(value?.operation_id===operation.payload.operation_id&&["COMPLETED","PENDING","NOT_RECORDED"].includes(value.status),"原请求回执身份不一致。");
        if(value.status==="NOT_RECORDED"){require(value.action===null&&value.request_hash===null&&value.result===null,"未记录回执不完整。");state.error="当前未见原请求，不代表未处理；保留原编号，只能继续查询。";return;}
        require(value.action===operation.action&&value.request_hash===operation.request_hash,"回执与原请求内容不一致。");
        if(value.status==="PENDING"){require(value.result===null,"待核对请求不能带入完成结果。");state.error="原请求仍待核对；不重新提交。";return;}
        return await accept(value.result,operation);
      }catch(error){state.readError="原请求回执读取未完成，仍保留原编号："+errorText(error);}
      finally{state.querying=false;emit();}
    }
    return {state,setContext,readContext,readList,openRecord,clearArtifact,setFileLoading,setArtifact,setConfirmation,check,save,queryPending,
      selectSaved:async()=>{require(state.fact?.view?.saved_input,"尚无已确认的新输入。");await deliver(state.fact.view.saved_input,true);}};
  }

  function installTerminalStockSupplementUI({host,api,perform,notify=()=>{},onInputSaved}){
    const document=host.ownerDocument,section=document.createElement("section");section.className="stock-supplement daily-section";section.hidden=true;
    section.innerHTML=`<style>.stock-supplement{min-width:0;border-top:1px solid var(--line,#52637c);padding-top:16px}.stock-supplement p,.stock-supplement dd{overflow-wrap:anywhere}.stock-supplement button,.stock-supplement summary,.stock-supplement input:not([type=checkbox]){min-height:44px}.stock-supplement summary{cursor:pointer;align-content:center}.stock-supplement .supplement-files{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));gap:16px}.stock-supplement input[type=file]{max-width:100%;width:100%;box-sizing:border-box}.stock-supplement input::file-selector-button{min-height:44px;font:inherit;padding:6px 10px}.stock-supplement .supplement-confirm{display:flex;gap:10px;align-items:flex-start;min-height:44px}.stock-supplement .supplement-confirm input{flex:none;margin-top:7px}.stock-supplement .actions{display:flex;flex-wrap:wrap;gap:8px}.stock-supplement pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>
      <h4>补充本机已有来源原件</h4><p data-supplement-role="context"></p><p>只读取你选择的四份已保存富途查询原件，不请求富途。原“公司行为覆盖未知”检查保持不变。</p>
      <div class="actions"><button type="button" class="btn" data-supplement-action="requirements">读取补证要求</button><button type="button" class="btn" data-supplement-action="list">读取已有补证记录</button></div><p data-supplement-role="requirements"></p>
      <div class="supplement-files">${keys.map(key=>`<label>${titles[key]}<input type="file" accept=".json,application/json" data-supplement-file="${key}"><span data-supplement-file-status="${key}">尚未选择</span></label>`).join("")}</div>
      <p class="section-note">单份原件最多 1 MiB，四份合计最多 4 MiB；上传原件字节，不修改或拼写内部字段。</p><button type="button" class="btn" data-supplement-action="check">检查这四份补充原件</button>
      <div data-supplement-role="list" class="daily-list"></div><div data-supplement-role="detail"></div>
      <label class="supplement-confirm" data-supplement-role="confirmation" hidden><input type="checkbox" data-supplement-confirm>我已核对证券与固定区间；来源完整性和截至时点仍未知，仅用于描述性研究，不是源方保证。我确认另存新输入，保留原检查和原结果。</label>
      <button type="button" class="btn primary" data-supplement-action="save" hidden>确认限制并另存新输入</button>
      <div data-supplement-role="fact" class="notice" role="status" hidden></div><div data-supplement-role="pending" class="notice" role="status" hidden></div><p data-supplement-role="error" role="alert" hidden></p><p data-supplement-role="read-error" role="status" hidden></p>`;
    host.appendChild(section);const role=name=>section.querySelector('[data-supplement-role="'+name+'"]'),button=name=>section.querySelector('[data-supplement-action="'+name+'"]');
    const controller=createController({api,perform,onInputSaved,changed:render}),state=controller.state;let fileContext="",fileEpoch=0;const fileSequences={};
    const securityText=(security,window)=>`${security.symbol} · ${security.exchange} · ${security.currency} · ${window.start} 至 ${window.end}`;
    function render(){const context=state.context,requirements=state.requirements,selected=state.selected,locked=state.busy||!!state.pending;section.hidden=!context&&!state.pending&&!state.fact;
      const stamp=context?context.id+context.check_hash:"";if(fileContext!==stamp){fileContext=stamp;fileEpoch++;for(const input of section.querySelectorAll('[data-supplement-file]'))input.value="";}
      role("context").textContent=context?securityText(context.security,{start:context.coverage_start,end:context.coverage_end}):"尚未选择可补证的原检查；下方仅保留先前请求与已保存事实。";
      role("requirements").textContent=state.loading?"正在只读核对补证要求…":requirements?(requirements.supported_formats.length?"支持本机已保存的富途 SDK 查询原件；检查不会连接来源。":"当前版本尚未提供可用来源解析器，不能提交补证。"):"请明确读取原记录的补证要求；不会获取新行情。";
      button("requirements").disabled=!context||state.loading||locked;button("list").disabled=!context||state.listLoading;
      for(const key of keys){const input=section.querySelector('[data-supplement-file="'+key+'"]');input.disabled=locked||!requirements?.supported_formats.length;
        section.querySelector('[data-supplement-file-status="'+key+'"]').textContent=state.readingFiles[key]?"正在本机读取…":state.files[key]?`${state.files[key].name} · ${state.files[key].size} 字节`:"尚未选择";}
      button("check").disabled=locked||!requirements?.supported_formats.length||!keys.every(key=>state.files[key])||Object.values(state.readingFiles).some(Boolean);
      role("list").innerHTML=state.listLoading?"正在只读查看已有补证…":state.items.map(row=>`<button type="button" class="btn" data-supplement-open="${esc(row.id)}">${esc(row.security.symbol)} · ${esc(row.window.end)} · ${row.saved_input_id?"已另存输入":row.status==="REVIEW_REQUIRED"?"待确认来源限制":"补证未通过"}</button>`).join("");
      const diagnostic=selected?.diagnostic,summary=typeof diagnostic==="string"?diagnostic:diagnostic?.summary;
      role("detail").innerHTML=selected?`<h4>${selected.saved_input_id?"补证输入已保存":selected.can_save?"可在确认来源限制后另存输入":"补证仍未通过"}</h4><p>${esc(securityText(selected.security,selected.window))}</p><p>${esc(summary||selected.reason||"请查看原补证依据。")}</p>${diagnostic?.action?`<p>下一步：${esc(diagnostic.action)}</p>`:""}<p>来源完整性与截至时点仍未知；未获独立来源认证。原失败记录保持不变。</p><details><summary>查看本次补证依据与身份</summary><p>原因：${esc(selected.reason)}</p><pre>${esc(JSON.stringify({details:diagnostic?.details,times:selected.times,check_hash:selected.check_hash,original_intake_id:selected.original_intake_id,original_check_hash:selected.original_check_hash},null,2))}</pre></details>`:"";
      const canSave=selected?.can_save===true&&!selected.saved_input_id;role("confirmation").hidden=!canSave;const confirm=section.querySelector('[data-supplement-confirm]');confirm.checked=state.confirmed;confirm.disabled=locked;button("save").hidden=!canSave;button("save").disabled=locked||!state.confirmed;
      const fact=state.fact;role("fact").hidden=!fact;role("fact").innerHTML=fact?`<strong>${fact.view.saved_input_id?"新输入已保存；本次保存没有复用、创建任务或运行研究。":"原补证检查已保留；没有改写原失败记录。"}</strong><p>${esc(securityText(fact.view.security,fact.view.window))}${same(fact.context,context)?"":" · 来自先前选择的检查"}</p>${fact.view.saved_input_id?'<button type="button" class="btn" data-supplement-action="select-saved">选用这份已保存行情</button>':""}<details><summary>查看原请求与保存身份</summary><p>${esc(fact.operation_id)}</p><p>补证：${esc(fact.view.id)}</p><p>新输入：${esc(fact.view.saved_input_id||"尚未保存")}</p></details>`:"";
      const pending=state.pending;role("pending").hidden=!pending;role("pending").innerHTML=pending?`<p>${state.busy?"正在处理原请求，请勿重复提交。":"原请求结果待核对；只查询这个编号，不重新提交。"}</p><p>原证券：${esc(pending.context.security.symbol)} · ${esc(pending.context.coverage_start)} 至 ${esc(pending.context.coverage_end)}</p><button type="button" class="btn" data-supplement-action="query">查询原请求回执</button><details><summary>查看原请求编号</summary><p>${esc(pending.payload.operation_id)}</p></details>`:"";
      if(pending)button("query").disabled=state.querying||!pending.request_hash;
      for(const [key,text] of [["error",state.error],["read-error",state.readError]]){role(key).hidden=!text;role(key).textContent=text;}
    }
    const fail=error=>{state.error=errorText(error);render();notify(state.error);};
    section.addEventListener("change",async event=>{const key=event.target.dataset.supplementFile;if(key){const file=event.target.files?.[0],epoch=fileEpoch,sequence=(fileSequences[key]||0)+1;fileSequences[key]=sequence;
        try{controller.clearArtifact(key);if(!file)return;require(file.size>0&&file.size<=(state.requirements?.limits.file_bytes||0),"原件不能为空，单份最多 1 MiB。");controller.setFileLoading(key,true);const bytes=new Uint8Array(await file.arrayBuffer());if(epoch!==fileEpoch||sequence!==fileSequences[key])return;require(bytes.byteLength===file.size,"本机原件读取不完整。");controller.setArtifact(key,{name:file.name,bytes});}
        catch(error){if(epoch===fileEpoch&&sequence===fileSequences[key])fail(error);}finally{if(epoch===fileEpoch&&sequence===fileSequences[key])controller.setFileLoading(key,false);}return;}
      if(event.target.matches('[data-supplement-confirm]'))controller.setConfirmation(event.target.checked);
    });
    section.addEventListener("click",event=>{const node=event.target.closest('button');if(!node||!section.contains(node)||node.disabled)return;
      if(node.dataset.supplementOpen){controller.openRecord(node.dataset.supplementOpen).catch(fail);return;}
      const actions={requirements:()=>controller.readContext(),list:()=>controller.readList(),check:()=>controller.check(),save:()=>controller.save(),query:()=>controller.queryPending(),"select-saved":()=>controller.selectSaved()};const action=actions[node.dataset.supplementAction];if(action)Promise.resolve().then(action).catch(fail);
    });
    render();return {element:section,setContext:controller.setContext,controller};
  }
  root.installTerminalStockSupplementUI=installTerminalStockSupplementUI;
  if(typeof module==="object"&&module.exports)module.exports={install:installTerminalStockSupplementUI,createController,canonical,keys,eligible};
})(typeof globalThis!=="undefined"?globalThis:window);
