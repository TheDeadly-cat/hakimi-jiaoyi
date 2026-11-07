"use strict";
const assert = require("node:assert/strict");
const test = require("node:test");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const journal = require("./terminal-judgment-ui");
const protocol = require("./terminal-quant-ui");
const INPUT = "a".repeat(64), ID = "b".repeat(64), TASK = "c".repeat(64), RUN = "d".repeat(64);
const clone = (value) => JSON.parse(JSON.stringify(value));
const input = () => ({id:INPUT,input_id:INPUT,symbol:"AAPL",date_start:"2026-01-02",date_end:"2026-10-01",row_count:190,
  source_id:"local-csv",meta:{session:"regular",price_basis:"RAW",asset_class:"EQUITY"}});
const context = () => ({input_id:INPUT,binding:{kind:"terminal_input",id:INPUT},input:input(),label:"AAPL 冻结行情"});
const fields = () => ({direction:"WAIT",as_of:"2026-06-13",thesis:"等待量价确认",trigger_condition:"收盘超过前高",
  invalidation_condition:"跌破确认低点",counter_evidence:"成交量不足\n行业不同步"});
const detail = (extra = {}) => ({id:ID,judgment_id:ID,status:"RECORDED",integrity_status:"PASS",client_request_id:"create-request",
  symbol:"AAPL",bar:"1D",input_id:INPUT,input_summary:input(),binding:{kind:"terminal_input",id:INPUT},
  direction:"WAIT",as_of:"2026-06-13",thesis:"等待量价确认",trigger_condition:"突破前高",invalidation_condition:"结构失败",
  counter_evidence:[],head:null,event_count:0,events:[],created_at:"2026-10-21T02:00:00Z",...extra});
const row = () => ({ts_ms:Date.parse("2026-06-12T20:00:00Z"),date:"2026-06-12",open:100,high:103,low:99,close:102,volume:1000});

test("loading the module only defines APIs without DOM or network access",() => {
  const sandbox={module:{exports:{}},get document(){throw new Error("unexpected DOM");},get fetch(){throw new Error("unexpected fetch");}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,"terminal-judgment-ui.js"),"utf8"),sandbox);
  assert.equal(typeof sandbox.installTerminalJudgmentUI,"function");
  assert.equal(typeof sandbox.module.exports.createController,"function");
});

test("create payload accepts an earlier covered cutoff including weekends and bounds the form",() => {
  const payload=journal.createPayload(context(),fields(),"request-1");
  assert.equal(payload.as_of,"2026-06-13");
  assert.deepEqual(payload.counter_evidence,["成交量不足","行业不同步"]);
  assert.equal(payload.client_request_id,"request-1");
  assert.equal(payload.created_at,undefined);
  assert.equal(payload.indicator_snapshot,undefined);
  for(const as_of of ["2025-12-31","2026-10-02","2026-02-30"])
    assert.throws(()=>journal.createPayload(context(),{...fields(),as_of},"x"),/日期|截止日/);
  assert.throws(()=>journal.createPayload(context(),{...fields(),thesis:"   "},"x"),/观点/);
  assert.throws(()=>journal.createPayload(context(),{...fields(),counter_evidence:Array(9).fill("a")},"x"),/8/);
  assert.throws(()=>journal.createPayload(context(),{...fields(),counter_evidence:["x".repeat(501)]},"x"),/500/);
  assert.throws(()=>journal.createPayload({...context(),binding:{kind:"constructor",id:INPUT}},fields(),"x"),/冻结/);
});

test("append captures the exact saved head and treats user actions as text only",() => {
  const payload=journal.eventPayload(detail({head:"e".repeat(64)}),{event_type:"USER_ACTION",as_of:"2026-06-15",note:"本人报告已减仓，尚无成交凭证"},"event-1");
  assert.equal(payload.expected_head,"e".repeat(64));
  assert.equal(payload.event_type,"USER_ACTION");
  assert.deepEqual(Object.keys(payload).sort(),["as_of","client_request_id","event_type","expected_head","judgment_id","note"].sort());
  assert.throws(()=>journal.eventPayload(detail({integrity_status:"UNKNOWN"}),{event_type:"OBSERVATION",as_of:"2026-06-15",note:"x"},"x"),/校验/);
  assert.throws(()=>journal.eventPayload(detail(),{event_type:"BUY",as_of:"2026-06-15",note:"x"},"x"),/类型/);
  assert.throws(()=>journal.eventPayload(detail({events:[{as_of:"2026-07-01"}]}),{event_type:"OBSERVATION",as_of:"2026-06-15",note:"x"},"x"),/最近/);
});

