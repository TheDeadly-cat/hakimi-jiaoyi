/* Presentation adapter for the verified, frozen stock-research desktop. */
(() => {
  "use strict";
  function createCoreCompletionAdapter({api,state,render,refresh,showError,esc,runTask,openResult,document = globalThis.document}) {
    const detailErrors = new Map();
    const completedTasks = new Map();
    let completed = null;
    let savedTask = null;
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
    function renderSavedTask() {
      if(!savedTask)return;
      const result=savedTask,position=result.revisions?.indexOf(result.selected_revision)??-1,version=position>=0?String(position+1):"未记录";
      const known=resultForTask(result),target=panel("saved-task");target.hidden=false;
      target.innerHTML=`<strong>“${esc(result.title||result.name||"研究任务")}”版本 ${esc(version)} 已保存。</strong>`
        +(known?`<p>此版本已有完成结果。查看同一份保存结果，不会再次运行回测。</p>${readButton("查看此版本已保存结果",known.id)}${identityText(known)}`
          :`<p>此保存版本尚未确认有完成结果。明确运行后，完成结果会显示在这里。</p><button type="button" class="btn primary" data-core-run-task="1" data-core-task-version="${esc(result.task_id)}" ${result.state!=="ENABLED"?"disabled":""}>运行这次回测</button><details><summary>已保存版本身份</summary><p>${esc(result.task_id)}</p></details>`);
    }
    async function showSavedResult(id) {
      if(typeof openResult==="function")await openResult(id);
      return loadRun(id);
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
    return {begin,confirm,restoreRuns,readFailure,clearReadFailure,clearRenderedDetail,present,operationError,resultPlaceholder,loadRun};
  }
  globalThis.createCoreCompletionAdapter=createCoreCompletionAdapter;
  if(typeof module==="object"&&module.exports)module.exports={createCoreCompletionAdapter};
})();
