/* Presentation adapter for the verified, frozen stock-research desktop. */
(() => {
  "use strict";
  function createCoreCompletionAdapter({api,state,render,refresh,showError,esc,runTask,document = globalThis.document}) {
    const detailErrors = new Map();
    let completed = null;
    let savedTask = null;
    const validDetail = (value,id = value?.id) => Boolean(value && typeof id === "string" && id.length > 0
      && id.length <= 160 && value.id === id && value.summary?.id === id
      && (value.status === undefined || value.status === "COMPLETED"));
    const errorText = error => [error?.info?.message,error?.info?.detail,error?.message]
      .filter(value=>typeof value === "string" && value.trim()).map(value=>value.replace(/\0/g,"").slice(0,1000)).join("；")
      || "读取未完成，请核对原操作记录。";
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
          const work=isRun
            ? (savedTask && typeof runTask === "function" ? runTask(savedTask,button) : Promise.reject(Error("请重新核对已保存任务。")))
            : button.dataset.coreReadAction === "refresh" ? refresh({quiet:true}) : loadRun(button.dataset.coreRunId);
          Promise.resolve(work).catch(error=>isRun?showError(error):readFailure("refresh",error)).finally(()=>{if(!isRun)button.disabled=false;});
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
        const position=result.revisions?.indexOf(result.selected_revision) ?? -1;
        const version=position>=0?String(position+1):"未记录";
        const target=panel("saved-task");target.hidden=false;
        target.innerHTML=`<strong>“${esc(result.title||result.name||"研究任务")}”版本 ${esc(version)} 已保存。</strong><p>保存没有运行回测。此按钮绑定刚保存的任务版本，版本改变时会停止并要求重新核对。</p><button type="button" class="btn primary" data-core-run-task="1" ${result.state!=="ENABLED"?"disabled":""}>运行这次回测</button><details><summary>已保存版本身份</summary><p>${esc(result.task_id)}</p></details>`;
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
      const target=panel("completed");target.hidden=false;
      target.innerHTML=`<strong>股票研究回测已完成，结果已保存。</strong><p>结果编号：${esc(result.id)}</p>${readButton("查看已保存结果",result.id)}`;
      // The operation receipt is a saved result even if the subsequent status
      // request fails or returns an older list.
      state.runCache.set(result.id,result);restoreRuns();
    }
    function restoreRuns() {
      if(completed && !state.runs.some(row=>row.id===completed.id))state.runs=[completed.summary,...state.runs];
    }
    function readFailure(kind,error,id) {
      const detail=kind==="detail" || kind==="presentation";
      if(detail && id)detailErrors.set(id,errorText(error));
      const target=panel(detail?"detail":"refresh");target.hidden=false;target.className="notice warning section-gap";
      const title=detail?"结果详情读取或展示未完成":"辅助记录读取未完成";
      target.innerHTML=`<strong>${title}</strong><p>${esc(errorText(error))}</p>${detail&&id?`<p>结果编号：${esc(id)}</p>`:""}<p>已保存结果保持不变；重新读取不会运行回测。</p>`
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
      return error?`<div class="notice warning"><strong>结果详情读取未完成</strong><p>${esc(error)}</p><p>结果编号：${esc(id)}。原结果保留；请使用上方“重新读取这份结果”。</p></div>`
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
