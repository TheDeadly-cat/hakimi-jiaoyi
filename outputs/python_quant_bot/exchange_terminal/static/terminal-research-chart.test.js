'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const chart=require('./terminal-research-chart');
const replay={source:'EXIT_RESEARCH_FROZEN',rows:Array.from({length:12},(_,i)=>({date:String(i)})),
 structure_marks:[{type:'PIVOT',pivot_index:2,confirmed_at_index:5,price:10},{type:'BREAKOUT',index:8,confirmed_at_index:8,price:12}],
 exit_paths:[{sample_id:'a',entry:{index:3,date:'3',price:10},rule:'fixed_pct',status:'EXITED',exit:{index:9,price:8},censor:null,
 threshold_trace:[{index:3,known_at_index:3,threshold:9},{index:4,known_at_index:3,threshold:9},{index:9,known_at_index:8,threshold:9}]},
 {sample_id:'b',entry:{index:10,date:'10',price:14},rule:'fixed_pct',status:'CENSORED',exit:null,censor:{index:11},threshold_trace:[]}]};
test('pivots only appear after confirmation, including when drawn at an earlier origin',()=>{
 assert.equal(chart.project(replay,5).marks.length,0);
 assert.equal(chart.project(replay,6).marks.length,1);
 assert.equal(chart.project(replay,9).marks.length,2);
});
test('future entries, exits, thresholds and outcome status cannot leak into a historical prefix',()=>{
 const early=chart.project(replay,5,'b');
 assert.equal(early.selected,'a');assert.equal(early.samples.length,1);
 assert.equal(early.paths[0].status,'OBSERVING');assert.equal(early.paths[0].exit,null);
 assert.equal(early.paths[0].threshold_trace.length,2);
 assert.equal(chart.project(replay,10).paths[0].status,'EXITED');
 assert.equal(chart.project(replay,11,'b').paths[0].status,'OBSERVING');
 assert.equal(chart.project(replay,12,'b').paths[0].status,'CENSORED');
});
test('ordinary result replay has no new annotations; structure-only replay needs no trades',()=>{
 assert.deepEqual(chart.project({...replay,source:'FROZEN_RUN'},12).marks,[]);
 assert.equal(chart.project({...replay,source:'STRUCTURE_FROZEN',exit_paths:[]},6).marks.length,1);
});
test('show-all requests an explicit viewport fit and preserves an unavailable selected sample across Home',()=>{
 const vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
 const nodes=new Map(),cutoffs=[];let redraws=0;
 const element=()=>({dataset:{},listeners:{},children:[],value:'',textContent:'',hidden:false,
   addEventListener(event,handler){this.listeners[event]=handler;},replaceChildren(...children){this.children=children;},append(child){this.children.push(child);}});
 for(const id of ['terminalResearchChartControls','researchChartCutoff','researchChartLatest','researchChartSample','researchChartSampleLabel','researchChartProgress','researchStructureRows','priceChart'])nodes.set(id,element());
 nodes.get('terminalResearchChartControls').querySelector=selector=>nodes.get(selector.slice(1));
 const context=vm.createContext({document:{getElementById:id=>nodes.get(id),createElement:element}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'terminal-research-chart.js'),'utf8'),context);
 const api=context.HakimiResearchChart;
 api.configure(replay,{cutoff:(...args)=>cutoffs.push(args),redraw:()=>redraws++});
 const noop=()=>{},ctx={save:noop,beginPath:noop,rect:noop,clip:noop,arc:noop,fill:noop,fillText:noop,setLineDash:noop,moveTo:noop,lineTo:noop,stroke:noop,restore:noop};
 const draw=end=>api.draw(ctx,replay,{start:0,end,pad:{left:0,top:0},chartW:120,chartH:100,x:i=>i,y:p=>p});
 draw(12);nodes.get('researchChartSample').listeners.change({target:{value:'b'}});draw(12);
 assert.equal(redraws,1);assert.equal(cutoffs.length,0);assert.equal(nodes.get('researchChartSample').value,'b');
 nodes.get('researchChartCutoff').listeners.input({target:{value:'1'}});draw(1);
 assert.deepEqual(cutoffs[0],[1]);assert.equal(nodes.get('researchChartSample').value,'b');
 assert.deepEqual(nodes.get('researchChartSample').children.map(v=>v.textContent),['所选入场尚未发生']);
 assert.ok(!nodes.get('researchChartProgress').textContent.includes('已退出'));
 nodes.get('researchChartLatest').listeners.click();draw(12);
 assert.equal(cutoffs[1][0],12);assert.equal(cutoffs[1][1].fitAll,true);
 assert.equal(nodes.get('researchChartSample').value,'b');assert.match(nodes.get('researchChartProgress').textContent,/区间／期限截断/);
});
