#!/usr/bin/env node
// DOM-level regression of the development-only administrator shortcut.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { pathToFileURL } = require('node:url');

class Element {
  constructor(id = '') {
    this.id = id; this.hidden = false; this.style = { display: '', cssText: '',
      setProperty: (key, value) => { this.style[key] = value; } };
    this.children = []; this.handlers = {}; this.isConnected = true;
    this.open = false; this.content = new Element('template-content');
  }
  append(node) { this.children.push(node); node.isConnected = true; }
  remove() { this.isConnected = false; }
  addEventListener(name, fn) { this.handlers[name] = fn; }
  querySelector(id) { return id === '#arcade-developer-control-inner' ? inner : null; }
  scrollIntoView() {}
}
const template = new Element('arcade-developer-template');
const room = new Element('arcade-developer-control');
const inner = new Element('arcade-developer-control-inner');
const panel = new Element('arcade-settings-body');
const elements = { 'arcade-developer-template': template,
  'arcade-developer-control': room,
  'arcade-developer-control-inner': inner };
global.document = {
  getElementById: id => elements[id] || null,
  createElement: () => new Element(),
};
let allowed = false, userPresent = true, calls = 0, unsubscribed = false;
const supabase = {
  auth: {
    getSession: async () => ({ data: { session: userPresent ?
      { access_token: 'mock-token', user: { id: 'mock-user' } } : null } }),
    getUser: async () => ({ data: { user: userPresent ? { id: 'mock-user' } : null } }),
    onAuthStateChange: () => ({ data: { subscription: {
      unsubscribe: () => { unsubscribed = true; },
    } } }),
  },
  rpc: async () => { calls++; return { data: {
    iscored_handle: 'DON', is_admin: allowed }, error: null }; },
};
(async () => {
  const { installAdminControlRoomShortcut } =
    await import(pathToFileURL(require('node:path').resolve('player-pass-admin-shortcut.js')).href);
  const shortcut = await installAdminControlRoomShortcut({ supabase, controlPanel: panel });
  const button = panel.children[0];
  assert.equal(button.hidden, true, 'No shortcut before verified authorization');
  await button.handlers.click();
  assert.equal(room.hidden, true, 'Unauthorized click cannot open room');

  allowed = true;
  await shortcut.refresh();
  assert.equal(button.hidden, false, 'Authorized DON sees shortcut');
  allowed = false; // revoked between visibility check and click
  await button.handlers.click();
  assert.equal(room.hidden, true, 'Revoked administrator cannot open room');
  assert.equal(button.hidden, true, 'Revocation conceals shortcut');

  allowed = true;
  await shortcut.refresh();
  await button.handlers.click();
  assert.equal(inner.open, true, 'Verified administrator can open room');
  userPresent = false;
  await shortcut.refresh();
  assert.equal(room.hidden, true, 'Sign-out closes developer room');
  assert.equal(inner.open, false, 'Sign-out closes inner control');
  assert.ok(calls >= 4, 'Authorization must be checked on refresh and click');
  shortcut.destroy();
  assert.equal(button.isConnected, false, 'Destroy removes shortcut');
  assert.equal(unsubscribed, true, 'Destroy unsubscribes auth listener');
  console.log('Player Pass admin shortcut DOM regression passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
