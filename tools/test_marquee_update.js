#!/usr/bin/env node
/* Browser-only marquee update: syntax, sanitized inventory and merge safeguards. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const html=fs.readFileSync('marquee-import.html','utf8');
const js=html.match(/<script>([\s\S]*?)<\/script>/i)?.[1];
assert.ok(js,'Importer script must exist');
new vm.Script(js,{filename:'marquee-import.html'});
const inventory=JSON.parse(fs.readFileSync('marquee-game-inventory.json','utf8')).games;
const mapping=JSON.parse(fs.readFileSync('game-logo-map.json','utf8'));
assert.ok(Object.keys(inventory).length>0,'Game inventory must not be empty');
assert.ok(Object.keys(mapping).length>0,'Existing verified logo map must not be empty');
for(const [id,url] of Object.entries(mapping)){
 assert.match(id,/^\d{1,12}$/,'Logo IDs must be numeric game IDs');
 assert.match(url,/^\/(?:community\/)?images\/games\/game\d+$/,'Existing logos must use safe game image paths');
}
assert.equal(inventory['49994'],'PAC-MAN');
assert.equal(mapping['101601'],'/community/images/games/game2781');
for(const [id,name] of Object.entries(inventory)){
 assert.match(id,/^\d{1,12}$/);
 assert.ok(typeof name==='string'&&name.length>0);
}
class Element{
 constructor(id=''){this.id=id;this.value='';this.disabled=false;this.hidden=false;this.files=[];this.children=[];this.listeners={};this.textContent='';this.firstChild=null;this.href='';this.download='';}
 addEventListener(type,callback){this.listeners[type]=callback;}
 click(){if(this.listeners.click)this.listeners.click();else this.didClick=true;}
 appendChild(child){this.children.push(child);return child;}
 replaceChildren(){this.children=[];}
}
const ids=Object.fromEntries(['records','source-file','status','download','build','report','metrics','details'].map(id=>[id,new Element(id)]));
let savedBlob=null;
const context={
 document:{getElementById:id=>ids[id],createElement:tag=>new Element(tag)},
 fetch:async path=>({ok:true,json:async()=>path.includes('inventory')?{games:inventory}:mapping}),
 Blob:class{constructor(parts){this.parts=parts;savedBlob=this;}},
 URL:{createObjectURL:()=> 'blob:test',revokeObjectURL:()=>{}},
 setTimeout:()=>{},console
};
vm.runInNewContext(js,context);
const settle=()=>new Promise(resolve=>setImmediate(resolve));
(async()=>{
 await settle();
 assert.equal(ids.build.disabled,false);
 ids.records.value=JSON.stringify([
  {gameID:49994,gameName:'PAC-MAN',RoomID:1118,GameLogo:'/community/images/games/game400'},
  {gameID:101601,gameName:'Food Fight',RoomID:1118,GameLogo:'/community/images/games/game2781'},
  {gameID:900001,gameName:'NEW ARCADE GAME',RoomID:1118,GameLogo:'/images/games/game900001'},
  {gameID:900002,gameName:'NO ART YET',RoomID:1118,GameLogo:''}
 ]);
 ids.build.click();
 assert.equal(ids.download.disabled,false,'Valid batch creates package');
 ids.download.click();
 const out=JSON.parse(savedBlob.parts.join(''));
 assert.equal(out.format,'big-daddys-arcade-marquee-update-v1');
 assert.equal(out.summary.new_games,2);
 assert.equal(out.summary.changed_artwork,2);
 assert.equal(out.games['900002'],'NO ART YET');
 assert.equal(out.logos['900001'],'/images/games/game900001');
 assert.equal(out.logos['49994'],'/community/images/games/game400');
 assert.equal(out.logos['101601'],mapping['101601']);
 assert.equal(Object.keys(out.logos).length,Object.keys(mapping).length+1,'Partial import preserves all existing mappings and adds one new logo');
for(const [id,url] of Object.entries(mapping)){
 if(id==='49994')continue; // Intentional artwork replacement in fixture.
 assert.equal(out.logos[id],url,`Existing logo ${id} must be preserved`);
}
 assert.ok(!JSON.stringify(out).includes('"scores"'),'No raw score fields in package');
 ids.records.value=JSON.stringify([{gameID:900003,gameName:'BAD',RoomID:1118,GameLogo:'https://wrong.site/x'}]);
 ids.build.click();
 assert.equal(ids.download.disabled,true,'Reject unsafe URLs');
 console.log('Marquee update page syntax and sanitized diff/merge safeguards passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
