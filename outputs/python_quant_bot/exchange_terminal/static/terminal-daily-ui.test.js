"use strict";
// Real DOM interactions in a fresh, network-blocked browser context. Requires
// Playwright (NODE_PATH may point at the installed desktop dependency bundle).
// Optional PLAYWRIGHT_BROWSER_EXECUTABLE and DAILY_UI_EVIDENCE_DIR are test-only.
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const {chromium} = require("playwright");
const source = fs.readFileSync(path.join(__dirname,"terminal-daily-ui.js"),"utf8");
const cid = letter => "canon-" + letter.repeat(32);
const common = (kind,letter) => ({id:cid(letter),record_namespace:"canonical-daily-v1",record_resource:"terminal_daily_" + kind});
const security = {security_id:"stock:NDAQ:fixture",symbol:"NDAQ",exchange:"XNAS",currency:"USD",instrument_type:"COMMON_STOCK"};
const intake = () => ({...common("intakes","a"),schema_version:"workbench-stock-intake-v1",status:"REVIEW_REQUIRED",can_save:true,
  intake_id:"check-fixture-check",ref:"stock-intakes/check-fixture-check",check_hash:"1".repeat(64),security,company_name:"Synthetic Nasdaq fixture",
  symbol:"NDAQ",history_sessions:60,coverage_start:"2026-07-01",coverage_end:"2026-10-28",session_count:60,
  source_url:"https://example.invalid/synthetic-source",retrieved_at:"2026-10-29T02:00:00Z",source_truth_verified:false,
  outside_window_actions:[],excluded_forming_sessions:[],saved_input_id:null});
const input = () => ({...common("inputs","b"),kind:"PRICE_SNAPSHOT",input_id:"2".repeat(64),status:"READY",security,
  coverage_start:"2026-07-01",coverage_end:"2026-10-28",sessions:60,price_basis:"RAW_UNADJUSTED",currency:"USD",
  source:{name:"Synthetic source fixture",reference:"https://example.invalid/fixture",retrieved_at:"2026-10-29T02:00:00Z",raw_sha256:"3".repeat(64)},
  calendar_coverage:"SOURCE_BACKED_IMPORTER_DECLARATION_NOT_EXTERNAL_TRUTH",corporate_actions:"ACTION_FREE_FIXED_WINDOW_ONLY",
  source_authentication:"NOT_CRYPTOGRAPHICALLY_AUTHENTICATED"});
const update = (status = "READY") => ({...common("updates","c"),status,display_status:{READY:"NEW_DAILY",REVISION_REVIEW_REQUIRED:"REVISION",UNCHANGED:"UNCHANGED"}[status] || "FAILED",
  symbol:"NDAQ",ref:"updates/check-fixture-update",check_hash:"4".repeat(64),baseline_snapshot_id:"2".repeat(64),baseline_start:"2026-07-01",baseline_end:"2026-10-28",
  latest_completed_session:"2026-10-29",checked_at:"2026-10-30T02:00:00Z",new_dates:status === "UNCHANGED" ? [] : ["2026-10-29"],
  revisions:status === "REVISION_REVIEW_REQUIRED" ? [{date:"2026-10-28",field:"volume",old_value:0,new_value:100}] : [],
  can_freeze:["READY","REVISION_REVIEW_REQUIRED"].includes(status),saved_input_id:null,reason:"SYNTHETIC_FIXTURE"});
