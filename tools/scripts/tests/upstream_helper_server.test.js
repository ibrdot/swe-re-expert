// SPDX-License-Identifier: MIT
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawnSync } = require('node:child_process');
const { pathToFileURL } = require('node:url');

(async () => {
  const repo = path.resolve(__dirname, '../../..');
  const modulePath = path.join(repo, 'skills/frontend-slides-frontend-slides/scripts/lib/confined-server.mjs');
  const { startDeckServer } = await import(pathToFileURL(modulePath).href);
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'aas-deck-server-'));
  const deck = path.join(tmp, 'deck with spaces');
  fs.mkdirSync(deck);
  fs.writeFileSync(path.join(deck, 'index.html'), 'deck');
  fs.writeFileSync(path.join(deck, 'asset file.txt'), 'asset');
  fs.writeFileSync(path.join(tmp, 'private.txt'), 'PRIVATE_SENTINEL');
  fs.symlinkSync(path.join(tmp, 'private.txt'), path.join(deck, 'outside.txt'));
  fs.symlinkSync(path.join(deck, 'asset file.txt'), path.join(deck, 'inside.txt'));
  const server = await startDeckServer(deck, 'index.html', { '.html': 'text/html' });
  try {
    assert.equal(server.address().address, '127.0.0.1');
    const request = (url, method = 'GET', headers = {}) => new Promise((done, reject) => {
      const req = http.request({ hostname: '127.0.0.1', port: server.address().port, path: url, method, headers }, res => {
        let body = ''; res.setEncoding('utf8'); res.on('data', chunk => { body += chunk; });
        res.on('end', () => done({ status: res.statusCode, body, headers: res.headers }));
      });
      req.on('error', reject); req.end();
    });
    assert.equal((await request('/')).body, 'deck');
    assert.equal((await request('/', 'GET', { Host: 'untrusted.example' })).status, 403);
    assert.equal((await request('/asset%20file.txt?version=1')).body, 'asset');
    assert.equal((await request('/inside.txt')).body, 'asset');
    for (const route of ['/../private.txt', '/%2e%2e/private.txt', '/..%2fprivate.txt', '/outside.txt']) {
      const result = await request(route);
      assert.equal(result.status, 403, route);
      assert.equal(result.body.includes('PRIVATE_SENTINEL'), false, route);
    }
    assert.equal((await request('/bad%zz')).status, 400);
    assert.equal((await request('/%00')).status, 400);
    assert.equal((await request('/missing.txt')).status, 404);
    assert.equal((await request('/', 'POST')).status, 405);
    const head = await request('/', 'HEAD');
    assert.equal(head.status, 200); assert.equal(head.body, '');
    assert.equal(head.headers['x-content-type-options'], 'nosniff');

    const exportScript = path.join(repo, 'skills/frontend-slides-frontend-slides/scripts/export-pdf.sh');
    const project = path.join(tmp, 'project without dependencies');
    const fakeBin = path.join(tmp, 'fake-bin');
    const npmMarker = path.join(tmp, 'npm-was-invoked');
    fs.mkdirSync(project); fs.mkdirSync(fakeBin);
    fs.writeFileSync(path.join(project, 'deck.html'), '<html>deck</html>');
    fs.writeFileSync(path.join(fakeBin, 'npm'), '#!/bin/sh\n: > "$AAS_TEST_NPM_MARKER"\n');
    fs.chmodSync(path.join(fakeBin, 'npm'), 0o755);
    const guarded = spawnSync('bash', [exportScript, path.join(project, 'deck.html'), path.join(project, 'deck.pdf')], {
      cwd: project,
      encoding: 'utf8',
      env: { ...process.env, PATH: `${fakeBin}${path.delimiter}${process.env.PATH}`, AAS_TEST_NPM_MARKER: npmMarker },
    });
    assert.equal(guarded.status, 1, guarded.stdout + guarded.stderr);
    assert.match(guarded.stderr, /Playwright and Chromium must already be installed/);
    assert.equal(fs.existsSync(npmMarker), false, 'the helper must not install packages automatically');
  } finally {
    await new Promise(done => server.close(done));
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  console.log('Upstream deck server confines paths, symlinks, methods and loopback binding.');
})().catch(error => { console.error(error); process.exitCode = 1; });
