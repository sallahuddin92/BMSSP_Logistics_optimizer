/* Real Chrome/Leaflet, actual prepared OSM snapshot, unmodified production API. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const input=JSON.parse(fs.readFileSync(process.env.ROAD_RESULTS,'utf8'));
 const output=process.env.BROWSER_EVIDENCE;
 const base=process.env.ROAD_BASE||'http://127.0.0.1:8878';
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROME_BINARY||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'});
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{
  const url=route.request().url();
  if(url.startsWith(base))return route.continue();
  if(url.includes('leaflet@1.9.4/dist/leaflet.js'))return route.fulfill({path:require.resolve('leaflet/dist/leaflet.js'),contentType:'application/javascript'});
  if(url.includes('leaflet@1.9.4/dist/leaflet.css'))return route.fulfill({path:require.resolve('leaflet/dist/leaflet.css'),contentType:'text/css'});
  return route.abort(); // Offline basemap; selected real road geometry remains visible.
 });
 await page.addInitScript(()=>window.BMSSP_BACKEND_URL=location.origin);
 await page.goto(base+'/ui/');
 await page.waitForFunction(()=>typeof map!=='undefined' && map);
 await page.selectOption('#engine-select','native_bmssp_2025');
 await page.selectOption('#road-select','osm-fixture:'+input.region);
 await page.waitForTimeout(600);
 const locations=input.browser_locations;
 await page.evaluate(locations=>map.fitBounds(locations.map(p=>[p.lat,p.lon]),{padding:[80,80],animate:false}),locations);
 async function choose(location){
  const point=await page.evaluate(location=>{const p=map.latLngToContainerPoint([location.lat,location.lon]);const r=document.getElementById('map').getBoundingClientRect();return{x:r.left+p.x,y:r.top+p.y};},location);
  const done=page.waitForResponse(r=>r.url().includes('/search-nodes'));
  await page.mouse.click(point.x,point.y);await done;
 }
 await choose(locations[0]);await page.waitForFunction(()=>depot!==null);
 await page.click('#stop-mode');
 await choose(locations[1]);await page.waitForFunction(()=>stops.length===1);
 await choose(locations[2]);await page.waitForFunction(()=>stops.length===2);
 await page.fill('#vehicle-input','2');await page.locator('#vehicle-input').dispatchEvent('change');
 await page.click('#advanced-toggle');await page.check('#enable-capacity');
 await page.fill('#default-capacity','1');await page.fill('#default-demand','1');
 const pending=page.waitForResponse(r=>r.url().endsWith('/vrp'));
 await page.click('#solve-btn');const response=await pending;const data=await response.json();
 assert.equal(response.status(),200);assert.equal(data.status,'FEASIBLE');
 assert.equal(data.selected_engine,'native_bmssp_2025');assert.equal(data.graph_snapshot,input.snapshot_id);
 assert.equal(data.metadata.road_provenance.source.sha256,input.provenance.source.sha256);
 assert.deepEqual(data.locations,locations.map(p=>p.id));
 assert.equal(data.routes.length,2);assert.ok(data.vehicle_loads.every(n=>n<=1));
 assert.ok(data.metadata.native_execution_diagnostics.sources.every(d=>d.implementation==='BMSSP2025Engine::solve'));
 await page.waitForFunction(()=>routeLines.length>0);
 const displayed=await page.evaluate(()=>routeLines.map(line=>line.getLatLngs().map(p=>[p.lat,p.lng])));
 assert.deepEqual(displayed,data.route_geometry_segments.flat());
 assert.ok(displayed.flat().length>data.locations.length);
 assert.deepEqual(errors,[]);
 await page.locator('#results').scrollIntoViewIfNeeded();
 await page.waitForFunction(()=>document.querySelectorAll('.toast').length===0);
 if(output){
  fs.writeFileSync(path.join(output,'road-browser.json'),JSON.stringify({chrome:browser.version(),request:response.request().postDataJSON(),response:data,displayed_geometry:displayed,basemap:'offline: tiles intentionally blocked'},null,2));
  await page.screenshot({path:path.join(output,'road-browser.png'),fullPage:true});
 }
 // Changing dataset must discard all previous stop IDs and route lines.
 await page.selectOption('#road-select','osm-fixture:seremban-medium');
 assert.equal(await page.evaluate(()=>depot),null);assert.equal(await page.evaluate(()=>stops.length),0);
 assert.equal(await page.evaluate(()=>routeLines.length),0);
 console.log('PASS real OSM Chrome/Leaflet routing, capacity, original geometry, identity, dataset change; Chrome '+browser.version());
 await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
