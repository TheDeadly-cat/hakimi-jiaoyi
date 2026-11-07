/* Presentation adapter for the verified, frozen stock-research desktop. */
(() => {
  "use strict";
  function createCoreCompletionAdapter({api,state,render,refresh,showError,esc,runTask,openResult,closeTask=()=>{},document = globalThis.document}) {
    const detailErrors = new Map();
    const completedTasks = new Map();
    let completed = null;
    let savedTask = null;
    let readSelection = 0;
    const validDetail = (value,id = value?.id) => Boolean(value && typeof id === "string" && id.length > 0
      && id.length <= 160 && value.id === id && value.summary?.id === id
      && (value.status === undefined || value.status === "COMPLETED"));
    const errorText = error => [error?.info?.message,error?.info?.detail,error?.message]
      .filter(value=>typeof value === "string" && value.trim()).map(value=>value.replace(/\0/g,"").slice(0,1000)).join("；")
      || "读取未完成，请核对原操作记录。";
    const identity = value => typeof value === "string" && value.length > 0 && value.length <= 160 ? value : null;
    function recordedIdentity(value,key) {
      const ids=[value?.identities?.[key],value?.summary?.[key]].map(identity).filter(Boolean);
      return ids.length && ids.every(id=>id===ids[0]) ? ids[0] : null;
    }
    function identityText(value,id=value?.id) {
      const runId=recordedIdentity(value,"run_id");
      return `<p>报告运行编号：${esc(runId||"未记录或记录不一致")}</p><details><summary>读取与版本身份</summary><p>路由读取编号：${esc(id)}</p>${recordedIdentity(value,"task_id")?`<p>任务版本身份：${esc(recordedIdentity(value,"task_id"))}</p>`:""}</details>`;
    }
    function resultForTask(task) {
      if(!task?.task_id)return null;
      const known=completedTasks.get(task.task_id);
      if(known)return known;
      for(const value of state.runCache.values())if(validDetail(value)&&recordedIdentity(value,"task_id")===task.task_id)return value;
      const row=state.runs.find(item=>item.task_id===task.task_id&&identity(item.id)&&identity(item.run_id)&&(item.status===undefined||item.status==="COMPLETED"));
      return row?{id:row.id,summary:row}:null;
    }
    function resultForReadId(id) {
      const detail=state.runCache.get(id)||[...completedTasks.values()].find(item=>item.id===id);
      if(detail)return detail;
      const row=state.runs.find(item=>item.id===id);return row?{id,summary:row}:null;
    }
    function taskContinuation(task) {
      const choices=new Map();
      if(identity(task?.task_id)) {
        for(const row of state.runs)if(row.task_id===task.task_id&&identity(row.id)&&identity(row.run_id)&&(row.status===undefined||row.status==="COMPLETED"))choices.set(row.id,{id:row.id,run_id:row.run_id});
        for(const detail of [...state.runCache.values(),...completedTasks.values()])if(validDetail(detail)&&recordedIdentity(detail,"task_id")===task.task_id&&recordedIdentity(detail,"run_id"))choices.set(detail.id,{id:detail.id,run_id:recordedIdentity(detail,"run_id")});
      }
      const pending=(state.jobs||[]).some(job=>job.action==="run_task"&&["queued","running","unknown"].includes(job.status));
      return {results:[...choices.values()],synthetic:task?.inputs?.snapshot?.evidence_kind==="SYNTHETIC_TEST",pending,
        canRun:Boolean(identity(task?.id)&&identity(task?.task_id)&&task.state==="ENABLED"&&!task.legacy_task&&!pending&&choices.size===0)};
    }
    function attachTaskActions(value) {
      if(!identity(value?.id)||!identity(value?.task_id))return;
      const dialog=document.getElementById("dialog"),body=dialog?.querySelector(".dialog-body"),actions=dialog?.querySelector(".dialog-footer .actions");
      if(!dialog?.open||!body||!actions)return;
      const task=JSON.parse(JSON.stringify(value)),model=taskContinuation(task);
      dialog.dataset.continuedTask=task.id;dialog.dataset.continuedVersion=task.task_id;
      const note=document.createElement("p");note.className="notice section-gap";note.dataset.coreTaskContext="true";
      note.textContent=(model.synthetic?"虚构教学资料（SYNTHETIC）。历史结果不代表真实市场或未来收益。 ":"")
        +(model.results.length?"此版本已有保存结果；选择原报告读取，不会重新运行。":model.pending?"有原运行记录尚待核对；请先查看设置与日志，不重复运行。":task.state!=="ENABLED"?"此任务已暂停；请先核对并启用原任务。":"这份任务已保存。点击运行才会计算这笔本金的历史结果。");body.prepend(note);
      const layout=document.createElement("style");layout.textContent='#dialog:has([data-core-task-context]) #dialog-content{display:flex;flex-direction:column;max-height:calc(100dvh - 48px)}#dialog:has([data-core-task-context]) .dialog-header,#dialog:has([data-core-task-context]) .dialog-footer{flex-shrink:0}#dialog:has([data-core-task-context]) .dialog-body{min-height:0;max-height:none;flex:1 1 auto}@media(max-width:700px){#dialog:has([data-core-task-context]) #dialog-content{max-height:calc(100dvh - 20px)}}';body.append(layout);
      const button=document.createElement("button");button.type="button";button.className="btn primary";button.dataset.coreContinueAction=model.results.length?"result":"run";
      button.dataset.coreTaskVersion=task.task_id;let select;
      if(model.results.length){
        button.textContent="查看此版本已保存结果";
        const field=document.createElement("label");field.className="field section-gap";field.textContent="已保存的原报告编号";select=document.createElement("select");select.setAttribute("aria-label","已保存的原报告编号");
        if(model.results.length>1){const option=document.createElement("option");option.value="";option.textContent="请选择要读取的原报告";select.append(option);}
        for(const item of model.results){const option=document.createElement("option");option.value=item.id;option.textContent=item.run_id+" · 读取编号 "+item.id;select.append(option);}
        field.append(select);body.prepend(field);button.disabled=!select.value;select.addEventListener("change",()=>{button.disabled=!model.results.some(item=>item.id===select.value);});
      }else{button.textContent="运行这次回测";button.disabled=!model.canRun;}
      actions.querySelector('[data-action="edit-task"]')?.classList.remove("primary");actions.prepend(button);
      button.addEventListener("click",()=>{
        if(button.disabled||!dialog.open||dialog.dataset.continuedTask!==task.id||dialog.dataset.continuedVersion!==task.task_id)return;
        const current=taskContinuation(task);
        if(select){const id=select.value;if(!current.results.some(item=>item.id===id))return;button.disabled=true;closeTask();Promise.resolve(showSavedResult(id)).catch(showError);}
        else if(current.canRun&&typeof runTask==="function"){closeTask();Promise.resolve(runTask(task,button)).catch(showError);}
      });
    }
    function renderSavedTask() {
      if(!savedTask)return;
      const result=savedTask,position=result.revisions?.indexOf(result.selected_revision)??-1,version=position>=0?String(position+1):"未记录";
      const known=resultForTask(result),target=panel("saved-task");target.hidden=false;
      target.innerHTML=`<strong>“${esc(result.title||result.name||"研究任务")}”版本 ${esc(version)} 已保存。</strong>`
        +(known?`<p>此版本已有完成结果。查看同一份保存结果，不会再次运行回测。</p>${readButton("查看此版本已保存结果",known.id)}${identityText(known)}`
          :`<p>此保存版本尚未确认有完成结果。明确运行后，完成结果会显示在这里。</p><button type="button" class="btn primary" data-core-run-task="1" data-core-task-version="${esc(result.task_id)}" ${result.state!=="ENABLED"?"disabled":""}>运行这次回测</button><details><summary>已保存版本身份</summary><p>${esc(result.task_id)}</p></details>`);
    }
    async function showSavedResult(id) {
      const selection=++readSelection;
      if(typeof openResult==="function")await openResult(id);
      const detail=await loadRun(id);
      if(validDetail(detail,id))revealSavedResult(id,selection);
      return detail;
    }
    function revealSavedResult(id,selection) {
      const view=document.defaultView;
      if(!view?.requestAnimationFrame)return;
      // Render observers add the report actions before this frame. Re-read the
      // current heading so a replaced view or a late read cannot steal focus.
      view.requestAnimationFrame(()=>{
        if(selection!==readSelection || state.view!=="results" || state.selectedRun!==id || detailErrors.has(id))return;
        const main=document.getElementById("main"),heading=main?.querySelector(".result-heading");
        if(!heading || main.hidden || !validDetail(state.runCache.get(id),id))return;
        try {
          const box=heading.getBoundingClientRect();let covered=0;
          for(const element of document.querySelectorAll(".sidebar,.topbar")) {
            const position=view.getComputedStyle(element).position,rect=element.getBoundingClientRect();
            if(["sticky","fixed"].includes(position) && rect.top<=0 && rect.bottom>0 && rect.left<box.right && rect.right>box.left)covered=Math.max(covered,rect.bottom);
          }
          // Scroll only this document's viewport; scrollIntoView can also move
          // its containing application iframe and obscure the report again.
          view.scrollTo({top:Math.max(0,view.scrollY+box.top-covered-12),left:view.scrollX,behavior:"auto"});
          const title=heading.querySelector("h2")||heading;
          title.setAttribute("tabindex","-1");title.focus({preventScroll:true});
        } catch(error) {readFailure("presentation",error,id);}
      });
    }
    function panel(kind) {
      let host=document.getElementById("core-completion-feedback");
      if(!host) {
        host=document.createElement("section");host.id="core-completion-feedback";host.className="panel-body";
        host.setAttribute("style","overflow-wrap:anywhere;scroll-margin-top:80px");
        host.setAttribute("aria-label","股票研究保存与读取状态");
        (document.getElementById("terminalQuantWorkspace") || document.getElementById("main")).before(host);
        host.addEventListener("click",event=>{
          const button=event.target.closest("[data-core-read-action],[data-core-run-task]");if(!button||button.disabled)return;
          const isRun=button.dataset.coreRunTask !== undefined;
          if(!isRun)button.disabled=true;
          const known=isRun?resultForTask(savedTask):null;
          const work=isRun
            ? (button.dataset.coreTaskVersion&&button.dataset.coreTaskVersion!==savedTask?.task_id?Promise.reject(Error("保存版本已变化，请重新核对当前版本。"))
              :known?showSavedResult(known.id):savedTask && typeof runTask === "function" ? runTask(savedTask,button) : Promise.reject(Error("请重新核对已保存任务。")))
            : button.dataset.coreReadAction === "refresh" ? refresh({quiet:true}) : showSavedResult(button.dataset.coreRunId);
          Promise.resolve(work).catch(error=>isRun&&!known?showError(error):readFailure(known||button.dataset.coreRunId?"detail":"refresh",error,known?.id||button.dataset.coreRunId)).finally(()=>{if(!isRun)button.disabled=false;});
        });
      }
      let element=document.getElementById("core-read-"+kind);
      if(!element){element=document.createElement("div");element.id="core-read-"+kind;element.className="notice section-gap";element.hidden=true;element.setAttribute("role","status");element.setAttribute("aria-live","polite");host.append(element);}
      return element;
    }
    function readButton(label,id) {
      return `<button type="button" class="btn small" data-core-read-action="result" data-core-run-id="${esc(id)}">${esc(label)}</button>`;
    }
    function begin(action) {
      if(!["run_task","create_task","revise_task","copy_task"].includes(action))return;
      readSelection++;
      completed=null;panel("completed").hidden=true;panel("outcome").hidden=true;
    }
    function confirm(action,result) {
      if(["create_task","revise_task","copy_task"].includes(action)) {
        if(!result?.id || !result.task_id || !["ENABLED","PAUSED"].includes(result.state)) return;
        savedTask=JSON.parse(JSON.stringify(result));
        renderSavedTask();
        const view=document.defaultView;
        if(view?.CustomEvent)view.dispatchEvent(new view.CustomEvent("hakimi-core-task-saved",{detail:JSON.parse(JSON.stringify(result))}));
        return;
      }
      if(action!=="run_task")return;
      if(!validDetail(result)) {
        const target=panel("outcome");target.className="notice warning section-gap";target.hidden=false;
        target.textContent="运行结果尚未确认。请核对原操作记录，不要重复运行。";
        return;
      }
      completed=result;
      const taskId=recordedIdentity(result,"task_id");if(taskId)completedTasks.set(taskId,result);
      const target=panel("completed");target.hidden=false;
      target.innerHTML=`<strong>股票研究回测已完成，结果已保存。</strong>${identityText(result)}${readButton("查看已保存结果",result.id)}`;
      // The operation receipt is a saved result even if the subsequent status
      // request fails or returns an older list.
      state.runCache.set(result.id,result);restoreRuns();
    }
    function restoreRuns() {
      if(completed && !state.runs.some(row=>row.id===completed.id))state.runs=[completed.summary,...state.runs];
      renderSavedTask();
    }
    function readFailure(kind,error,id) {
      const detail=kind==="detail" || kind==="presentation";
      if(detail && id)detailErrors.set(id,errorText(error));
      const target=panel(detail?"detail":"refresh");target.hidden=false;target.className="notice warning section-gap";
      const title=detail?"结果详情读取或展示未完成":"辅助记录读取未完成";
      target.innerHTML=`<strong>${title}</strong><p>${esc(errorText(error))}</p>${detail&&id?identityText(resultForReadId(id),id):""}<p>已保存结果保持不变；重新读取不会运行回测。</p>`
        +(detail&&id?readButton("重新读取这份结果",id):'<button type="button" class="btn small" data-core-read-action="refresh">重新读取记录</button>');
    }
    function clearReadFailure(kind,id) {
      if(kind==="detail")detailErrors.delete(id);
      const target=document.getElementById("core-read-"+kind);
      if(target && (kind!=="detail" || !detailErrors.size))target.hidden=true;
      else if(target && kind==="detail") {
        const [remaining,message]=[...detailErrors].at(-1);
        readFailure("detail",{message},remaining);
      }
    }
    function clearRenderedDetail() {
      const id=state.selectedRun||state.runs[0]?.id;
      if(id && state.runCache.has(id))clearReadFailure("detail",id);
    }
    async function present(callback,result,action) {
      if(action==="run_task" && !validDetail(result))return;
      try { await callback(result); if(action==="run_task")clearRenderedDetail(); }
      catch(error) {readFailure(action==="run_task"?"presentation":"refresh",error,result?.id);}
    }
    function operationError(action,job,error,target) {
      if(job?.status!=="succeeded"){showError(error,target);return null;}
      confirm(action,job.result);readFailure("refresh",error);
      return job.result;
    }
    function resultPlaceholder(id) {
      const error=detailErrors.get(id);
      return error?`<div class="notice warning"><strong>结果详情读取未完成</strong><p>${esc(error)}</p>${identityText(resultForReadId(id),id)}<p>原结果保留；请使用上方“重新读取这份结果”。</p></div>`
        :'<div class="loading-block"><span class="spinner" aria-hidden="true"></span>正在读取保存的结果…</div>';
    }
    async function loadRun(id,quiet=false) {
      if(!id || state.runLoading.has(id) || (quiet && detailErrors.has(id)))return;
      if(!quiet)state.selectedRun=id;
      if(state.runCache.has(id) && !detailErrors.has(id)) {
        if(!quiet)try{render();}catch(error){readFailure("presentation",error,id);}
        return state.runCache.get(id);
      }
      state.runLoading.add(id);
      try {
        if(!quiet)render();
        const detail=await api("runs/"+encodeURIComponent(id));
        if(!validDetail(detail,id))throw Error("返回的保存结果身份或状态无法确认，请核对原操作记录。");
        state.runCache.set(id,detail);clearReadFailure("detail",id);
        const taskId=recordedIdentity(detail,"task_id");if(taskId)completedTasks.set(taskId,detail);renderSavedTask();
        if(!state.selectedRun)state.selectedRun=id;
        render();return detail;
      } catch(error) {
        readFailure("detail",error,id);
        try{render();}catch(renderError){readFailure("presentation",renderError,id);}
      } finally {state.runLoading.delete(id);}
    }
    return {begin,confirm,restoreRuns,readFailure,clearReadFailure,clearRenderedDetail,present,operationError,resultPlaceholder,loadRun,showSavedResult,taskContinuation,attachTaskActions};
  }
  globalThis.createCoreCompletionAdapter=createCoreCompletionAdapter;
  if(typeof module==="object"&&module.exports)module.exports={createCoreCompletionAdapter};
})();
