'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs/promises');
const os = require('node:os');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { createHash } = require('node:crypto');
const { spawnSync } = require('node:child_process');
const modulePath = path.resolve(__dirname, '../../../skills/eas-workflows/scripts/fetch.js');
const source = import(pathToFileURL(modulePath).href);
const url = 'https://api.expo.dev/v2/workflows/schema';

async function fixture(t) {
  const cacheDirectory = await fs.mkdtemp(path.join(os.tmpdir(), 'aas-eas-fetch-'));
  t.after(() => fs.rm(cacheDirectory, { recursive: true, force: true }));
  return { cacheDirectory, cacheFile: path.join(cacheDirectory, createHash('sha256').update(url).digest('hex') + '.json') };
}

test('EAS reference helper rejects arbitrary URL before network or cache writes', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory } = await fixture(t);
  let calls = 0;
  for (const target of ['http://127.0.0.1/private', url+'?token=private', 'https://user:pass@api.expo.dev/v2/workflows/schema']) {
    await assert.rejects(fetchCached(target, { cacheDirectory, fetchImpl: async () => { calls++; } }), /documented Expo/);
  }
  assert.equal(calls, 0);
  assert.deepEqual(await fs.readdir(cacheDirectory), []);
});

test('EAS helper bounds timeout options and streamed bytes, leaving no successful cache', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory } = await fixture(t);
  await assert.rejects(fetchCached(url, { cacheDirectory, timeoutMs: 0 }), /Invalid timeout/);
  await assert.rejects(fetchCached(url, { cacheDirectory, maxBytes: 1048577 }), /response limit/);
  await assert.rejects(fetchCached(url, { cacheDirectory, maxBytes: 3, fetchImpl: async () => new Response('too large') }), /byte limit/);
  await assert.rejects(fetchCached(url, { cacheDirectory, maxBytes: 3, fetchImpl: async () => new Response('four', {headers:{'content-length':'4'}}) }), /byte limit/);
  assert.deepEqual(await fs.readdir(cacheDirectory), []);
});

test('EAS helper passes no-redirect policy and aborts a stalled request', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory } = await fixture(t);
  let aborted = false;
  await assert.rejects(fetchCached(url, { cacheDirectory, timeoutMs: 15, fetchImpl: async (_url, options) => {
    assert.equal(options.redirect, 'error');
    return new Promise((_resolve, reject) => options.signal.addEventListener('abort', () => {
      aborted = true; reject(new Error('observed abort'));
    }, {once:true}));
  } }), /observed abort/);
  assert.equal(aborted, true);
  assert.deepEqual(await fs.readdir(cacheDirectory), []);
});

test('EAS helper rejects HTTP errors, empty body and invalid UTF-8 without caching', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory } = await fixture(t);
  for (const response of [new Response('denied',{status:403}), new Response('  '), new Response(new Uint8Array([255]))]) {
    await assert.rejects(fetchCached(url, { cacheDirectory, fetchImpl: async () => response }));
  }
  assert.deepEqual(await fs.readdir(cacheDirectory), []);
});

test('EAS helper caps cache freshness and reuses actual local bytes without another request', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory, cacheFile } = await fixture(t);
  let calls = 0;
  const fetchImpl = async () => { calls++; return new Response('reference text',{headers:{'cache-control':'max-age=999999','etag':'v1'}}); };
  assert.equal(await fetchCached(url, { cacheDirectory, fetchImpl }), 'reference text');
  const cached = JSON.parse(await fs.readFile(cacheFile,'utf8'));
  assert.ok(cached.expires <= Math.floor(Date.now()/1000)+900);
  assert.equal(await fetchCached(url, { cacheDirectory, fetchImpl }), 'reference text');
  assert.equal(calls, 1);
});

test('EAS conditional 304 refresh is bound to prior matching URL and ETag', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory } = await fixture(t);
  await fetchCached(url, { cacheDirectory, fetchImpl: async () => new Response('old',{headers:{'cache-control':'max-age=0','etag':'v1'}}) });
  const data = await fetchCached(url, { cacheDirectory, fetchImpl: async (_url, options) => {
    assert.equal(options.headers['If-None-Match'], 'v1');
    return new Response(null,{status:304,headers:{'cache-control':'max-age=60'}});
  } });
  assert.equal(data, 'old');
});

test('EAS no-store response removes previous bytes and does not leave a new cache', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory, cacheFile } = await fixture(t);
  await fs.writeFile(cacheFile, JSON.stringify({url,expires:0,data:'stale'}));
  assert.equal(await fetchCached(url,{cacheDirectory,fetchImpl:async()=>new Response('fresh',{headers:{'cache-control':'no-store'}})}),'fresh');
  assert.deepEqual(await fs.readdir(cacheDirectory), []);
});

test('EAS cache symlink cannot read or overwrite its external target', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory, cacheFile } = await fixture(t);
  const outside = await fs.mkdtemp(path.join(os.tmpdir(),'aas-eas-outside-'));
  t.after(()=>fs.rm(outside,{recursive:true,force:true}));
  const target=path.join(outside,'private.json');
  const bytes=JSON.stringify({url,expires:Math.floor(Date.now()/1000)+60,data:'external'});
  await fs.writeFile(target,bytes);
  await fs.symlink(target,cacheFile);
  assert.equal(await fetchCached(url,{cacheDirectory,fetchImpl:async()=>new Response('fetched')}),'fetched');
  assert.equal(await fs.readFile(target,'utf8'),bytes);
  assert.equal((await fs.lstat(cacheFile)).isSymbolicLink(),false);
});

test('EAS CLI entrypoint displays help on supported Node without import.meta.main', () => {
  const result=spawnSync(process.execPath,[modulePath,'--help'],{encoding:'utf8'});
  assert.equal(result.status,0);
  assert.match(result.stdout,/Usage: node fetch.js/);
});


test('EAS body deadline also aborts a transfer after headers arrived', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory } = await fixture(t);
  await assert.rejects(fetchCached(url, { cacheDirectory, timeoutMs: 15, fetchImpl: async (_url, options) => {
    const body = new ReadableStream({start(controller) {
      controller.enqueue(new TextEncoder().encode('partial'));
      options.signal.addEventListener('abort', () => controller.error(new Error('body timeout')), {once:true});
    }});
    return new Response(body);
  }}), /body timeout/);
  assert.deepEqual(await fs.readdir(cacheDirectory), []);
});

test('EAS cache root symlink is rejected before any request', async t => {
  const { fetchCached } = await source;
  const { cacheDirectory } = await fixture(t);
  const target=path.join(cacheDirectory,'real');
  const link=path.join(cacheDirectory,'linked');
  await fs.mkdir(target);
  await fs.symlink(target,link);
  let calls=0;
  await assert.rejects(fetchCached(url,{cacheDirectory:link,fetchImpl:async()=>{calls++;return new Response('x');}}), /real directory/);
  assert.equal(calls,0);
  assert.deepEqual(await fs.readdir(target),[]);
});