let browser;
test.before(async () => {
  const executablePath = [process.env.PLAYWRIGHT_BROWSER_EXECUTABLE,chromium.executablePath(),
    "C:/Program Files/Google/Chrome/Application/chrome.exe","C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe"].find(value => value && fs.existsSync(value));
  browser = await chromium.launch({headless:true,...(executablePath ? {executablePath} : {}),args:["--disable-background-networking","--no-first-run"]});
});
test.after(async () => { await browser?.close(); });
async function mount(t, options = {}) {
  const context = await browser.newContext({viewport:{width:1120,height:900}});
  await context.route("**/*",route => route.abort());
  const page = await context.newPage(), errors = [];
  page.on("pageerror",error => errors.push(error.message));
  page.on("console",message => { if (["error","warning"].includes(message.type())) errors.push(message.text()); });
  t.after(async () => { await context.close(); assert.deepEqual(errors,[],"isolated component has no console/page errors"); });
  await page.setContent('<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Daily data isolated fixture</title><style>body{margin:24px;background:#0c1018;color:#e4e9f2;font:16px/1.6 system-ui}button,input,select{font:inherit;background:#182130;color:inherit;border:1px solid #52637c;border-radius:6px;padding:7px 12px}button:disabled{opacity:.45}.panel{max-width:1060px;margin:auto;padding:20px;border:1px solid #35445a;border-radius:12px}.panel-head,.form-grid,.actions{display:flex;flex-wrap:wrap;align-items:center;gap:16px}.field input,.field select{display:block}.section-note{color:#b1bbcc}h2,h3,h4{margin:12px 0}.primary{background:#1b4e91}a{color:#82b5ff}</style></head><body><main id="host"></main></body></html>');
  await page.addScriptTag({content:source});
  await page.evaluate(({options,fixtures}) => {
    window.records = {inputs:options.inputs || [],intakes:options.intakes || [],updates:options.updates || []};
    window.fixtures = fixtures; window.calls = []; window.reads = []; window.imports = []; window.notices = [];window.gateCalls=[];window.timeline=[];
    window.gate={schema_version:"hakimi-public-daily-access-v1",state:"DISABLED",provider:"Yahoo Finance",scope:"ONE_EXPLICIT_DAILY_CHECK",allowed_actions:[],unconsumed_authorizations:0,actual_attempts:0,requests_in_flight:0,operations_in_flight:0,request_cancellation_supported:false,automatic_retry:false};
    window.failReads = false; window.unknownResult = false; window.afterCallbackThrow = false; window.importResult = {status:"IMPORTED",input_id:"native-independent-id"};
    const api = async (resource,method="GET",payload) => {
      if(method==="GET"){window.reads.push(resource);if(window.failReads)throw Error("synthetic read failure");if(resource==="public-daily-access")return structuredClone(window.gate);return {items:structuredClone(window.records[resource.replace("terminal_daily_","")]),warnings:[]};}
      window.gateCalls.push({resource,method,payload:structuredClone(payload)});window.timeline.push(resource);
      if(resource==="public-daily-access/allow-once"){
        if(window.deferGrant)await new Promise(resolve=>window.releaseGrant=resolve);
        if(window.grantFail)throw Error("单次许可被拒绝（合成测试）");
        Object.assign(window.gate,{state:"AVAILABLE_ONCE",allowed_actions:[payload.action],unconsumed_authorizations:1});
      }else if(resource==="public-daily-access/revoke")Object.assign(window.gate,{state:window.gate.requests_in_flight?"REVOKED_IN_FLIGHT":"DISABLED",allowed_actions:[],unconsumed_authorizations:0});
      else throw Error("unexpected control "+resource);
      return structuredClone(window.gate);
    };
    const perform = async (action,payload,{onSuccess}) => {
      window.calls.push({action,payload:structuredClone(payload)});
      window.timeline.push(action);
      const network=["terminal_daily_check_stock","terminal_daily_check_update"].includes(action);
      if(network&&window.refusedResult){
        Object.assign(window.gate,{state:"DISABLED",allowed_actions:[],unconsumed_authorizations:0});
        const result={status:"PUBLIC_DAILY_REQUEST_REFUSED",error:{code:"PUBLIC_DAILY_PERMISSION_REVOKED",message:"单次许可已撤销"},public_daily_request:{actual_attempts:0,request_in_flight:false,operation_in_flight:false},new_economic_runs:0,automatic_retry:false};onSuccess(result);return result;
      }
      if(network)Object.assign(window.gate,{state:"REQUESTING",unconsumed_authorizations:0,allowed_actions:[],actual_attempts:window.gate.actual_attempts+1,requests_in_flight:1,operations_in_flight:1});
      if (window.deferPerform) await new Promise(resolve => { window.releasePerform = resolve; });
      if(network)Object.assign(window.gate,{state:"DISABLED",requests_in_flight:0,operations_in_flight:0});
      if (window.unknownResult) return null;
      let result;
      if (action === "terminal_daily_check_stock") {
        result = {...structuredClone(window.fixtures.intake),intake_id:"check-" + payload.operation_id,ref:"stock-intakes/check-" + payload.operation_id}; window.records.intakes = [result];
      } else if (action === "terminal_daily_save_stock") {
        result = {...structuredClone(window.fixtures.input),action_status:"STOCK_INPUT_SAVED"}; window.records.inputs = [result]; window.records.intakes[0].saved_input_id = result.id;
      } else if (action === "terminal_daily_check_update") {
        result = {...structuredClone(window.fixtures.update),ref:"updates/check-" + payload.operation_id}; window.records.updates = [result];
      } else if (action === "terminal_daily_freeze_update") {
        result = {...structuredClone(window.fixtures.input),id:"canon-" + "d".repeat(32),input_id:"5".repeat(64),coverage_end:"2026-10-29",action_status:"DAILY_UPDATE_FROZEN"};
        window.records.inputs.push(result); window.records.updates.find(item => item.id === payload.update_id).saved_input_id = result.id;
      } else throw new Error("unexpected action " + action);
      if(network)result.public_daily_request={actual_attempts:1,request_in_flight:false,operation_in_flight:false};
      onSuccess(structuredClone(result));
      if (window.afterCallbackThrow) { window.failReads = true; throw new Error("synthetic post-save global refresh failed"); }
      return result;
    };
    window.ui = window.installTerminalDailyUI({host:document.querySelector("#host"),api,perform,notify:text => window.notices.push(text),allowPublicDataRequest:options.online === true,
      ...(options.importCallback ? {onInputImported:async value => { window.imports.push(value); return window.importResult; }} : {})});
  },{options,fixtures:{intake:intake(),input:input(),update:update()}});
  assert.equal(page.url(),"about:blank"); assert.equal(await page.title(),"Daily data isolated fixture");
  assert.equal(await page.getByRole("heading",{name:"股票日线资料",exact:true}).count(),1);
  await page.evaluate(() => window.ui.reveal());
  return page;
}
const button = (page,name) => page.locator(`[data-do="${name}"]`);
const waitIdle = page => page.waitForFunction(() => document.querySelector(".terminal-daily-ui").getAttribute("aria-busy") === "false");
const select = async (page,kind,id) => { await page.locator(`[data-open="${kind}"][data-id="${id}"]`).click(); };

