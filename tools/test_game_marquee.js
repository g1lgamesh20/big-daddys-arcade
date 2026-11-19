#!/usr/bin/env node
/* Verify iScored GameID -> GameLogo mapping and off-DOM image safety. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('game-marquee.js','utf8');
const mapping=JSON.parse(fs.readFileSync('game-logo-map.json','utf8'));
assert.equal(mapping['49994'],'/images/games/game49994');
assert.equal(mapping['101601'],'/community/images/games/game2781');

function setup(map=mapping){
  const pending=[], requests=[];
  class FakeImage{
    constructor(){this.naturalWidth=250;this.naturalHeight=77;pending.push(this);}
    set src(value){this.url=value;}
    get src(){return this.url;}
  }
  const window={};
  const fetch=(url,options)=>{
    requests.push({url,options});
    return Promise.resolve({ok:true,json:()=>Promise.resolve(map)});
  };
  vm.runInNewContext(source,{window,Image:FakeImage,WeakMap,fetch});
  const children=[];
  const slot={get firstChild(){return children[0]||null;},insertBefore(img){children.unshift(img);}};
  return {load:window.arcadeShowGameMarquee,slot,children,pending,requests};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function run(){
  {
    const a=setup();a.load(a.slot,'49994','Pac-Man');await tick();
    assert.equal(a.pending.length,1);
    assert.equal(a.pending[0].src,'https://www.iscored.info/images/games/game49994');
    assert.equal(a.children.length,0,'No image before successful load');
    a.pending[0].onload();assert.equal(a.children.length,1);
    assert.equal(a.requests.length,1,'Only fetch game map once');
  }
  {
    const a=setup();a.load(a.slot,'101601','Food Fight');await tick();
    assert.equal(a.pending[0].src,'https://www.iscored.info/community/images/games/game2781');
    a.pending[0].onerror();assert.equal(a.children.length,0,'Failed image never appears');
  }
  {
    const a=setup();a.load(a.slot,'50042','Unknown');await tick();
    assert.equal(a.pending.length,0,'No guesses for unmapped games');
  }
  {
    const a=setup();a.load(a.slot,'101601','Old');a.load(a.slot,'49994','New');
    await tick();assert.equal(a.pending.length,1,'Stale map lookup never starts old request');
    assert.match(a.pending[0].src,/game49994$/);
    a.pending[0].onload();assert.equal(a.children.length,1);
  }
  {
    const a=setup({'49994':'https://untrusted.example/logo.png','101601':'/community/images/games/game2781'});
    a.load(a.slot,'49994','Bad');await tick();
    assert.equal(a.pending.length,0,'Reject arbitrary image URLs');
  }
  {
    const a=setup();a.load(a.slot,'101601?bad=true','Unsafe');await tick();
    assert.equal(a.requests.length,0,'Reject malformed game IDs');
  }
  console.log('Verified marquee mapping, unknown fallback, preload, stale-load and URL safety tests passed.');
}
run().catch(err=>{console.error(err);process.exitCode=1;});
