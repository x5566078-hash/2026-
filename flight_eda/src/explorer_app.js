'use strict';
const $=id=>document.getElementById(id), COL={EWR:'#237f8c',JFK:'#da8c37',LGA:'#7d63a8'};
const controls=['strategy','origin','carrier','month','band','rain','pressure','scope','variables'];
let state={}, visible=[], selectionPreset=false, activeModel=null, lastUpdate=Promise.resolve();
const number=(n,d=0)=>Number.isFinite(n)?n.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
function reset(){for(const k of controls)$(k).value=k==='strategy'?'HOTDECK':'all';selectionPreset=false;}
function matchPoint(p,s){return(s.strategy!=='CCA'||p.ok)&&(s.origin==='all'||s.origin===p.o)&&(s.carrier==='all'||s.carrier===p.c)&&(s.month==='all'||+s.month===p.m)&&(s.band==='all'||s.band===p.b)&&(s.rain==='all'||s.rain===p.r)&&(s.pressure==='all'||(s.pressure==='missing')===p.p);}
function matchCube(c,s){return c[0]===s.strategy&&(s.origin==='all'||s.origin===c[1])&&(s.carrier==='all'||s.carrier===c[2])&&(s.month==='all'||+s.month===c[3])&&(s.band==='all'||s.band===c[4])&&(s.rain==='all'||s.rain===c[5])&&(s.pressure==='all'||(s.pressure==='missing')===c[6]);}
function aggregate(s){const a=Object.fromEntries(['EWR','JFK','LGA'].map(o=>[o,{n:0,arr:0,dist:0}]));for(const c of DATA.cube)if(matchCube(c,s)){a[c[1]].n+=c[7];a[c[1]].arr+=c[8];a[c[1]].dist+=c[9];}return a;}
function vector(p,s){return s==='CCA'?p.raw:p.raw.slice(0,4).concat(s==='MEAN'?p.mean:p.hot);}
function project(x,model){const z=x.map((v,i)=>(v-model.mean[i])/model.scale[i]);return[0,1].map(k=>z.reduce((v,b,i)=>v+b*model.vectors[i][k],0));}
function getState(){return Object.fromEntries(controls.map(k=>[k,$(k).value]));}
function modelFor(s){return DATA.models[s.strategy][s.scope==='airport'&&s.origin!=='all'?s.origin:'all'];}
async function update(){
 state=getState();activeModel=modelFor(state);const a=aggregate(state),total=Object.values(a).reduce((v,b)=>({n:v.n+b.n,arr:v.arr+b.arr,dist:v.dist+b.dist}),{n:0,arr:0,dist:0});
 $('n').textContent=number(total.n);$('delay').textContent=number(total.n?total.arr/total.n:NaN,2);$('distance').textContent=number(total.n?total.dist/total.n:NaN,0);$('evr').textContent=number(100*(activeModel.evr[0]+activeModel.evr[1]),2)+'%';
 $('score-subtitle').textContent=state.scope==='airport'&&state.origin!=='all'?`${state.origin} 機場模型 · PC1 × PC2`:'固定全體模型 · PC1 × PC2';
 visible=DATA.points.filter(p=>matchPoint(p,state)).map(p=>({p,x:vector(p,state.strategy),z:project(vector(p,state.strategy),activeModel)}));
 const traces=['EWR','JFK','LGA'].map(o=>{const v=visible.filter(r=>r.p.o===o);return{type:'scattergl',mode:'markers',name:o,x:v.map(r=>r.z[0]),y:v.map(r=>r.z[1]),customdata:v.map(r=>[r.p.id,r.p.o,r.p.c,r.p.m,r.p.d,r.x[1],r.x[3],r.p.p?'缺失':'觀測',...r.x]),marker:{color:COL[o],size:5,opacity:.46},hovertemplate:'ID %{customdata[0]} | %{customdata[1]} %{customdata[2]}<br>%{customdata[3]}/%{customdata[4]}<br>抵達延誤 %{customdata[5]:.1f} 分<br>距離 %{customdata[6]:.0f} mi<br>原始氣壓 %{customdata[7]}<br>PC1 %{x:.2f} / PC2 %{y:.2f}<extra></extra>'};});
 const shapes=selectionPreset?[{type:'rect',x0:-4,x1:4,y0:2,y1:8,line:{color:'#da8c37',width:2},fillcolor:'rgba(218,140,55,0.06)'}]:[];
 const layout={template:'plotly_white',paper_bgcolor:'white',plot_bgcolor:'white',font:{family:'Arial, PingFang TC',color:'#153c48'},margin:{t:12,l:62,r:22,b:58},showlegend:false,dragmode:'select',hovermode:'closest',xaxis:{title:'PC1 分數',zerolinecolor:'#dbe5e8',gridcolor:'#edf2f3'},yaxis:{title:'PC2 分數',zerolinecolor:'#dbe5e8',gridcolor:'#edf2f3'},shapes};
 const indices=DATA.variables.map((_,i)=>i).filter(i=>state.variables==='all'||(state.variables==='flight'?i<4:i>=4));
 const lt=[0,1].map(k=>({type:'bar',orientation:'h',name:'PC'+(k+1),y:indices.map(i=>DATA.variables[i]),x:indices.map(i=>activeModel.vectors[i][k]),customdata:indices.map(i=>activeModel.loadings[i][k]),marker:{color:k===0?'#237f8c':'#da8c37'},hovertemplate:'%{y}<br>係數=%{x:.4f}<br>相關負荷量=%{customdata:.4f}<extra>PC'+(k+1)+'</extra>'}));
 const air=['EWR','JFK','LGA'];$('airport-table').innerHTML=air.map(o=>`<tr><td>${o}</td><td>${number(a[o].n)}</td><td>${number(a[o].n?a[o].arr/a[o].n:NaN,2)} 分</td></tr>`).join('');
 $('sample-note').textContent=`目前散布圖顯示固定隨機樣本中的 ${number(visible.length)} 班；上方與機場摘要使用全部 ${number(total.n)} 班。模型 n=${number(activeModel.n)}。`;
 $('selection').textContent='拖曳矩形框選分數圖；手動框選摘要僅限展示樣本。';
 if(selectionPreset){const op=DATA.operations[4];$('selection').textContent=`預設矩形 [-4,4] × [2,8] 的全資料計算：${number(op.n)} 班，平均距離 ${number(op.distance_mean)} 英里，平均抵達延誤 ${number(op.arr_delay_mean,2)} 分。JFK 30,262、EWR 17,215、LGA 0。`;
 }
 await Promise.all([
  Plotly.react('score',traces,layout,{responsive:true,displaylogo:false,modeBarButtonsToRemove:['lasso2d']}),
  Plotly.react('loading',lt,{...layout,shapes:[],dragmode:'zoom',barmode:'group',margin:{t:12,l:105,r:20,b:58},xaxis:{title:'單位特徵向量係數',gridcolor:'#edf2f3'},yaxis:{autorange:'reversed',gridcolor:'#edf2f3'}},{responsive:true,displaylogo:false}),
  Plotly.react('airport',[{type:'bar',x:air,y:air.map(o=>a[o].n?a[o].arr/a[o].n:null),marker:{color:air.map(o=>COL[o])},customdata:air.map(o=>a[o].n),hovertemplate:'%{x}<br>n=%{customdata:,}<br>平均抵達延誤 %{y:.2f} 分<extra></extra>'}],{...layout,shapes:[],dragmode:'zoom',margin:{t:8,l:62,r:18,b:42},xaxis:{},yaxis:{title:'分鐘',gridcolor:'#edf2f3'}},{responsive:true,displaylogo:false})]);
 const score=$('score');score.removeAllListeners('plotly_selected');score.on('plotly_selected',event=>{if(!event||!event.points.length)return;const pts=event.points.filter(p=>p.customdata);if(!pts.length)return;const mean=pts.reduce((v,p)=>v+p.customdata[5],0)/pts.length;const dist=pts.reduce((v,p)=>v+p.customdata[6],0)/pts.length;const counts={};for(const p of pts)counts[p.customdata[1]]=(counts[p.customdata[1]]||0)+1;$('selection').textContent=`手動框選的展示樣本：n=${number(pts.length)}，平均抵達延誤 ${number(mean,2)} 分，平均距離 ${number(dist)} 英里；${JSON.stringify(counts)}。這些不是全資料估計。`;});
 $('busy').style.display='none';
 return{state,total,airports:a,plotN:visible.length};
}
function preset(i){reset();const o=DATA.operations[i];$('strategy').value=o.strategy;$('origin').value=o.origin;$('carrier').value=o.carrier;$('rain').value=o.rain;$('pressure').value=o.pressure;$('scope').value=o.refit?'airport':'all';selectionPreset=i===4;$('finding').textContent=o.caption;lastUpdate=update();return lastUpdate;}
async function exportSnapshot(){await lastUpdate;const urls=await Promise.all(['score','loading'].map(id=>Plotly.toImage($(id),{format:'png',width:900,height:600,scale:1.5})));const imgs=await Promise.all(urls.map(url=>new Promise(resolve=>{const i=new Image();i.onload=()=>resolve(i);i.src=url;})));const cv=document.createElement('canvas');cv.width=1800;cv.height=850;const ctx=cv.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,cv.width,cv.height);ctx.fillStyle='#153c48';ctx.font='bold 32px sans-serif';ctx.fillText('紐約航班：缺失處理 × PCA 操作輸出',35,48);ctx.font='20px sans-serif';ctx.fillText(controls.map(k=>`${k}=${$(k).value}`).join(' | '),35,88);ctx.fillText(`全資料 n=${$('n').textContent} | 平均抵達延誤=${$('delay').textContent} 分 | 平均距離=${$('distance').textContent} mi`,35,125);ctx.drawImage(imgs[0],0,145,900,600);ctx.drawImage(imgs[1],900,145,900,600);ctx.font='18px sans-serif';ctx.fillText('散布圖為固定隨機樣本；模型與篩選摘要使用全資料。圖表快照，非整個瀏覽器畫面。',35,790);const a=document.createElement('a');a.href=cv.toDataURL('image/png');a.download=`flight-pca-${state.strategy}-${state.origin}.png`;a.click();}
for(const c of [...new Set(DATA.points.map(p=>p.c))].sort())$('carrier').add(new Option(c,c));
for(let m=1;m<=12;m++)$('month').add(new Option(m+' 月',m));
for(const k of controls)$(k).addEventListener('change',()=>{selectionPreset=false;$('finding').textContent='檢查樣本數、延誤與負荷量。切換子群時先確認座標系是否重新估計。';lastUpdate=update();});
document.querySelectorAll('[data-step]').forEach(b=>b.addEventListener('click',()=>preset(+b.dataset.step)));
$('export').addEventListener('click',exportSnapshot);
window.EDA={aggregate,matchPoint,project,modelFor,preset,update,getState,ready:()=>lastUpdate};
lastUpdate=update();
