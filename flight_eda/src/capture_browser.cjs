/* Capture real rendered browser interactions. No screenshots are synthesized.
   Run on a normal desktop: node src/capture_browser.cjs
   Requires playwright or playwright-core plus Chrome. Failure never marks QA passed. */
const fs=require('fs'),path=require('path'),os=require('os'),assert=require('assert');
const {pathToFileURL}=require('url');
const root=path.resolve(__dirname,'..'),out=path.join(root,'output/browser_screenshots');
function playwright(){
 const locations=['playwright','playwright-core',path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright-core')];
 for(const p of locations){try{return require(p)}catch{}}
 throw Error('找不到 Playwright。請先安裝 Node.js，再在此資料夾執行 npm install --no-save playwright，接著 npx playwright install chromium。');
}
function chrome(){
 const explicit=process.env.EDA_CHROME_PATH;if(explicit)return explicit;
 const c=['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome','/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge',
  path.join(os.homedir(),'.cache/puppeteer/chrome/mac_arm-153.0.8010.36/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
  '/usr/bin/google-chrome','/usr/bin/chromium','C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe'];
 return c.find(p=>fs.existsSync(p));
}
async function main(){
 fs.mkdirSync(out,{recursive:true});
 const {chromium}=playwright();const executablePath=chrome();
 const browser=await chromium.launch({headless:true,...(executablePath?{executablePath}:{})});
 const page=await browser.newPage({viewport:{width:1600,height:1280},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const ops=JSON.parse(fs.readFileSync(path.join(root,'output/screenshots/operations.json'),'utf8'));
 const records=[];
 try{
  await page.goto(pathToFileURL(path.join(root,'output/interactive/flight_explorer.html')).href);
  await page.waitForFunction(()=>window.EDA&&document.querySelector('#busy').style.display==='none',{},{timeout:60000});
  for(let i=0;i<6;i++){
   await page.locator(`[data-step="${i}"]`).click();
   await page.evaluate(()=>window.EDA.ready());
   await page.waitForFunction(()=>['score','loading','airport'].every(id=>document.getElementById(id)._fullLayout));
   const state=await page.evaluate(()=>({filters:window.EDA.getState(),n:document.querySelector('#n').textContent,delay:document.querySelector('#delay').textContent,finding:document.querySelector('#finding').textContent}));
   const expectedN=[327346,291140,11915,57782,327346,101140][i];
   assert.equal(Number(state.n.replaceAll(',','')),expectedN,`Step ${i+1} full-data n`);
   if(i===4){
    // Actual mouse rectangle in the current graph, in the documented PCA coordinates.
    const box=await page.evaluate(()=>{const g=document.getElementById('score'),r=g.getBoundingClientRect(),a=g._fullLayout;return{x0:r.x+a.xaxis._offset+a.xaxis.l2p(-4),x1:r.x+a.xaxis._offset+a.xaxis.l2p(4),y0:r.y+a.yaxis._offset+a.yaxis.l2p(8),y1:r.y+a.yaxis._offset+a.yaxis.l2p(2)};});
    await page.mouse.move(box.x0,box.y0);await page.mouse.down();await page.mouse.move(box.x1,box.y1,{steps:25});await page.mouse.up();
    await page.waitForFunction(()=>document.querySelector('#selection').textContent.includes('手動框選的展示樣本'),{},{timeout:10000});
    state.brushSummary=await page.locator('#selection').textContent();
   }
   await page.evaluate(()=>window.scrollTo(0,0));
   const filename=`${String(i+1).padStart(2,'0')}_browser.png`;
   await page.screenshot({path:path.join(out,filename),fullPage:true});
   records.push({step:i+1,image:`output/browser_screenshots/${filename}`,caption:ops[i].caption,operation:ops[i],state,kind:'real_browser_screenshot'});
   console.log('Captured',filename,state.n,state.delay);
  }
  // Both score and loading hover are checked in the actual browser.
  await page.locator('[data-step="0"]').click();await page.evaluate(()=>window.EDA.ready());
  for(const id of ['score','loading']){
   await page.evaluate(id=>Plotly.Fx.hover(document.getElementById(id),[{curveNumber:0,pointNumber:10<document.getElementById(id).data[0].x.length?10:0}]),id);
   await page.waitForFunction(id=>document.querySelector(`#${id} .hoverlayer`).textContent.trim().length>0,id);
   const filename=`hover_${id}.png`;await page.screenshot({path:path.join(out,filename),fullPage:true});
   records.push({step:`hover_${id}`,image:`output/browser_screenshots/${filename}`,caption:id==='score'?'Hover 航班分數，核對機場、航空公司、延誤與距離。':'Hover 負荷量，同時檢查特徵向量係數與相關負荷量。',kind:'real_browser_screenshot',hoverText:await page.locator(`#${id} .hoverlayer`).textContent()});
   await page.evaluate(id=>Plotly.Fx.unhover(document.getElementById(id)),id);
  }
  assert.deepEqual(errors,[],'No browser page errors');
  const record={passed:true,browser_visual_capture:true,browser:browser.version(),captured_at:new Date().toISOString(),screenshot_count:records.length,records,errors};
  fs.writeFileSync(path.join(out,'capture_manifest.json'),JSON.stringify(record,null,2));
  console.log('成功保存 8 張真實瀏覽器截圖。執行 python src/attach_browser_evidence.py 放入 notebook。');
 }finally{await browser.close();}
}
main().catch(e=>{console.error('未完成瀏覽器截圖：',e.message);process.exitCode=1;});
