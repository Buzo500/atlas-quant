// Bounded synthetic reproduction of browser POST + simultaneous browser/API GET.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { performance } = require('node:perf_hooks');
const { assertStateResponse, readActiveRun } = require('./checks.cjs');
const root = path.resolve(__dirname, '../..');
// Playwright resolves its installation path when imported, not at launch time.
process.env.PLAYWRIGHT_BROWSERS_PATH=path.join(root,'var/playwright-browsers');
const { chromium } = require('../../frontend/node_modules/@playwright/test');
const runId = process.argv[2];
const identity = readActiveRun(root, runId);
function check() {
  readActiveRun(root, runId, identity.token);
}
check();
const report = { run_id: runId, started: new Date().toISOString(), timeout_ms: 10000,
  method: '100 POST demo responses raced with browser fetch and APIRequestContext GET; direct backend control GET; original timeouts, no retries',
  samples: [], network_violations: [], success: false };
let browser;
const deadline = setTimeout(() => { void browser?.close(); }, 180000);
async function sample(label, action) {
  const start = performance.now();
  try {
    const value = await action();
    report.samples.push({ label, at: new Date().toISOString(), ms: performance.now()-start, ...value });
    return value;
  } catch (error) {
    report.samples.push({ label, at: new Date().toISOString(), ms: performance.now()-start, error: error.message });
    throw error;
  }
}
async function api(context, port, correlation) {
  return sample(correlation, async () => {
    const response = await context.request.get(`http://127.0.0.1:${port}/api/state`, {
      timeout: 10000, maxRetries: 0, headers: {'x-atlas-diag': correlation},
    });
    try {
      const state = await response.json();
      assertStateResponse(response.status(), state);
      return { status: response.status(), datasets: state.datasets.length };
    } finally {
      await response.dispose();
    }
  });
}
(async()=>{
  try {
    browser=await chromium.launch({headless:true,args:['--disable-background-networking']});
    const context=await browser.newContext({locale:'es-ES',serviceWorkers:'block'});
    await context.route('**/*', async route=>{
      const r=route.request(), u=new URL(r.url());
      if(u.origin!=='http://127.0.0.1:3000' || (r.method()!=='GET' && !(r.method()==='POST'&&u.pathname==='/api/datasets/demo'))) {
        report.network_violations.push(r.method()+' '+u.origin+u.pathname); await route.abort();
      } else await route.continue();
    });
    const page=await context.newPage();
    await page.goto('http://127.0.0.1:3000/');
    await page.getByText('Motor conectado',{exact:true}).waitFor();
    await api(context, 3000, 'preflight-proxy-api');
    for(let i=0;i<100;i++) {
      check();
      const response=page.waitForResponse(r=>r.url().endsWith('/api/datasets/demo')&&r.request().method()==='POST');
      await page.evaluate(index=>{
        window.diagPost=fetch('/api/datasets/demo',{method:'POST',headers:{'Content-Type':'application/json','X-Atlas-Client':'local-v1','X-Atlas-Diag':`case-${index}-post`},body:'{}'}).then(r=>r.json());
      },i);
      assert.equal((await response).status(),200);
      const results=await Promise.allSettled([
        api(context,3000,`case-${i}-proxy-api`),
        api(context,8000,`case-${i}-direct-api`),
        sample(`case-${i}-browser`,async()=>{
          const result=await page.evaluate(async index=>{
            const r=await fetch('/api/state',{headers:{'X-Atlas-Diag':`case-${index}-browser`},signal:AbortSignal.timeout(10000)});
            return {status:r.status,state:await r.json()};
          },i);
          assertStateResponse(result.status, result.state);
          return {status:result.status,datasets:result.state.datasets.length};
        }),
      ]);
      if(results.some(r=>r.status==='rejected')) throw new Error(`Case ${i} had a failed request; recorded without retry.`);
      await page.evaluate(()=>window.diagPost);
      if(i%20===0) console.log(JSON.stringify({iteration:i,requests:report.samples.length}));
    }
    check(); assert.deepEqual(report.network_violations,[]); report.success=true;
  } catch(error) { report.error=error.message; process.exitCode=1; }
  finally {
    clearTimeout(deadline); await browser?.close();
    report.finished=new Date().toISOString();
    const filename=path.join(root,'output/validation',`api-clients-${runId}.json`);
    fs.mkdirSync(path.dirname(filename), {recursive:true});
    fs.writeFileSync(filename,JSON.stringify(report,null,2)+'\n',{flag:'wx'});
    const ordered=report.samples.filter(s=>!s.error).map(s=>s.ms).sort((a,b)=>a-b);
    console.log(JSON.stringify({report:filename,success:report.success,error:report.error,samples:report.samples.length,max_ms:ordered.at(-1)}));
  }
})();
