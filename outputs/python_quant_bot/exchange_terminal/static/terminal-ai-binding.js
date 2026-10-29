/* Pure comparisons of explicitly recorded AI strategy identity. No requests. */
(() => {
  "use strict";
  const own=(value,key)=>Boolean(value&&Object.hasOwn(value,key));
  const plain=value=>Boolean(value&&typeof value==="object"&&!Array.isArray(value));
  const text=(value,limit)=>typeof value==="string"&&value.trim().length>0&&value.length<=limit&&!value.includes("\0");
  function validStrategyContext(value) {
    if(!plain(value)||Object.keys(value).some(key=>!["engine_id","strategy_id","strategy_params"].includes(key)))return false;
    if(own(value,"engine_id")&&!text(value.engine_id,150))return false;
    if(own(value,"strategy_id")&&!text(value.strategy_id,80))return false;
    if(!own(value,"strategy_params"))return true;
    const params=value.strategy_params;
    return plain(params)&&Object.keys(params).length<=40&&Object.entries(params).every(([key,item])=>
      /^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(key)&&(typeof item==="boolean"||typeof item==="number"&&Number.isFinite(item)&&Math.abs(item)<=Number.MAX_SAFE_INTEGER||text(item,100)));
  }
  function compareStrategy(evidence,current) {
    const copy=value=>JSON.parse(JSON.stringify(value));
    const analysis=validStrategyContext(evidence?.strategy_context)?copy(evidence.strategy_context):null;
    const task=validStrategyContext(current)?copy(current):{};
    const missing=[],differences=[],matches={};
    for(const field of ["engine_id","strategy_id","strategy_params"]) {
      for(const [label,context] of [["analysis",analysis],["task",task]])if(!own(context,field))missing.push(label+"."+field);
      if(!own(analysis,field)||!own(task,field))matches[field]=null;
      else if(field!=="strategy_params")matches[field]=analysis[field]===task[field];
      else {
        const left=analysis[field],right=task[field];let incomplete=false;
        for(const key of [...new Set([...Object.keys(left),...Object.keys(right)])].sort()) {
          if(!own(left,key)||!own(right,key)){missing.push((!own(left,key)?"analysis":"task")+".strategy_params."+key);incomplete=true;}
          else if(left[key]!==right[key])differences.push(key);
        }
        matches[field]=differences.length?false:incomplete?null:true;
      }
    }
    return {status:Object.values(matches).includes(false)?"MISMATCH":missing.length?"UNKNOWN":"MATCH",
      analysis_context:analysis,task_context:task,engine_matches:matches.engine_id,strategy_matches:matches.strategy_id,
      parameters_match:matches.strategy_params,differing_parameters:differences,missing_fields:missing};
  }
  const api={validStrategyContext,compareStrategy};
  globalThis.HakimiAiBinding=api;
  if(typeof module==="object"&&module.exports)module.exports=api;
})();
