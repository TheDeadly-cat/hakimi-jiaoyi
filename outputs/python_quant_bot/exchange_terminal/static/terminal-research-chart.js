/* Causal annotations for frozen research; does not create execution signals. */
(function(root){
  'use strict';
  const RULES={fixed_pct:{label:'固定比例',color:'#f5b642'},atr_trailing:{label:'ATR 移动',color:'#43d7ff'},confirmed_structure:{label:'确认结构',color:'#d6a4ff'}};
  const supported=replay=>['STRUCTURE_FROZEN','EXIT_RESEARCH_FROZEN'].includes(replay?.source);
  function project(replay,end,sampleId){
    if(!supported(replay))return {marks:[],paths:[],samples:[],end:0};
    const cutoff=Math.max(0,Math.min(replay.rows.length,Math.trunc(end)));
    const marks=(replay.structure_marks||[]).filter(mark=>Number.isInteger(mark.confirmed_at_index)&&mark.confirmed_at_index<cutoff);
    const available=(replay.exit_paths||[]).filter(path=>Number.isInteger(path.entry?.index)&&path.entry.index<cutoff);
    const samples=[...new Map(available.map(path=>[path.sample_id,{id:path.sample_id,entry:path.entry}])).values()];
    const selected=samples.find(sample=>sample.id===sampleId)?.id||samples[0]?.id;
    const paths=available.filter(path=>path.sample_id===selected).map(path=>{
      const exit=path.exit&&path.exit.index<cutoff?path.exit:null;
      const censor=path.censor&&path.censor.index<cutoff?path.censor:null;
      return {...path,exit,censor,reason:exit||censor||path.status==='UNAVAILABLE'?path.reason:null,
        status:exit?'EXITED':censor?'CENSORED':path.status==='UNAVAILABLE'?'UNAVAILABLE':'OBSERVING',
        threshold_trace:(path.threshold_trace||[]).filter(point=>point.index<cutoff&&point.known_at_index<=point.index)};
    });
    return {marks,paths,samples,selected,end:cutoff};
  }
  let replayValue=null,selected=null,lastUiKey=null,changeCutoff=()=>{},redraw=()=>{};
  function configure(replay,callbacks={}){
    replayValue=replay;selected=null;lastUiKey=null;changeCutoff=callbacks.cutoff||(()=>{});redraw=callbacks.redraw||(()=>{});
    const host=root.document?.getElementById('terminalResearchChartControls');
    if(!host)return;
    host.hidden=!supported(replay);
    if(host.hidden)return;
    if(!host.dataset.installed){
      host.innerHTML='<div class="research-chart-controls"><label>观察截止位置 <input id="researchChartCutoff" type="range" min="1" step="1" aria-label="结构回放截止位置"></label><label id="researchChartSampleLabel">入场样本 <select id="researchChartSample" aria-label="出场比较入场样本"></select></label><button type="button" id="researchChartLatest">查看全部冻结区间</button></div><p id="researchChartProgress" role="status"></p><p>结构在确认后才显示；标注位置为发生日。阈值颜色：橙色固定比例、蓝色 ATR、紫色确认结构。独立样本不表示账户成交或组合收益。</p><details><summary>最近 20 个可知结构：发生日与确认日</summary><table><thead><tr><th>结构</th><th>发生日</th><th>确认日</th><th>价位</th></tr></thead><tbody id="researchStructureRows"></tbody></table></details>';
      host.querySelector('#researchChartCutoff').addEventListener('input',event=>changeCutoff(Number(event.target.value)));
      host.querySelector('#researchChartLatest').addEventListener('click',()=>changeCutoff(replayValue.rows.length,{fitAll:true}));
      host.querySelector('#researchChartSample').addEventListener('change',event=>{selected=event.target.value;redraw();});
      host.dataset.installed='true';
    }
    host.querySelector('#researchChartCutoff').max=String(replay.rows.length);
    host.querySelector('#researchChartSampleLabel').hidden=replay.source!=='EXIT_RESEARCH_FROZEN';
  }
  function draw(ctx,replay,meta){
    if(!supported(replay)||!meta)return;
    const data=project(replay,meta.end,selected);
    // Keep an explicit sample selection while its entry lies beyond the cutoff.
    // Do not silently display another sample or reveal the future entry details.
    if(selected&&!data.samples.some(sample=>sample.id===selected)){data.selected=null;data.paths=[];}
    else if(!selected)selected=data.selected;
    const {x,y,start,end,pad,chartW,chartH}=meta;
    const canvas=root.document?.getElementById('priceChart');
    if(canvas){canvas.dataset.structureMarkCount=String(data.marks.length);canvas.dataset.researchCutoff=String(data.end);}
    const host=root.document?.getElementById('terminalResearchChartControls');
    const uiKey=String(data.end)+':'+String(selected);
    if(host&&!host.hidden&&lastUiKey!==uiKey){
      lastUiKey=uiKey;
      host.querySelector('#researchChartCutoff').value=String(data.end);
      const select=host.querySelector('#researchChartSample');
      select.replaceChildren(...data.samples.map(sample=>{
        const option=root.document.createElement('option');option.value=sample.id;option.textContent=sample.entry.date+' · 入场 '+sample.entry.price;return option;
      }));
      if(selected&&!data.selected){
        const option=root.document.createElement('option');option.value=selected;option.textContent='所选入场尚未发生';option.disabled=true;select.append(option);
      }
      if(selected)select.value=selected;
      const states=data.paths.map(path=>RULES[path.rule]?.label+'：'+(path.status==='EXITED'?'已退出':path.status==='CENSORED'?'区间／期限截断':path.status==='UNAVAILABLE'?'入场时依据不足':'观察中'));
      host.querySelector('#researchChartProgress').textContent='截至 '+(replay.rows[data.end-1]?.date||'—')+' · 已确认结构 '+data.marks.length+' 个'+(states.length?' · '+states.join(' / '):'');
      host.querySelector('#researchStructureRows').replaceChildren(...data.marks.slice(-20).map(mark=>{
        const tr=root.document.createElement('tr');
        for(const value of [mark.classification||mark.kind,mark.pivot_date||mark.date,mark.confirmed_at_date,mark.price]){
          const td=root.document.createElement('td');td.textContent=String(value);tr.append(td);
        }
        return tr;
      }));
    }
    ctx.save();ctx.beginPath();ctx.rect(pad.left,pad.top,chartW,chartH);ctx.clip();
    const marker=(index,price,label,color,above=true)=>{
      if(index<start||index>=end||!Number.isFinite(price))return;
      const xx=x(index-start),yy=y(price);ctx.fillStyle=color;ctx.strokeStyle=color;ctx.font='10px Segoe UI';
      ctx.beginPath();ctx.arc(xx,yy,3,0,Math.PI*2);ctx.fill();ctx.fillText(label,xx+5,yy+(above?-8:14));
    };
    for(const mark of data.marks){
      marker(mark.type==='PIVOT'?mark.pivot_index:mark.index,mark.price,
        mark.type==='PIVOT'?mark.classification:(mark.kind==='BREAK_UP'?'突破↑':'跌破↓'),
        mark.type==='PIVOT'?'#b8c5dc':'#e3a2d4',mark.kind!=='LOW');
    }
    for(const path of data.paths){
      const rule=RULES[path.rule];if(!rule)continue;
      ctx.strokeStyle=rule.color;ctx.lineWidth=1.7;ctx.setLineDash(path.rule==='fixed_pct'?[5,3]:[]);ctx.beginPath();
      let previous=null;
      for(const point of path.threshold_trace){
        const price=point.effective_threshold??point.threshold;
        if(point.index<start||point.index>=end||!Number.isFinite(price)){previous=null;continue;}
        const xx=x(point.index-start),yy=y(price);
        if(previous&&point.index===previous.index+1){ctx.lineTo(xx,previous.y);ctx.lineTo(xx,yy);}else ctx.moveTo(xx,yy);
        ctx.lineTo(Math.min(pad.left+chartW,xx+Math.max(2,chartW/Math.max(1,end-start-1)/2)),yy);
        previous={index:point.index,y:yy};
      }
      ctx.stroke();ctx.setLineDash([]);
      marker(path.entry.index,path.entry.price,'入场','#ffffff',false);
      if(path.exit)marker(path.exit.index,path.exit.price,rule.label+'退出',rule.color,true);
    }
    ctx.restore();
  }
  root.HakimiResearchChart={project,configure,draw,supported};
  if(typeof module==='object'&&module.exports)module.exports=root.HakimiResearchChart;
})(typeof globalThis==='object'?globalThis:this);
