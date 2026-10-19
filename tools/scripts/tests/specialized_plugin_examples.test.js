const assert = require('assert');
const fs = require('fs');
const path = require('path');
const vm = require('vm');
const { findProjectRoot } = require('../../lib/project-root');
const root = findProjectRoot(__dirname);
const read = id => fs.readFileSync(path.join(root, 'skills', id, 'SKILL.md'), 'utf8');
const blocks = read('api-rate-limit-handler').match(/```typescript\n[\s\S]*?```/g);
// Execute the published function bodies; only erase the two TypeScript signatures.
const delayBody = blocks[0].slice(blocks[0].indexOf(': number {') + ': number '.length, -3);
const retryBody = blocks[1].slice(blocks[1].indexOf('): Promise<Response> {') + '): Promise<Response> '.length, -3);
function fixture(statuses) {
  let now = 1_000_000, calls = 0, released = 0;
  const waits = [];
  const sandbox = {
    Date: class extends Date { static now() { return now; } },
    Math: Object.assign(Object.create(Math), { random: () => 0.5 }),
    console: { warn() {} },
    setTimeout(fn, delay) { waits.push(delay); now += delay; fn(); },
    fetch: async () => {
      const s = statuses[Math.min(calls++, statuses.length - 1)];
      return { ok: s.status === 200, status: s.status, statusText: '',
        headers: new Headers(s.headers), body: { cancel: async () => { released++; } } };
    },
  };
  const api = vm.runInNewContext(`function getRetryDelay(response, attempt, maxDelayMs = 60_000) ${delayBody}\nasync function fetchWithRetry(url, options, maxRetries = 3, maxElapsedMs = 120_000, retryNonIdempotent = false) ${retryBody}\n({getRetryDelay, fetchWithRetry})`, sandbox);
  return { ...api, waits, calls: () => calls, released: () => released };
}
(async () => {
  const f = fixture([{status: 200}]);
  const response = headers => ({ headers: new Headers(headers) });
  assert.strictEqual(f.getRetryDelay(response({}), 0), 500, 'absent reset must use backoff, not zero');
  assert.strictEqual(f.getRetryDelay(response({'x-ratelimit-reset': ''}), 0), 500);
  assert.strictEqual(f.getRetryDelay(response({'Retry-After': '3600'}), 0), 3_600_000, 'do not shorten provider wait');
  assert.strictEqual(f.getRetryDelay(response({'Retry-After': '0'}), 0), 0);
  assert.strictEqual(f.getRetryDelay(response({'Retry-After': new Date(1_010_000).toUTCString()}), 0), 10_000);
  assert.strictEqual(f.getRetryDelay(response({'x-ratelimit-reset': '1010'}), 0), 10_000);
  const budget = fixture([{status: 429, headers: {'Retry-After': '3600'}}]);
  await assert.rejects(budget.fetchWithRetry('fixture', {}), /cannot be scheduled/);
  assert.strictEqual(budget.calls(), 1); assert.deepStrictEqual(budget.waits, []);
  const terminal = fixture([{status: 405}]);
  await assert.rejects(terminal.fetchWithRetry('fixture', {}), /Terminal/);
  assert.strictEqual(terminal.calls(), 1);
  const post = fixture([{status: 503}]);
  await assert.rejects(post.fetchWithRetry('fixture', {method: 'POST'}), /replay safety/);
  assert.strictEqual(post.calls(), 1);
  const zero = fixture([{status: 429, headers: {'Retry-After': '0'}}]);
  await assert.rejects(zero.fetchWithRetry('fixture', {}, 2), /after 2 retries/);
  assert.strictEqual(zero.calls(), 3); assert.deepStrictEqual(zero.waits, [0, 0]);
  const recovered = fixture([{status: 503}, {status: 200}]);
  assert.strictEqual((await recovered.fetchWithRetry('fixture', {})).status, 200);
  assert.strictEqual(recovered.released(), 1);
  // Assert the documented UI check rejects a missing element rather than a truthy Promise.
  const snippet = read('testing-patterns').match(/\/\/ async-appearance-example[^\n]*\n([^\n]+)/)[1];
  const check = new Function('screen', 'expect', `return (async () => { ${snippet} })();`);
  let checked = false;
  const expect = value => ({ toBeTruthy() { assert.ok(value); assert.ok(!(value instanceof Promise)); checked = true; } });
  await check({findByText: async () => ({text: 'Loaded'})}, expect); assert.ok(checked);
  await assert.rejects(check({findByText: async () => { throw new Error('missing'); }}, expect), /missing/);
  console.log('ok');
})().catch(error => { console.error(error); process.exitCode = 1; });