test("offline reveal and refresh only read saved records, with provider controls disabled",async t => {
  const page = await mount(t,{inputs:[input()],intakes:[intake()]});
  assert.match(await page.locator('[data-role="mode"]').innerText(),/当前离线/);
  assert.equal(await button(page,"check-stock").isDisabled(),true);
  await select(page,"inputs",cid("b")); assert.equal(await button(page,"check-update").isDisabled(),true);
  await page.getByLabel("股票代码",{exact:true}).fill("NDAQ");
  await page.locator("form").dispatchEvent("submit"); await button(page,"refresh").click();
  assert.deepEqual(await page.evaluate(() => window.calls),[]);
  assert.deepEqual([...new Set(await page.evaluate(() => window.reads))].sort(),["public-daily-access","terminal_daily_inputs","terminal_daily_intakes","terminal_daily_updates"]);
  assert.deepEqual(await page.evaluate(()=>window.gateCalls),[]);
  assert.equal(await button(page,"import").isDisabled(),true);
});

test("explicit check, exact security confirmation, save, and optional native import remain separate",async t => {
  const page = await mount(t,{online:true,importCallback:true});
  assert.deepEqual(await page.evaluate(()=>window.gateCalls),[]);assert.match(await page.locator('[data-role="mode"]').innerText(),/Yahoo Finance.*一次/);
  await page.getByLabel("股票代码",{exact:true}).fill("ndaq");assert.equal(await page.getByLabel("历史交易日",{exact:true}).inputValue(),"120");
  await button(page,"check-stock").click(); await page.waitForSelector('[data-role="confirm-wrap"]:not([hidden])'); await waitIdle(page);
  assert.equal(await button(page,"save").isDisabled(),true);
  assert.match(await page.locator('[data-role="intake"]').innerText(),/XNAS/); assert.match(await page.locator('[data-role="intake"]').innerText(),/未获独立认证/);
  assert.equal(await page.locator('[data-role="intake"] dt').filter({hasText:/^价格口径$/}).locator("..").locator("dd").innerText(),"未记录");
  await button(page,"confirm").check(); await button(page,"save").click(); await waitIdle(page);
  assert.match(await page.getByRole("status").innerText(),/行情已保存/);
  const calls = await page.evaluate(() => window.calls);
  assert.equal(calls.length,2); assert.equal(calls[0].payload.symbol,"NDAQ"); assert.equal(calls[0].payload.history_sessions,120);
  const grants=await page.evaluate(()=>window.gateCalls);assert.equal(grants.length,1);assert.equal(grants[0].resource,"public-daily-access/allow-once");assert.equal(grants[0].payload.action,calls[0].action);assert.deepEqual(grants[0].payload.payload,calls[0].payload);
  assert.deepEqual((await page.evaluate(()=>window.timeline)).slice(0,2),["public-daily-access/allow-once","terminal_daily_check_stock"]);
  assert.deepEqual(calls[1].payload.confirmed_security,security); assert.equal(calls[1].payload.intake_id,cid("a"));
  assert.equal(calls[1].payload.expected_check_hash,"1".repeat(64));
  assert.deepEqual(await page.evaluate(() => window.imports),[]);
  await button(page,"import").click(); await waitIdle(page);
  assert.equal((await page.evaluate(() => window.imports))[0].id,cid("b")); assert.equal(await button(page,"import").isDisabled(),true);
  assert.match(await page.getByRole("status").innerText(),/已复用到原策略研究/); assert.equal((await page.evaluate(() => window.calls)).length,2);
  if (process.env.DAILY_UI_EVIDENCE_DIR) { fs.mkdirSync(process.env.DAILY_UI_EVIDENCE_DIR,{recursive:true}); await page.screenshot({path:path.join(process.env.DAILY_UI_EVIDENCE_DIR,"daily-ui-saved-desktop.png"),fullPage:true}); }
});

