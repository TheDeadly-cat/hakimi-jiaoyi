"use strict";
const assert=require("node:assert/strict"),path=require("node:path"),test=require("node:test"),{execFileSync}=require("node:child_process");
const {compareStrategy,validStrategyContext}=require("./terminal-ai-binding");
const current={engine_id:"terminal.causal-long-only-signals-v7",strategy_id:"dual_ma",strategy_params:{fast_window:5,slow_window:20,min_cash_pct:10}};

test("current-form parameter edits are compared to the analysis snapshot without mutation",()=>{
  const evidence={strategy_context:structuredClone(current)},before=JSON.stringify(evidence);
  assert.equal(compareStrategy(evidence,current).status,"MATCH");
  const changed=compareStrategy(evidence,{...current,strategy_params:{...current.strategy_params,fast_window:6}});
  assert.equal(changed.status,"MISMATCH");assert.deepEqual(changed.differing_parameters,["fast_window"]);
  assert.equal(JSON.stringify(evidence),before);
  changed.analysis_context.strategy_params.fast_window=99;assert.equal(evidence.strategy_context.strategy_params.fast_window,5);
});

test("missing old rule fields remain unknown and different engines never match",()=>{
  for(const evidence of [{},{strategy_context:{}},{strategy_context:{strategy_id:"dual_ma"}},
    {strategy_context:{...current,strategy_params:{fast_window:5}}}]) {
    const result=compareStrategy(evidence,current);assert.equal(result.status,"UNKNOWN");assert.ok(result.missing_fields.length);
  }
  assert.equal(compareStrategy({strategy_context:current},{...current,engine_id:"terminal.causal-long-only-signals-v6"}).status,"MISMATCH");
});

test("strategy context accepts only bounded explicit scalar fields",()=>{
  assert.equal(validStrategyContext(current),true);assert.equal(validStrategyContext({}),true);
  for(const context of [{...current,order_allowed:true},{...current,engine_id:""},
    {...current,strategy_params:{threshold:NaN}},{...current,strategy_params:{threshold:Infinity}},
    {...current,strategy_params:{threshold:2**54}},{...current,strategy_params:{x:{value:1}}}])assert.equal(validStrategyContext(context),false);
});

test("browser comparison and saved backend binding agree on valid complete and legacy cases",()=>{
  const cases=[{evidence:{strategy_context:current},current},
    {evidence:{strategy_context:current},current:{...current,strategy_params:{...current.strategy_params,slow_window:21}}},
    {evidence:{},current},{evidence:{strategy_context:{strategy_id:"dual_ma"}},current},
    {evidence:{strategy_context:{...current,strategy_params:{fast_window:5}}},current},
    {evidence:{strategy_context:current},current:{...current,engine_id:"terminal.other"}},
    {evidence:{strategy_context:{...current,strategy_params:{flag:true}}},current:{...current,strategy_params:{flag:1}}}];
  const results=JSON.parse(execFileSync(process.env.PYTHON||"python",["-c",
    "import sys,json;sys.path.insert(0,'outputs/python_quant_bot');from exchange_terminal.services.terminal_ai_evidence import compare_ai_strategy;cases=json.load(sys.stdin);json.dump([compare_ai_strategy(x['evidence'],x['current'].get('strategy_id'),x['current'].get('strategy_params'),x['current'].get('engine_id')) for x in cases],sys.stdout)"],
    {cwd:path.resolve(__dirname,"../../../.."),input:JSON.stringify(cases),encoding:"utf8"}));
  assert.deepEqual(cases.map(row=>compareStrategy(row.evidence,row.current)),results);
});
