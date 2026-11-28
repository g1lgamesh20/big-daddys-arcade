#!/usr/bin/env node
// Offline Turnstile lifecycle regression with a browser-like stub.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let source = fs.readFileSync('player-pass-turnstile.js', 'utf8')
  .replace('export function createPlayerPassTurnstile', 'function createPlayerPassTurnstile');
source += '\nthis.createPlayerPassTurnstile = createPlayerPassTurnstile;';
let config, resetCount = 0, removeCount = 0;
const widget = { remove() { this.removed = true; } };
const host = { append(node) { this.node = node; } };
const context = {
  document: { createElement: () => widget },
  window: { turnstile: {
    render: (_, options) => { config = options; return 'widget-1'; },
    reset: () => { resetCount++; },
    remove: () => { removeCount++; },
  } },
};
vm.runInNewContext(source, context);
(async () => {
  const provider = context.createPlayerPassTurnstile({ host, siteKey: 'publicSiteKey123' });
  const pending = provider.getTurnstileToken();
  assert.equal(resetCount, 1);
  config.callback('fresh-token');
  assert.equal(await pending, 'fresh-token');
  const next = provider.getTurnstileToken();
  assert.equal(resetCount, 2);
  config['expired-callback']();
  await assert.rejects(next, /expired/);
  const third = provider.getTurnstileToken();
  config.callback('second-token');
  assert.equal(await third, 'second-token');
  provider.destroy();
  assert.equal(removeCount, 1);
  assert.equal(widget.removed, true);
  await assert.rejects(provider.getTurnstileToken(), /unavailable/);
  console.log('Player Pass Turnstile lifecycle regression passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