test("judgment input replay uses independent identity and cannot carry pretend fills",() => {
  const replay={source:"JUDGMENT_FROZEN_INPUT",judgment_id:ID,record_hash:"e".repeat(64),input_id:INPUT,
    symbol:"AAPL",meta:input().meta,rows:[row()],trades:[]};
  assert.equal(protocol.validReplay(replay),true);
  for(const bad of [{...replay,trades:[{side:"BUY"}]},{...replay,run_id:"judgment:"+ID},{...replay,report_hash:ID},
    {...replay,record_hash:"wrong"},{...replay,judgment_id:"wrong"},{...replay,rows:[{...row(),high:98}]}])
    assert.equal(protocol.validReplay(bad),false);
  assert.equal(protocol.validReplay({...replay,source:"JUDGMENT_FROZEN_RUN",run_id:RUN,report_hash:RUN,trades:[{side:"BUY"}]}),true);
});

test("only completed runs become judgment sources while old task identities stay available",() => {
  const sources=journal.sourcesFrom({inputs:[input()],tasks:[{id:TASK,input_id:INPUT,title:"旧任务",version:1,requires_revision:true}],
    runs:[{id:RUN,status:"COMPLETED",configuration:{input_id:INPUT},version:2},{id:"f".repeat(64),status:"UNKNOWN",input_summary:input()}]});
  assert.equal(sources.length,3);
  assert.ok(sources.some((source)=>source.kind==="terminal_task"&&source.id===TASK));
  assert.equal(sources.filter((source)=>source.kind==="terminal_run").length,1);
});

test("timeline and details escape untrusted text and distinguish cutoff, write time and AI",() => {
  const html=journal.detailHtml(detail({thesis:'<img src=x onerror="bad()">',task_configuration:{ai_evidence:{content:"<script>bad()</script>"}},
    events:[{event_type:"USER_ACTION",note:"<b>买入</b>",as_of:"2026-06-15",created_at:"2026-10-21T02:10:00Z"}]}));
  assert.match(html,/用户报告 · 未核验成交/); assert.match(html,/AI 参考/); assert.match(html,/系统记录时间/);
  assert.match(html,/声明的数据截止日/); assert.match(html,/冻结原输入覆盖/);
  assert.ok(!html.includes("<script>bad()")); assert.ok(!html.includes("<img src=x"));
  assert.match(html,/&lt;b&gt;买入/);
  const unknown=journal.detailHtml(detail({integrity_status:"UNKNOWN",reason:"source missing"}));
  assert.match(unknown,/不可复盘/);assert.ok(!unknown.includes('data-tj-action="replay"'));assert.ok(!unknown.includes("tj-event-form"));
  assert.match(journal.indicatorHtml({values:{sma:null,ema:Infinity,rsi:0},contract:{version:"v1"}}),/不足／缺失/);
});

test("AI generated after a historical cutoff is retrospective; unparseable timing stays unknown without changing evidence",() => {
  const evidence={generated_at:Date.parse("2026-10-21T03:00:00Z"),content:"原任务 AI 内容"},before=clone(evidence);
  const html=journal.detailHtml(detail({as_of:"2026-09-20",task_configuration:{ai_evidence:evidence}}));
  assert.match(html,/AI 参考生成日期（UTC）：2026-10-21/);
  assert.match(html,/该 AI 参考生成于声明截止日之后，仅用于事后对照/);
  assert.deepEqual(evidence,before);assert.match(html,/原任务 AI 内容/);
  for(const generated_at of [undefined,null,"unknown","2026-02-30T12:00:00Z",Infinity]) {
    const unknown=journal.detailHtml(detail({task_configuration:{ai_evidence:{generated_at,content:"原文"}}}));
    assert.match(unknown,/AI 参考生成日期未知/);assert.match(unknown,/无法确认它在声明截止日之前已经存在/);
    assert.ok(!unknown.includes("该 AI 参考生成于声明截止日之后"));
  }
  const earlier=journal.detailHtml(detail({task_configuration:{ai_evidence:{generated_at:"2026-05-01T08:00:00+08:00"}}}));
  assert.match(earlier,/生成日期（UTC）：2026-05-01/);assert.ok(!earlier.includes("生成于声明截止日之后"));
});

