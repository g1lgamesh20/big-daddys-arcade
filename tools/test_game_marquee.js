#!/usr/bin/env node
/* No real iScored HTTP requests. Verify only successful off-DOM image loads
   reach the page; alternate image path and stale async results remain safe. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('game-marquee.js','utf8');

function setup(){
  const pending=[];
  class FakeImage{
    constructor(){this.naturalWidth=250;this.naturalHeight=77;pending.push(this);}
    set src(value){this.url=value;}
    get src(){return this.url;}
  }
  const window={};
  vm.runInNewContext(source,{window,Image:FakeImage,WeakMap});
  const children=[];
  const slot={get firstChild(){return children[0]||null;},insertBefore(image){children.unshift(image);}};
  return {load:window.arcadeShowGameMarquee,slot,children,pending};
}
{
  const a=setup();
  a.load(a.slot,'49994','Pac-Man');
  assert.equal(a.children.length,0,'Image must not appear before load completes');
  assert.match(a.pending[0].src,/\/images\/games\/game49994$/);
  a.pending[0].onload();
  assert.equal(a.children.length,1,'Successful image should be displayed once');
}
{
  const a=setup();
  a.load(a.slot,'50032','Game');
  a.pending[0].onerror();
  assert.equal(a.children.length,0,'Failed primary should not flash');
  assert.match(a.pending[1].src,/\/community\/images\/games\/game50032$/);
  a.pending[1].onload();
  assert.equal(a.children.length,1,'Working alternate should appear');
}
{
  const a=setup();
  a.load(a.slot,'50032','Game');
  a.pending[0].onerror();
  a.pending[1].onerror();
  assert.equal(a.children.length,0,'Neither failing URL may show broken art');
}
{
  const a=setup();
  a.load(a.slot,'101601','Old');
  a.load(a.slot,'50042','New');
  a.pending[0].onload();
  assert.equal(a.children.length,0,'Old game cannot render after selection changes');
  a.pending[1].onload();
  assert.equal(a.children.length,1);
  assert.match(a.children[0].src,/game50042$/);
}
{
  const a=setup();
  a.load(a.slot,'49994?x=1','Unsafe');
  assert.equal(a.pending.length,0,'Reject non-numeric IDs');
}
console.log('Game marquee preload, fallback, no-flash, stale-load and ID tests passed.');