test("saved success survives a later shared refresh failure and is not retried",async t => {
  const page = await mount(t,{intakes:[intake()]}); await select(page,"intakes",cid("a")); await button(page,"confirm").check();
  await page.evaluate(() => { window.afterCallbackThrow = true; }); await button(page,"save").click(); await waitIdle(page);
  await page.waitForFunction(() => document.querySelector('[data-role="error"]').textContent.includes("读取失败"));
  assert.match(await page.getByRole("status").innerText(),/行情已保存/); assert.doesNotMatch(await page.getByRole("alert").innerText(),/提交结果尚未确认/);
  assert.equal(await button(page,"save").isVisible(),false); assert.match(await page.locator('[data-role="input"]').innerText(),/原始未复权/);
  await button(page,"refresh").click(); assert.equal((await page.evaluate(() => window.calls)).length,1);
});

test("unknown submission blocks repeat actions, while GET recovery uses the original operation identity",async t => {
  const page = await mount(t,{online:true}); await page.evaluate(() => { window.unknownResult = true; });
  await page.getByLabel("股票代码",{exact:true}).fill("NDAQ"); await button(page,"check-stock").click(); await waitIdle(page);
  assert.equal(await button(page,"check-stock").isDisabled(),true); assert.match(await page.getByRole("alert").innerText(),/不要重复提交/);
  await page.locator("form").dispatchEvent("submit"); await button(page,"refresh").click();
  assert.equal((await page.evaluate(() => window.calls)).length,1);
  assert.equal((await page.evaluate(()=>window.gateCalls)).length,1);assert.match(await page.locator('[data-role="access"]').innerText(),/实际外部请求：1 次/);
  await page.evaluate(() => { const op = window.calls[0].payload.operation_id; window.records.intakes = [{...window.fixtures.intake,intake_id:"check-" + op,ref:"stock-intakes/check-" + op}]; });
  await button(page,"refresh").click(); await page.waitForFunction(() => !document.querySelector('[data-do="check-stock"]').disabled);
  assert.equal((await page.evaluate(() => window.calls)).length,1); assert.equal(await button(page,"save").isDisabled(),true);
});

