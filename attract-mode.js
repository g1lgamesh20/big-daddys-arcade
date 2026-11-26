/* Hall of Legends Attract Mode Phase 2.
   Read-only from already-rendered public content; never fetch, publish, or award.
   Single 60-second idle clock; independently rotate four arcade display modes. */
(() => {
 'use strict';
 const overlay=document.getElementById('arcade-attract');
 const toggle=document.getElementById('arcade-attract-enabled');
 if(!overlay||!toggle)return;
 const exitButton=document.getElementById('arcade-attract-exit');
 const stages=Array.from(overlay.querySelectorAll('[data-attract-stage]'));
 const board=document.getElementById('attract-crt-rows');
 const medalPlayer=document.getElementById('attract-medal-player');
 const medalGame=document.getElementById('attract-medal-game');
 const medalHeading=document.getElementById('attract-medal-heading');
 const storageKey='big-daddys-arcade-attract-enabled-v1';
 const IDLE_MS=60000, STAGE_MS=8500;
 let enabled=true,idleTimer=null,rotation=null,stageIndex=0,medalIndex=0,priorFocus=null;
 try{enabled=localStorage.getItem(storageKey)!=='false';}catch(_){}
 toggle.checked=enabled;
 function isBlocked(){
  const settings=document.getElementById('arcade-settings-panel');
  const lab=document.getElementById('arcade-test-lab-panel');
  const celebrate=document.getElementById('arcade-celebrate');
  const leaders=document.getElementById('leaders-dialog');
  return Boolean(settings?.open||lab?.open||document.hidden||
   (celebrate&&!celebrate.hidden)||(leaders&&!leaders.hidden)||
   document.activeElement?.matches('input,textarea,select'));
 }
 function refreshCRT(){
  if(!board)return;
  const fragment=document.createDocumentFragment();
  const rows=Array.from(document.querySelectorAll('#leaders-all .leaders-full-row')).slice(0,10);
  rows.forEach((source,i)=>{
   const cells=source.querySelectorAll('button,span');
   if(cells.length<2)return;
   const line=document.createElement('div');
   line.className='attract-crt-row';
   const rank=document.createElement('span');
   rank.className='attract-crt-rank';
   rank.textContent=String(i+1).padStart(2,'0');
   const player=document.createElement('span');
   player.className='attract-crt-player';
   // Name comes from the actual leaderboard row, not an invented sample.
   player.textContent=(cells[0].textContent||'').replace(/^\s*\d+\.\s*/, '').slice(0,48);
   const points=document.createElement('span');
   points.className='attract-crt-points';
   points.textContent=(cells[1].textContent||'').trim();
   line.append(rank,player,points);
   fragment.append(line);
  });
  if(!fragment.childNodes.length){
   const blank=document.createElement('p');blank.className='attract-crt-empty';
   blank.textContent='AWAITING LIVE HALL OF LEGENDS SCORES';
   fragment.append(blank);
  }
  board.replaceChildren(fragment);
 }
 function refreshMedal(){
  const cards=Array.from(document.querySelectorAll('#medal-feed .medal-card'));
  const card=cards.length?cards[medalIndex++%cards.length]:null;
  const player=card?.querySelector('.medal-player')?.textContent?.trim();
  const game=card?.querySelector('.medal-game')?.textContent?.trim();
  const medal=card?.querySelector('.medal-label')?.textContent?.trim();
  if(medalPlayer)medalPlayer.textContent=player||'NEXT LEGEND WANTED';
  if(medalGame)medalGame.textContent=game||'BE THE NEXT PLAYER ON THE PODIUM';
  if(medalHeading)medalHeading.textContent=medal||'GOLD • SILVER • BRONZE';
 }
 function refreshPlayer(){
  const source=document.querySelector('#player-spotlight .player-stat-card');
  const name=document.getElementById('attract-player-name');
  const rank=document.getElementById('attract-player-rank');
  const stats=document.getElementById('attract-player-stats');
  if(!name||!rank||!stats)return;
  name.textContent=source?.querySelector('h3')?.textContent||'AWAITING PLAYER DATA';
  rank.textContent=source?.querySelector('.player-stat-rank')?.textContent||'';
  stats.replaceChildren();
  source?.querySelectorAll('.player-stat-cell')?.forEach(cell=>{
    const item=document.createElement('div');item.className='attract-player-stat';
    const value=document.createElement('strong');value.textContent=cell.querySelector('strong')?.textContent||'';
    const label=document.createElement('span');label.textContent=cell.querySelector('span')?.textContent||'';
    item.append(value,label);stats.append(item);
  });
 }
 let trophyIndex=0;
 function refreshTrophy(){
  // Reuse the verified trophy collection already rendered by player cards.
  // Never display an unverified submission as an earned award.
  const source=document.querySelector('#player-spotlight .player-stat-card');
  const awards=Array.from(source?.querySelectorAll('.player-verified-trophies > div')||[]);
  const entry=awards.length?awards[trophyIndex++%awards.length]:null;
  const name=document.getElementById('attract-trophy-name');
  const player=document.getElementById('attract-trophy-player');
  const detail=document.getElementById('attract-trophy-detail');
  if(name)name.textContent=entry?.querySelector('strong')?.textContent||'NEXT TROPHY AWAITS';
  if(player)player.textContent=entry?(source?.querySelector('h3')?.textContent||'ARCADE LEGEND'):'YOUR NAME COULD BE HERE';
  if(detail)detail.textContent=entry?.querySelector('span')?.textContent||'EARN A VERIFIED ACHIEVEMENT';
 }
 function showStage(){
  if(!stages.length)return;
  const stage=stages[stageIndex++%stages.length];
  if(stage.dataset.attractStage==='crt')refreshCRT();
  if(stage.dataset.attractStage==='medals')refreshMedal();
  if(stage.dataset.attractStage==='player')refreshPlayer();
  if(stage.dataset.attractStage==='trophy')refreshTrophy();
  for(const item of stages)item.hidden=item!==stage;
  overlay.dataset.attractMode=stage.dataset.attractStage;
 }
 function stop(){
  clearInterval(rotation);rotation=null;
  if(overlay.hidden)return;
  overlay.hidden=true;
  if(priorFocus?.isConnected)priorFocus.focus({preventScroll:true});
 }
 function start(){
  if(!enabled||isBlocked()||!overlay.hidden)return;
  priorFocus=document.activeElement;
  stageIndex=0;medalIndex=0;trophyIndex=0;
  overlay.hidden=false;showStage();
  exitButton?.focus({preventScroll:true});
  rotation=setInterval(showStage,STAGE_MS);
 }
 function resetIdle(){
  clearTimeout(idleTimer);
  if(!overlay.hidden)return;
  if(enabled)idleTimer=setTimeout(()=>{
   if(isBlocked()){resetIdle();return;}
   start();
  },IDLE_MS);
 }
 function exit(){stop();resetIdle();}
 toggle.addEventListener('change',()=>{
  enabled=toggle.checked;
  try{localStorage.setItem(storageKey,String(enabled));}catch(_){}
  if(!enabled){clearTimeout(idleTimer);stop();}else resetIdle();
 });
 overlay.addEventListener('pointerdown',exit);
 document.addEventListener('keydown',event=>{
  if(!overlay.hidden){
   if(event.key!=='Tab'){event.preventDefault();exit();}
   return;
  }
  resetIdle();
 },{capture:true});
 ['pointerdown','pointermove','touchstart','scroll'].forEach(event=>
  document.addEventListener(event,()=>{if(overlay.hidden)resetIdle();},{passive:true}));
 document.addEventListener('visibilitychange',()=>{
  if(document.hidden){clearTimeout(idleTimer);stop();}
  else resetIdle();
 });
 resetIdle();
})();
