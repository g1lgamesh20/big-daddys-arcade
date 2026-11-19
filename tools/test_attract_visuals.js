#!/usr/bin/env node
/* Static regression checks: no network and no live-score/notification mutations. */
'use strict';
const fs=require('fs'),assert=require('assert'),vm=require('vm');
const html=fs.readFileSync('index.html','utf8');
const css=fs.readFileSync('attract-visuals.css','utf8');
const controller=fs.readFileSync('attract-mode.js','utf8');
assert(html.includes('ENABLE ATTRACT MODE (AFTER 60 SECONDS)'), 'Approved 60s setting label missing');
assert(controller.includes('IDLE_MS=60000'), 'Idle timer not set to 60s');
assert(html.includes('arcade-attract-scene'), 'Decorative scene missing');
assert(html.includes('aria-hidden="true"><div class="arcade-attract-stars"'), 'Scene must be hidden from accessibility tree');
assert(html.includes('attract-visuals.css?v='), 'Attract CSS not linked');
for(const cls of ['arcade-attract-stars','arcade-attract-horizon','arcade-attract-sweep','arcade-attract-pixels'])assert(css.includes('.'+cls), 'Missing visual '+cls);
assert(css.includes('prefers-reduced-motion:reduce'), 'Reduced-motion fallback missing');
assert(controller.includes('STAGE_MS=8500'), 'Four-screen mode rotation missing');
assert(controller.includes('AWAITING LIVE HALL OF LEGENDS SCORES'), 'Keep no-score fallback');
assert(controller.includes("localStorage.setItem(storageKey,String(enabled))"), 'Preserve enable/disable preference');
// Parse every inline classic script; external/JSON scripts are not modified by this PR.
let count=0;
for(const match of html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)){
  if(/\bsrc\s*=|\btype\s*=\s*["'](?:application\/json|module)["']/.test(match[1]))continue;
  new vm.Script(match[2],{filename:'index.html inline script '+(++count)});
}
new vm.Script(controller,{filename:'attract-mode.js'});
console.log('Attract Mode visuals, 60-second timer, stage loop and JavaScript checks passed ('+count+' inline scripts)');