test("saved receipt recovery does not resubmit an uncertain save",async t => {
  const page = await mount(t,{intakes:[intake()]}); await select(page,"intakes",cid("a")); await button(page,"confirm").check();
  await page.evaluate(() => { window.unknownResult = true; }); await button(page,"save").click(); await waitIdle(page);
  assert.equal(await button(page,"save").isDisabled(),true);
  await page.evaluate(() => { window.records.inputs = [window.fixtures.input]; window.records.intakes[0].saved_input_id = window.fixtures.input.id; });
  await button(page,"refresh").click(); await page.waitForFunction(() => document.querySelector('[data-role="status"]').textContent.includes("行情已保存"));
  assert.equal((await page.evaluate(() => window.calls)).length,1); assert.equal(await button(page,"save").isVisible(),false);
});

test("recorded UNKNOWN remains unknown after reread and never enables a second check",async t => {
  const page = await mount(t,{online:true}); await page.evaluate(() => { window.fixtures.intake = {...window.fixtures.intake,status:"UNKNOWN",can_save:false,reason:"SOURCE_OUTCOME_UNKNOWN"}; });
  await page.getByLabel("股票代码",{exact:true}).fill("NDAQ"); await button(page,"check-stock").click(); await waitIdle(page); await button(page,"refresh").click();
  assert.equal(await button(page,"check-stock").isDisabled(),true); assert.equal(await button(page,"save").isVisible(),false);
  assert.match(await page.locator('[data-role="intake"]').innerText(),/结果尚未确认/); assert.equal((await page.evaluate(() => window.calls)).length,1);
});

test("historical revisions require acknowledgment and freeze preserves distinct prior input identity",async t => {
  const page = await mount(t,{inputs:[input()],updates:[update("REVISION_REVIEW_REQUIRED")]}); await select(page,"updates",cid("c"));
  assert.equal(await button(page,"freeze").isDisabled(),true); assert.equal(await page.getByRole("cell",{name:"0",exact:true}).count(),1);
  await button(page,"revisions").check(); await button(page,"freeze").click(); await waitIdle(page);
  const calls = await page.evaluate(() => window.calls); assert.equal(calls.length,1); assert.equal(calls[0].action,"terminal_daily_freeze_update");
  assert.equal(calls[0].payload.acknowledge_revisions,true); assert.equal(calls[0].payload.expected_check_hash,"4".repeat(64));
  assert.deepEqual((await page.evaluate(() => window.records.inputs)).map(row => row.id),[cid("b"),cid("d")]);
  assert.equal(await button(page,"freeze").isVisible(),false); assert.match(await page.getByRole("status").innerText(),/尚未运行策略/);
});

test("UNCHANGED, failed, and new-daily states use actual status and expose only eligible save",async t => {
  for (const status of ["UNCHANGED","BLOCKED","WAITING_SOURCE_UPDATE","CALENDAR_UNAVAILABLE","READY"]) {
    const page = await mount(t,{updates:[update(status)]}); await select(page,"updates",cid("c"));
    assert.equal(await button(page,"freeze").isVisible(),status === "READY",status);
    assert.equal((await page.evaluate(() => window.calls)).length,0);
    if (status === "UNCHANGED") assert.match(await page.locator('[data-role="update"]').innerText(),/不创建新行情、任务版本或回测结果/);
    if (status === "READY") { await button(page,"freeze").click(); await waitIdle(page); assert.equal((await page.evaluate(() => window.calls))[0].payload.acknowledge_revisions,false); }
  }
});

test("explicit update check is the only update request and double submit cannot issue another",async t => {
  const page = await mount(t,{online:true,inputs:[input()]}); await select(page,"inputs",cid("b"));
  assert.equal((await page.evaluate(() => window.calls)).length,0); await page.evaluate(() => { window.deferPerform = true; });
  await button(page,"check-update").click(); await page.waitForFunction(() => typeof window.releasePerform === "function");
  await button(page,"check-update").dispatchEvent("click"); assert.equal((await page.evaluate(() => window.calls)).length,1);
  await page.evaluate(() => window.releasePerform()); await waitIdle(page);
  const calls = await page.evaluate(() => window.calls); assert.equal(calls[0].payload.input_id,cid("b")); assert.equal(calls[0].action,"terminal_daily_check_update");
  assert.equal(await button(page,"freeze").isVisible(),true);
});

