"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const {renderDiagnostic,factorValue}=require("./terminal-strategy-candidates-ui");
const row=changes=>({schema_version:"hakimi-terminal-strategy-diagnostic-v1",diagnostic_id:"a".repeat(64),input_id:"b".repeat(64),
  strategy_id:"momentum",name:"动量",strategy_params:{threshold:.015},status:"READY",group:"ENTRY_MATCH",decision_matches_factors:true,
  signal:{action:"BUY"},position_context:{has_position:false},symbol:"QA",cutoff_session:"2024-07-31",complete_rows:130,warmup_rows:80,required_rows:82,
  factors:[{key:"momentum",label:"动量",value:.02,operator:">",threshold:.015,passed:true,applies_to_position:true,unit:"ratio"}],...changes});
test("ratio values and both inclusive boundaries use the same percent units",()=>{
  assert.equal(factorValue(.015,"ratio"),"1.5%");assert.equal(factorValue(0,"ratio"),"0%");
  assert.equal(factorValue([.005,.04],"ratio"),"0.5% 至 4%");
  const html=renderDiagnostic(row({factors:[{label:"ATR 比例",value:.02,operator:"between_inclusive",threshold:[.005,.04],passed:true,unit:"ratio"}]}));
  assert.match(html,/2%/);assert.match(html,/0.5% 至 4%（含边界）/);assert.doesNotMatch(html,/between_inclusive<\/td>/);
});
test("a BUY on insufficient data cannot offer strategy selection",()=>{
  const html=renderDiagnostic(row({status:"DATA_INSUFFICIENT",group:"INSUFFICIENT",missing_rows:2,complete_rows:80}));
  assert.match(html,/还缺 2 根/);assert.match(html,/至少需要 82 根/);
  assert.match(html,/data-candidate-choose="[a-f0-9]+" disabled/);
  assert.doesNotMatch(html,/截至所选日，满足开仓条件/);
});
test("missing factor is not zero and observed EXIT is not described as a new buy",()=>{
  const html=renderDiagnostic(row({signal:{action:"EXIT"},group:"EXIT_MATCH",position_context:{has_position:true},
    factors:[{label:"未记录值",value:null,operator:"<",threshold:1,passed:null,unit:"price"}]}));
  assert.match(html,/满足退出条件/);assert.match(html,/未记录值<\/th><td>未记录/);assert.match(html,/资料不足/);
});
test("provider and strategy text is escaped in visible reasons and raw details",()=>{
  const html=renderDiagnostic(row({name:'<img src=x onerror=alert(1)>',factors:[{label:'<script>alert(1)</script>',value:2,threshold:1,operator:'>',passed:true}]}));
  assert.doesNotMatch(html,/<img|<script>/);assert.match(html,/&lt;img/);assert.match(html,/&lt;script/);
});