function service() {
  let stored=null,serial=0;const calls=[];
  const api=async(resource)=>{calls.push(["read",resource]);if(resource==="terminal_judgments")return {items:stored?[clone(stored)]:[],warnings:[]};
    if(resource==="terminal_judgments/"+ID)return clone(stored);
    if(resource==="terminal_inputs/"+INPUT)return input();
    if(resource==="terminal_judgment_replay/"+ID)return {available:true,source:"JUDGMENT_FROZEN_INPUT",judgment_id:ID,record_hash:ID,input_id:INPUT,
      as_of:stored.as_of,symbol:"AAPL",meta:input().meta,rows:[row()],trades:[]};
    throw new Error("unexpected resource "+resource);};
  const perform=async(action,payload,options={})=>{calls.push(["write",action,clone(payload)]);
    if(options.button?.disabled)return undefined;
    if(action==="terminal_save_judgment")stored=detail({...payload,id:ID,judgment_id:ID});
    else if(action==="terminal_append_judgment_event") {
      assert.equal(payload.expected_head,stored.head);
      stored={...stored,head:String(++serial).repeat(64),event_count:stored.event_count+1,
        events:[...stored.events,{...payload,created_at:"2026-10-21T02:10:00Z",action_verification:payload.event_type==="USER_ACTION"?"USER_REPORTED_UNVERIFIED":undefined}]};
    } else throw new Error("unexpected write "+action);
    await options.onSuccess?.(clone(stored));return clone(stored);};
  return {api,perform,calls,get:()=>clone(stored),set:(value)=>{stored=clone(value);}};
}

test("create, append all four event kinds, refresh and reopen use durable reads without trading",async()=>{
  const backend=service();let next=0;const c=journal.createController({...backend,uuid:()=>"request-"+(++next)});
  c.begin(context());await c.save(fields(),{disabled:true});
  assert.equal(c.state.detail.thesis,fields().thesis);
  for(const event_type of ["OBSERVATION","TRIGGERED","INVALIDATED","USER_ACTION"])
    await c.append({event_type,as_of:"2026-06-15",note:event_type+" note"});
  const reopened=journal.createController({...backend,uuid:()=>"reopened"});await reopened.refresh();await reopened.open(ID);
  assert.equal(reopened.state.detail.events.length,4);assert.equal(reopened.state.detail.as_of,"2026-06-13");
  assert.equal(reopened.state.detail.events.at(-1).action_verification,"USER_REPORTED_UNVERIFIED");
  assert.ok(backend.calls.filter(([kind])=>kind==="write").every(([,action])=>["terminal_save_judgment","terminal_append_judgment_event"].includes(action)));
  assert.equal(backend.calls.filter(([kind])=>kind==="write").length,5);
});

test("unknown create does not retry and clears only after its precise receipt is read",async()=>{
  const backend=service();let writes=0;const c=journal.createController({api:backend.api,uuid:()=>"uncertain-create",
    perform:async()=>{writes++;return null;}});
  c.begin(context());assert.equal(await c.save(fields()),null);assert.equal(c.state.unknown,true);
  await c.refresh();assert.equal(c.state.unknown,true);
  await assert.rejects(()=>c.save(fields()),/待核对/);assert.equal(writes,1);
  backend.set(detail({client_request_id:"different"}));await c.refresh();assert.equal(c.state.unknown,true);
  backend.set(detail({client_request_id:"uncertain-create",status:"UNKNOWN"}));await c.refresh();assert.equal(c.state.unknown,true);
  backend.set(detail({client_request_id:"uncertain-create"}));await c.refresh();
  assert.equal(c.state.unknown,false);assert.equal(c.state.context,null);assert.equal(c.state.selectedId,ID);assert.equal(writes,1);
});

test("unknown event reconciles by event request id, never by a changed head alone",async()=>{
  const backend=service();backend.set(detail());const c=journal.createController({api:backend.api,uuid:()=>"uncertain-event",perform:async()=>null});
  await c.open(ID);await c.append({event_type:"OBSERVATION",as_of:"2026-06-15",note:"观察"});
  backend.set(detail({head:"f".repeat(64),events:[{client_request_id:"different"}]}));await c.refresh();assert.equal(c.state.unknown,true);
  backend.set(detail({head:"f".repeat(64),events:[{client_request_id:"uncertain-event"}]}));await c.refresh();assert.equal(c.state.unknown,false);
});

test("a late detail response cannot replace the latest selection; read errors remain unknown",async()=>{
  let resolveFirst;const second="f".repeat(64);
  const c=journal.createController({uuid:()=>"x",perform:async()=>null,api:async(resource)=>resource.endsWith(ID)
    ?new Promise(resolve=>{resolveFirst=resolve;}):detail({id:second,judgment_id:second})});
  const first=c.open(ID);await c.open(second);resolveFirst(detail());await first;
  assert.equal(c.state.selectedId,second);assert.equal(c.state.detail.judgment_id,second);
  const failed=journal.createController({uuid:()=>"x",perform:async()=>null,api:async()=>{throw new Error("input_missing");}});
  await failed.open(ID);assert.equal(failed.state.detail.integrity_status,"UNKNOWN");assert.match(journal.detailHtml(failed.state.detail),/不可复盘/);
});