test("partial and hostile stored fields stay unrecorded or literal, with mobile layout and import uncertainty",async t => {
  const partial = {...common("inputs","e"),kind:"PRICE_SNAPSHOT",status:"READY",security:{symbol:'<img src=x onerror="window.injection=true">'}};
  const page = await mount(t,{inputs:[partial],importCallback:true}); await page.setViewportSize({width:390,height:844}); await select(page,"inputs",cid("e"));
  assert.equal(await page.locator("img").count(),0); assert.equal(await page.evaluate(() => window.injection),undefined);
  assert.equal(await page.locator('[data-role="input"] dt').filter({hasText:/^币种$/}).locator("..").locator("dd").innerText(),"未记录");
  assert.equal(await page.locator('[data-role="input"] dt').filter({hasText:/^已记录交易日数$/}).locator("..").locator("dd").innerText(),"未记录");
  await page.evaluate(() => { window.importResult = null; }); await button(page,"import").click(); await waitIdle(page);
  assert.equal(await button(page,"import").isDisabled(),true); assert.match(await page.getByRole("alert").innerText(),/复用结果尚未确认/);
  await button(page,"refresh").click(); assert.equal((await page.evaluate(() => window.imports)).length,1);
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),true);
  if (process.env.DAILY_UI_EVIDENCE_DIR) await page.screenshot({path:path.join(process.env.DAILY_UI_EVIDENCE_DIR,"daily-ui-partial-mobile.png"),fullPage:true});
});

test("recorded missing sessions and corporate-action failure are visible without guessing",async t => {
  const missing = {...intake(),status:"BLOCKED",can_save:false,reason:"SOURCE_MISSING_COMPLETED_SESSIONS:2026-10-23,2026-10-26"};
  const failure = {...update("BLOCKED"),stop_detail:{category:"CORPORATE_ACTION",code:"CORPORATE_ACTION_IN_WINDOW",summary:"检查窗口内存在公司行为，当前账务尚不支持处理。",details:{kind:"splits",date:"2026-10-28"}}};
  const page = await mount(t,{intakes:[missing],updates:[failure]}); await select(page,"intakes",cid("a"));
  assert.equal(await page.locator('[data-role="intake"] dt').filter({hasText:/^缺失数据记录$/}).locator("..").locator("dd").innerText(),"2026-10-23,2026-10-26");
  assert.equal(await button(page,"save").isVisible(),false); await select(page,"updates",cid("c"));
  assert.match(await page.locator('[data-role="update"]').innerText(),/当前账务尚不支持处理/); assert.equal(await button(page,"freeze").isVisible(),false);
  assert.equal((await page.evaluate(() => window.calls)).length,0);
});

test("another canonical identity cannot be presented as a completed native import",async t => {
  const page = await mount(t,{inputs:[input()],importCallback:true}); await select(page,"inputs",cid("b"));
  await page.evaluate(() => { window.importResult = {status:"IMPORTED",input_id:"canon-" + "f".repeat(32)}; });
  await button(page,"import").click(); await waitIdle(page);
  assert.match(await page.getByRole("alert").innerText(),/复用结果尚未确认/);
  assert.doesNotMatch(await page.getByRole("status").innerText(),/已复用到原策略研究/);
  assert.equal(await button(page,"import").isDisabled(),true);
});

test("grant failure reports not started and permits a new explicit click without an unknown job",async t=>{
  const page=await mount(t,{online:true});await page.evaluate(()=>window.grantFail=true);
  await page.getByLabel("股票代码",{exact:true}).fill("NDAQ");await button(page,"check-stock").click();await waitIdle(page);
  assert.equal((await page.evaluate(()=>window.calls)).length,0);assert.equal(await button(page,"check-stock").isDisabled(),false);
  assert.match(await page.getByRole("alert").innerText(),/尚未发起行情检查/);assert.doesNotMatch(await page.getByRole("alert").innerText(),/不要重复提交/);
  const original=(await page.evaluate(()=>window.gateCalls))[0].payload.payload.operation_id;
  await page.evaluate(()=>window.grantFail=false);await button(page,"check-stock").click();await waitIdle(page);
  const calls=await page.evaluate(()=>window.calls);assert.equal(calls.length,1);assert.notEqual(calls[0].payload.operation_id,original);
});

