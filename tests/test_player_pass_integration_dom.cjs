#!/usr/bin/env node
// Exercise adapter rollback with stubbed child modules in an isolated VM.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
let source = fs.readFileSync('player-pass-integration.js', 'utf8');
source = source.replace(/^import .*;\s*$/gm, '').replace('export async function mountArcadePlayerPass', 'async function mountArcadePlayerPass');
source += '\nthis.mountArcadePlayerPass = mountArcadePlayerPass;';
class Element {
  constructor() { this.children = []; this.isConnected = true; }
  append(child) { this.children.push(child); child.isConnected = true; }
  remove() { this.isConnected = false; }
}
const panel = new Element();
const nodes = [];
const context = {
  document: {
    querySelector: () => panel,
    getElementById: () => null,
    createElement: () => { const node = new Element(); nodes.push(node); return node; },
  },
  mountOperatorGitHubLogin: () => ({ element: nodes[1], verify: async () => true }),
  mountPlayerPass: () => { const node = new Element(); nodes[0].append(node); return node; },
  installAdminControlRoomShortcut: async () => { throw Error('simulated shortcut failure'); },
};
vm.runInNewContext(source, context);
(async () => {
  await assert.rejects(
    context.mountArcadePlayerPass({
      supabase: { auth: {} }, handles: ['DON'], endpoint: 'https://example.invalid',
      getTurnstileToken: async () => 'mock',
    }),
    /simulated shortcut failure/,
  );
  assert.equal(nodes[0].isConnected, false, 'Failed integration must remove Player Pass host');
  assert.equal(nodes[1].isConnected, false, 'Failed integration must remove login host');
  console.log('Player Pass integration rollback DOM regression passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
