"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const test = require("node:test");
const protocol = require("./terminal-quant-ui.js");
const ui = fs.readFileSync(path.join(__dirname, "terminal-quant-ui.js"), "utf8");

function evidence() {
  return {schema_version:"hakimi-ai-research-evidence-v1",symbol:"AAPL",bar:"1Dutc",session:"regular",
    question:"QA fixture",generated_at:1792503000000,
    input_identity:{rows_sha256:"a".repeat(64),row_count:100,first_ts:1700000000000,last_ts:1792500000000,
      source:"fixture-provider",price_basis:"SUPPLIED_LAST_CANDLE_CLOSE",snapshot_id:null},
    providers:[{provider:"deepseek",model:"qa-model",content:"<script>fake_instruction()</script>",summary:"QA only"}]};
}
function uiFunction(name) {
  const offset = ui.indexOf("function " + name + "(");
  assert.ok(offset >= 0, name);
  const start = ui.slice(offset-6,offset) === "async " ? offset-6 : offset;
  const next = /\n    (?:async )?function \w+\(/g;
  next.lastIndex = offset+10;
  return ui.slice(start,next.exec(ui)?.index ?? ui.length).trim();
}
function context(ai = evidence()) {
  return {symbol:"AAPL",bar:"1Dutc",session:"regular",strategy_id:"macd",strategy_params:{fast:12},
    strategy_name:"MACD",risk:{position_pct:25},blockers:[],ai_evidence:ai};
}

test("only bounded daily evidence for the same chart context can cross the bridge", () => {
  const receipt = evidence();
  assert.equal(protocol.validAiEvidence(receipt,context()),true);
  assert.equal(protocol.validContext(context()),true);
  for (const change of [{symbol:"MSFT"},{bar:"1H"},{session:"pre"},{order_allowed:true}]) {
    assert.equal(protocol.validAiEvidence({...receipt,...change},context()),false);
  }
  assert.equal(protocol.validAiEvidence({...receipt,providers:[receipt.providers[0],receipt.providers[0]]}),false);
  assert.equal(protocol.validAiEvidence({...receipt,generated_at:Number.MAX_SAFE_INTEGER}),false);
  assert.equal(protocol.validAiEvidence({...receipt,providers:[{...receipt.providers[0],content:"x".repeat(16001)}]}),false);
});

test("receiving a reference changes no strategy/risk controls and respects deselection", () => {
  const state = {revisionOf:null,aiEvidence:null,aiEvidenceEnabled:false,strategy_params:{fast:7},risk:{position_pct:10}};
  const elements = {"tq-symbol":{value:""},"tq-context":{}};
  const h = vm.createContext({state,validAiEvidence:protocol.validAiEvidence,$:id=>elements[id],
    value:id=>elements[id]?.value || "",renderAiEvidence(){},esc:String,button:()=>""});
  vm.runInContext(uiFunction("applyContext"),h);
  h.applyContext(context());
  assert.equal(state.aiEvidenceEnabled,true);
  assert.equal(state.aiEvidence.symbol,"AAPL");
  assert.deepEqual(state.strategy_params,{fast:7});
  assert.deepEqual(state.risk,{position_pct:10});
  state.aiEvidenceEnabled = false;
  h.applyContext(context());
  assert.equal(state.aiEvidenceEnabled,false);
  h.applyContext({...context(),bar:"1H",ai_evidence:undefined});
  assert.equal(state.aiEvidence,null);
  assert.equal(state.aiEvidenceEnabled,false);
});

test("editing a saved version keeps its original reference despite a new live context", () => {
  const original = evidence();
  const state = {revisionOf:"saved-task",aiEvidence:original,aiEvidenceEnabled:true};
  const elements = {"tq-symbol":{value:"AAPL"},"tq-context":{}};
  const h = vm.createContext({state,validAiEvidence:protocol.validAiEvidence,$:id=>elements[id],
    value:id=>elements[id]?.value || "",renderAiEvidence(){},esc:String,button:()=>""});
  vm.runInContext(uiFunction("applyContext"),h);
  h.applyContext({...context(),symbol:"MSFT",ai_evidence:undefined});
  assert.equal(state.aiEvidence,original);
  assert.equal(state.aiEvidenceEnabled,true);
});

test("raw model text is escaped and numerical identity does not claim authentication", () => {
  const h = vm.createContext({validAiEvidence:protocol.validAiEvidence,
    esc:value=>String(value).replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")});
  vm.runInContext(uiFunction("aiEvidenceHtml"),h);
  const html = h.aiEvidenceHtml(evidence(),{status:"SAME_NUMERIC_ROWS"});
  assert.match(html,/&lt;script&gt;/);
  assert.doesNotMatch(html,/<script>/);
  assert.match(html,/来源仍未独立认证/);
  assert.match(h.aiEvidenceHtml(evidence(),{status:"DIFFERENT_SNAPSHOT"}),/不代表分析过这份回测数据/);
});

test("save action includes only selected reference and leaves execution values unchanged", async () => {
  const state = {revisionOf:null,aiEvidence:evidence(),aiEvidenceEnabled:false,
    catalog:[{id:"macd",parameter_fields:[{key:"fast"}]}]};
  const values = {"tq-name":"QA task","tq-strategy":"macd","tq-input":"frozen-input",
    "tq-position":"25","tq-take":"0","tq-stop":"8","tq-fee":"0.05","tq-slippage":"2"};
  const payloads = [];
  const form = {reportValidity:()=>true,querySelectorAll:()=>[{dataset:{tqParam:"fast",tqType:"number"},value:"7"}]};
  const h = vm.createContext({state,validAiEvidence:protocol.validAiEvidence,value:id=>values[id],
    $:()=>form,researchBlocker:()=>"",notify(){},act:async(action,payload)=>payloads.push({action,payload})});
  vm.runInContext(uiFunction("saveTask"),h);
  await h.saveTask({preventDefault(){},submitter:{}});
  assert.equal("ai_evidence" in payloads[0].payload,false);
  state.aiEvidenceEnabled = true;
  await h.saveTask({preventDefault(){},submitter:{}});
  assert.equal(payloads[1].action,"terminal_save_task");
  assert.equal(payloads[1].payload.ai_evidence,state.aiEvidence);
  assert.equal(payloads[1].payload.strategy_params.fast,7);
  assert.equal(payloads[1].payload.risk.leverage,1);
  assert.equal(payloads[1].payload.risk.position_pct,25);
  assert.equal(payloads.length,2); // Saving never dispatches run_task.
});