function fakeDocument() {
  const map=new Map();
  class Element {
    constructor(tag){this.tagName=tag;this.ownerDocument=document;this.listeners={};this.dataset={};this.hidden=false;this.disabled=false;this.value="";this.children=[];}
    set id(value){this._id=value;map.set(value,this);}get id(){return this._id;}
    set innerHTML(value){this.html=value;for(const match of value.matchAll(/<([a-z][\w-]*)\b([^>]*\bid="([^"]+)"[^>]*)>/g)){
      const child=new Element(match[1]);child.id=match[3];child.value=/\bvalue="([^"]*)"/.exec(match[2])?.[1]||"";}}
    get innerHTML(){return this.html||"";}
    querySelector(selector){return map.get(selector.replace(/^#/,""))||null;}
    setAttribute(name,value){this[name]=value;}append(...children){this.children.push(...children);}after(child){this.children.push(child);}
    addEventListener(type,callback){this.listeners[type]=callback;}focus(){document.focused=this.id;}scrollIntoView(){}reset(){}reportValidity(){return true;}
  }
  const document={createElement:(tag)=>new Element(tag),focused:null};document.head=new Element("head");
  const host=new Element("main");return {document,host,get:(id)=>map.get(id)};
}

test("mounted controls save and reopen a historical judgment, append and send only verified frozen input",async()=>{
  const dom=fakeDocument(),backend=service(),replays=[];
  const mounted=journal.install({host:dom.host,...backend,notify(){},validReplay:protocol.validReplay,sendReplay:(value)=>replays.push(value)});
  mounted.setSources({inputs:[input()]});await mounted.refresh();await mounted.openSource("terminal_input",INPUT);
  assert.equal(dom.get("tj-as-of").min,"2026-01-02");assert.equal(dom.get("tj-as-of").max,"2026-10-01");
  const values={"tj-direction":"WAIT","tj-as-of":"2026-06-13","tj-thesis":"等待确认","tj-trigger":"突破前高","tj-invalidation":"跌破低点","tj-counter":"成交量不足"};
  for(const [id,value]of Object.entries(values))dom.get(id).value=value;
  const section=dom.get("terminalJudgmentWorkspace");
  await section.listeners.submit({target:dom.get("tj-create-form"),submitter:dom.get("tj-create-submit"),preventDefault(){}});
  assert.equal(backend.get().as_of,"2026-06-13");assert.match(dom.get("tj-detail").innerHTML,/等待确认/);
  dom.get("tj-event-type").value="USER_ACTION";dom.get("tj-event-date").value="2026-06-15";dom.get("tj-event-note").value="用户报告减仓";
  await section.listeners.submit({target:dom.get("tj-event-form"),submitter:dom.get("tj-event-submit"),preventDefault(){}});
  assert.equal(backend.get().events.length,1);assert.match(dom.get("tj-detail").innerHTML,/未核验成交/);
  await mounted.refresh();assert.match(dom.get("tj-detail").innerHTML,/用户报告减仓/);
  await section.listeners.click({target:{closest:()=>({dataset:{tjAction:"replay"},disabled:false})}});
  assert.equal(replays.length,1);assert.equal(replays[0].source,"JUDGMENT_FROZEN_INPUT");assert.deepEqual(replays[0].trades,[]);
  assert.equal(replays[0].run_id,undefined);
});

test("unavailable replay leaves the original chart untouched and explains the missing source",async()=>{
  const dom=fakeDocument(),backend=service(),replays=[];backend.set(detail());
  const mounted=journal.install({host:dom.host,perform:backend.perform,notify(){},validReplay:protocol.validReplay,sendReplay:(value)=>replays.push(value),
    api:async(resource)=>resource.startsWith("terminal_judgment_replay/")?{available:false,judgment_id:ID,reason:"冻结输入校验失败"}:backend.api(resource)});
  mounted.setSources({inputs:[input()]});await mounted.refresh();const section=dom.get("terminalJudgmentWorkspace");
  await section.listeners.click({target:{closest:()=>({dataset:{tjAction:"open",tjId:ID},disabled:false})}});
  await section.listeners.click({target:{closest:()=>({dataset:{tjAction:"replay"},disabled:false})}});
  assert.equal(replays.length,0);assert.match(dom.get("tj-replay-status").textContent,/不可复盘.*校验失败/);
});
