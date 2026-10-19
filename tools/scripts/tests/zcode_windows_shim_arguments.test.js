const assert = require('node:assert/strict');
const path = require('node:path');
const {mkdtempSync,writeFileSync,existsSync,readFileSync,rmSync}=require('node:fs');
const {tmpdir}=require('node:os');
const {spawnSync}=require('node:child_process');
const {pathToFileURL} = require('node:url');
(async () => {
  const modulePath=path.resolve(__dirname,'../../../skills/zcode-delegate/scripts/relay.mjs');
  const {assertDirectExecutable}=await import(pathToFileURL(modulePath));
  for(const shim of ['C:\\Program Files\\ZCode\\zcode.cmd','zcode.BAT','/tmp/untrusted.cmd']) {
    assert.throws(()=>assertDirectExecutable(shim), /Shell shims.*unsupported/);
  }
  for(const executable of ['C:\\Program Files\\ZCode\\zcode.exe','/reviewed/zcode','/usr/local/bin/node']) {
    assert.doesNotThrow(()=>assertDirectExecutable(executable));
  }
  const directory=mkdtempSync(path.join(tmpdir(),'zcode-shim-refusal-'));
  try {
    const shim=path.join(directory,'zcode.cmd');
    const marker=path.join(directory,'executed');
    const output=path.join(directory,'artifacts');
    writeFileSync(shim,`echo dispatched > "${marker}"`);
    const run=spawnSync(process.execPath,[modulePath,'--zcode-path',shim,'--cd',directory,'--out-dir',output,'--read-only'],{input:'Review only.',encoding:'utf8',timeout:15000});
    assert.equal(run.status,1);
    assert.match(run.stderr,/Shell shims.*unsupported/);
    assert.equal(existsSync(marker),false);
    const receipt=JSON.parse(readFileSync(path.join(output,'result.json'),'utf8'));
    assert.equal(receipt.status,'failed');
    assert.match(receipt.error,/was not dispatched/);
  } finally { rmSync(directory,{recursive:true,force:true}); }
  console.log('Shell shims refused; direct executable paths accepted. No CLI or Windows execution claimed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
