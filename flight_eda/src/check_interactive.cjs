// Test real application logic against full-data known values without pretending
// that a mocked DOM verifies browser rendering. Run: node src/check_interactive.cjs
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const root=path.resolve(__dirname,'..');
const DATA=JSON.parse(fs.readFileSync(path.join(root,'output/interactive/explorer_data.json'),'utf8'));
const elements={};
for(const k of ['strategy','origin','carrier','month','band','rain','pressure','scope','variables','n','delay','distance','evr','airport-table','sample-note','selection','score-subtitle','score','loading','airport','busy','finding','export'])elements[k]={value:k==='strategy'?'HOTDECK':'all',textContent:'',innerHTML:'',style:{},add(){},addEventListener(){},removeAllListeners(){},on(){}};
const context={DATA,console,document:{getElementById:k=>elements[k],querySelectorAll:()=>[]},window:{},Option:function(t,v){this.text=t;this.value=v},Plotly:{react:async()=>{}},Image:function(){},Promise,JSON,Object,Number,Array,Math,Set};
vm.createContext(context);vm.runInContext(fs.readFileSync(path.join(root,'src/explorer_app.js'),'utf8'),context);
(async()=>{
 const E=context.window.EDA;
 const sums=s=>Object.values(E.aggregate(s)).reduce((a,b)=>({n:a.n+b.n,arr:a.arr+b.arr}),{n:0,arr:0});
 const base={strategy:'HOTDECK',origin:'all',carrier:'all',month:'all',band:'all',rain:'all',pressure:'all',scope:'all',variables:'all'};
 let a=sums(base);assert.equal(a.n,327346);assert(Math.abs(a.arr/a.n-6.89537675731489)<1e-10);
 a=sums({...base,strategy:'CCA'});assert.equal(a.n,291140);assert(Math.abs(a.arr/a.n-4.759624235762863)<1e-10);
 a=sums({...base,rain:'rain',pressure:'missing'});assert.equal(a.n,11915);assert(Math.abs(a.arr/a.n-39.1797733948804)<1e-10);
 assert.equal(sums({...base,carrier:'UA'}).n,57782);
 for(let i=0;i<6;i++)await E.preset(i);
 assert.equal(elements.origin.value,'LGA');assert.equal(elements.scope.value,'airport');
 assert(elements['score-subtitle'].textContent.includes('LGA 機場模型'));
 const m=E.modelFor({...base,origin:'LGA',scope:'airport'});assert.equal(m.n,101140);
 const point=DATA.points.find(p=>p.ok);const sc=E.project(point.raw,DATA.models.CCA.all);assert(sc.every(Number.isFinite));
 assert.equal(sums({...base,strategy:'CCA',pressure:'missing'}).n,0);
 const result={passed:true,checks:['full-data HOTDECK summary','CCA summary','rain-and-missing intersection','UA subgroup','six presets','LGA model scope','finite PCA projection','empty subgroup'],browser_visual_qa:false};
 fs.writeFileSync(path.join(root,'output/interactive_logic_validation.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
})().catch(e=>{console.error(e);process.exit(1)});
