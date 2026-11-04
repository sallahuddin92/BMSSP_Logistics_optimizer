/* Real Chrome + real Leaflet + local deterministic native backend acceptance. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BINARY||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const base=process.env.FIXTURE_BASE||'http://127.0.0.1:8877';
 await page.route('**/*',route=>{
  const url=route.request().url();
  if(url.startsWith(base))return route.continue();
  if(url.includes('leaflet@1.9.4/dist/leaflet.js'))return route.fulfill({path:require.resolve('leaflet/dist/leaflet.js'),contentType:'application/javascript'});
  if(url.includes('leaflet@1.9.4/dist/leaflet.css'))return route.fulfill({path:require.resolve('leaflet/dist/leaflet.css'),contentType:'text/css'});
  return route.abort();
 });
 await page.addInitScript(()=>window.BMSSP_BACKEND_URL=location.origin);
 await page.request.post(base+'/fixture-mode',{data:{mode:'cycle'}});
 await page.goto(base+'/ui/');
 await page.waitForFunction(()=>typeof map!=='undefined' && map);
 await page.selectOption('#engine-select','native_bmssp_2025');
 await page.waitForTimeout(600);
 await page.evaluate(()=>map.setView([3.005,101.005],14,{animate:false}));
 async function choose(lat,lon){
  const p=await page.evaluate(({lat,lon})=>{const p=map.latLngToContainerPoint([lat,lon]);const r=document.getElementById('map').getBoundingClientRect();return{x:r.left+p.x,y:r.top+p.y};},{lat,lon});
  const done=page.waitForResponse(r=>r.url().includes('/search-nodes'));
  await page.mouse.click(p.x,p.y);await done;
 }
 await choose(3,101);
 await page.waitForFunction(()=>depot && depot.node_id==='9007199254740993');
 await page.click('#stop-mode');await choose(3,101.01);
 await page.waitForFunction(()=>stops.length===1);
 await choose(3.01,101.01);await page.waitForFunction(()=>stops.length===2);
 await choose(3.01,101.01);assert.equal(await page.evaluate(()=>stops.length),2);
 await page.locator('#stops-list .remove-btn').last().click();assert.equal(await page.evaluate(()=>stops.length),1);
 await choose(3.01,101.01);await page.waitForFunction(()=>stops.length===2);
 await page.fill('#vehicle-input','2');await page.locator('#vehicle-input').dispatchEvent('change');
 await page.click('#advanced-toggle');await page.check('#enable-capacity');
 await page.fill('#default-capacity','1');await page.fill('#default-demand','1');
 await page.check('#enable-time-windows');await page.fill('#service-duration','1');
 const responsePromise=page.waitForResponse(r=>r.url().endsWith('/vrp'));
 await page.click('#solve-btn');const response=await responsePromise;const data=await response.json();
 assert.equal(data.status,'FEASIBLE');assert.equal(data.selected_engine,'native_bmssp_2025');
 assert.deepEqual(data.locations,['9007199254740993','9007199254740995','9007199254740997']);
 assert.equal(data.routes.length,2);assert.equal(data.duration_units,'seconds');
 await page.waitForFunction(()=>routeLines.length===2);
 const points=await page.evaluate(()=>routeLines.flatMap(line=>line.getLatLngs().map(p=>[p.lat,p.lng])));
 assert.ok(points.some(p=>p[0]===3.002 && p[1]===101.005));
 assert.ok((await page.textContent('#results-content')).includes('native_bmssp_2025'));
 assert.ok((await page.textContent('#results-content')).includes('Stop 1'));
 assert.ok((await page.textContent('#results-content')).includes('Stop 2'));
 await page.locator('#results').scrollIntoViewIfNeeded();
 if(process.env.BROWSER_EVIDENCE)await page.screenshot({path:path.join(process.env.BROWSER_EVIDENCE,'browser-feasible.png')});
 await page.fill('#vehicle-input','1');await page.locator('#vehicle-input').dispatchEvent('change');
 await page.fill('#default-capacity','0');await page.fill('#default-demand','0');
 const zeroResponse=page.waitForResponse(r=>r.url().endsWith('/vrp'));await page.click('#solve-btn');
 const zero=await (await zeroResponse).json();assert.equal(zero.status,'FEASIBLE');assert.equal(zero.vehicle_loads[0],0);
 await page.waitForFunction(()=>!solving);
 // Actual infeasible native solve returns 200: UI must not show a successful route.
 await page.request.post(base+'/fixture-mode',{data:{mode:'oneway'}});
 await page.uncheck('#enable-time-windows');
 const noSolution=page.waitForResponse(r=>r.url().endsWith('/vrp'));await page.click('#solve-btn');
 assert.equal((await (await noSolution).json()).status,'NO_SOLUTION');
 await page.waitForFunction(()=>document.getElementById('results-content').textContent.includes('NO_SOLUTION'));
 assert.equal(await page.evaluate(()=>routeLines.length),0);
 await page.request.post(base+'/fixture-mode',{data:{mode:'failure'}});
 const failed=page.waitForResponse(r=>r.url().endsWith('/vrp'));await page.click('#solve-btn');assert.equal((await failed).status(),500);
 await page.waitForTimeout(100);
 assert.ok(!(await page.textContent('body')).includes('PRIVATE_TEST_SERVER_ERROR'));
 assert.equal(await page.evaluate(()=>routeLines.length),0);
 await page.click('#clear-btn');
 assert.equal(await page.evaluate(()=>depot),null);assert.equal(await page.evaluate(()=>stops.length),0);
 assert.equal(await page.isDisabled('#solve-btn'),true);
 assert.deepEqual(errors,[]);
 if(process.env.BROWSER_EVIDENCE) {fs.writeFileSync(path.join(process.env.BROWSER_EVIDENCE,'browser-response.json'),JSON.stringify(data,null,2));await page.screenshot({path:path.join(process.env.BROWSER_EVIDENCE,'browser.png')});}
 console.log('Chrome version:',browser.version());
 await browser.close();console.log('PASS real Chrome/Leaflet: depot, stops/removal/duplicates, large IDs, vehicles/capacity/time, BMSSP, curved geometry, infeasible 200, failed native, clear');
})().catch(error=>{console.error(error);process.exit(1);});