test("known queued permission refusal unlocks UI and reports actual zero attempts",async t=>{
  const page=await mount(t,{online:true});await page.evaluate(()=>{window.refusedResult=true;window.gate.actual_attempts=3;});
  await page.getByLabel("股票代码",{exact:true}).fill("NDAQ");await button(page,"check-stock").click();await waitIdle(page);
  assert.equal(await button(page,"check-stock").isDisabled(),false);assert.match(await page.getByRole("alert").innerText(),/实际外部请求 0 次/);
  assert.match(await page.locator('[data-role="access"]').innerText(),/会话实际外部请求：3 次/);assert.match(await page.locator('[data-role="access"]').innerText(),/最近一次检查实际外部请求：0 次/);
  await button(page,"refresh").click();assert.equal((await page.evaluate(()=>window.calls)).length,1);
  assert.equal((await page.evaluate(()=>window.gateCalls)).length,1);assert.equal((await page.evaluate(()=>window.records.intakes)).length,0);
});

test("stop during in-flight fetch blocks later use without claiming cancellation or losing returned record",async t=>{
  const page=await mount(t,{online:true});await page.evaluate(()=>window.deferPerform=true);
  await page.getByLabel("股票代码",{exact:true}).fill("NDAQ");await button(page,"check-stock").click();await page.waitForFunction(()=>typeof window.releasePerform==="function");
  assert.equal(await button(page,"revoke").isDisabled(),false);await button(page,"revoke").click();
  await page.waitForFunction(()=>document.querySelector('[data-role="status"]').textContent.includes("在途请求无法撤销"));
  assert.doesNotMatch(await page.getByRole("status").innerText(),/已取消|已撤销请求/);
  assert.equal(await page.evaluate(()=>window.gate.state),"REVOKED_IN_FLIGHT");assert.equal((await page.evaluate(()=>window.calls)).length,1);
  if(process.env.DAILY_UI_EVIDENCE_DIR){await page.screenshot({path:path.join(process.env.DAILY_UI_EVIDENCE_DIR,"daily-gate-in-flight-desktop.png"),fullPage:true});await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(process.env.DAILY_UI_EVIDENCE_DIR,"daily-gate-in-flight-narrow.png"),fullPage:true});}
  await page.evaluate(()=>window.releasePerform());await waitIdle(page);await page.waitForSelector('[data-role="confirm-wrap"]:not([hidden])');
  assert.equal((await page.evaluate(()=>window.records.intakes)).length,1);assert.equal((await page.evaluate(()=>window.calls)).length,1);
  assert.equal((await page.evaluate(()=>window.gateCalls)).filter(x=>x.resource.endsWith("allow-once")).length,1);
});

test("hiding during a delayed grant revokes its late permission and never submits the job",async t=>{
  const page=await mount(t,{online:true});await page.evaluate(()=>window.deferGrant=true);
  await page.getByLabel("股票代码",{exact:true}).fill("NDAQ");await button(page,"check-stock").click();await page.waitForFunction(()=>typeof window.releaseGrant==="function");
  const noticesBefore=await page.evaluate(()=>window.notices.slice());
  await page.evaluate(()=>window.ui.hide());await page.evaluate(()=>window.releaseGrant());await waitIdle(page);
  assert.deepEqual(await page.evaluate(()=>window.notices),noticesBefore,"hidden cleanup cannot overwrite the host's next-step message");
  assert.equal((await page.evaluate(()=>window.calls)).length,0);assert.equal(await page.evaluate(()=>window.gate.state),"DISABLED");
  const grants=(await page.evaluate(()=>window.gateCalls)).filter(x=>x.resource.endsWith("allow-once"));assert.equal(grants.length,1);
  await page.evaluate(()=>window.ui.reveal());assert.equal(await button(page,"check-stock").isDisabled(),false);
  assert.equal((await page.evaluate(()=>window.gateCalls)).filter(x=>x.resource.endsWith("allow-once")).length,1);
});
