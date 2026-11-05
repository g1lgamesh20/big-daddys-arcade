const reset=document.querySelector('#reset');reset.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));let deferredPrompt;window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();deferredPrompt=event;document.querySelector('#install').hidden=false});document.querySelector('#install').addEventListener('click',async()=>{if(!deferredPrompt)return;deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;document.querySelector('#install').hidden=true});if('serviceWorker' in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));
const leadersDialog=document.querySelector('#leaders-dialog'),leadersOpen=document.querySelector('#leaders-open'),leadersClose=document.querySelector('#leaders-close'),leadersAll=document.querySelector('#leaders-all');
let lastLeadersFocus=null;
function openLeaders(){lastLeadersFocus=document.activeElement;leadersDialog.hidden=false;document.body.classList.add('leaders-dialog-open');leadersClose.focus()}
function closeLeaders(){leadersDialog.hidden=true;document.body.classList.remove('leaders-dialog-open');if(lastLeadersFocus&&lastLeadersFocus.focus)lastLeadersFocus.focus()}
leadersOpen.addEventListener('click',openLeaders);leadersClose.addEventListener('click',closeLeaders);
leadersDialog.addEventListener('click',e=>{if(e.target===leadersDialog)closeLeaders()});
document.addEventListener('keydown',e=>{if(leadersDialog.hidden)return;if(e.key==='Escape')closeLeaders();if(e.key==='Tab'){const items=[...leadersDialog.querySelectorAll('button:not([disabled]),a[href]')];if(!items.length)return;const first=items[0],last=items[items.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}});
(async function initLegends(){
 const panel=document.querySelector('#legend-spotlight'),controls=document.querySelector('#legend-controls'),counter=document.querySelector('#legend-counter'),source=document.querySelector('#legend-source');
 let entries=[],position=0,updatedAt=null;
 function show(){if(!entries.length)return;const e=entries[position];panel.replaceChildren();const label=document.createElement('p');label.className='legend-kind';label.textContent=e.kind==='recent'?'RECENT SCORE':'GAME CHAMPION';const h=document.createElement('p');h.className='legend-headline';h.textContent=String(e.player).toUpperCase();const g=document.createElement('p');g.className='legend-detail';g.textContent=String(e.game).toUpperCase();const sc=document.createElement('p');sc.className='legend-score';sc.textContent=Number(e.score).toLocaleString('en-US');panel.append(label,h,g,sc);counter.textContent=`${position+1} / ${entries.length}`;}
 function move(delta){position=(position+delta+entries.length)%entries.length;show()}
 document.querySelector('#legend-prev').addEventListener('click',()=>move(-1));document.querySelector('#legend-next').addEventListener('click',()=>move(1));
 async function refresh(){try{const response=await fetch('./legends.json?refresh='+Date.now(),{cache:'no-store'});if(!response.ok)throw Error('Unavailable');const data=await response.json();const next=Array.isArray(data.entries)?data.entries.filter(e=>e&&typeof e.player==='string'&&typeof e.game==='string'&&Number.isFinite(Number(e.score))):[];if(!next.length){source.textContent='AWAITING FIRST LIVE SCORE SYNC — SEE iSCORED FOR RECORDS';return}entries=next;position=Math.min(position,entries.length-1);controls.hidden=entries.length<2;updatedAt=data.updated_at;source.textContent=updatedAt?'SCORES SYNCED '+new Date(updatedAt).toLocaleString():'VERIFIED iSCORED SCORE FEED';show();const rankings=document.querySelector('#papa-standings');if(rankings){rankings.replaceChildren();const allStandings=Array.isArray(data.standings)?data.standings.filter(r=>r&&typeof r.player==='string'&&Number.isFinite(Number(r.points))):[];const standings=allStandings.slice(0,5);leadersAll.replaceChildren();allStandings.forEach((r,i)=>{const row=document.createElement('div');row.className='leaders-full-row';const name=document.createElement('span');name.textContent=`${i+1}. ${r.player.toUpperCase()}`;const pts=document.createElement('span');pts.textContent=`${Number(r.points).toLocaleString('en-US')} PTS`;row.append(name,pts);leadersAll.append(row)});standings.forEach((r,i)=>{const line=document.createElement('div');line.className='papa-row';line.textContent=`${i+1}. ${String(r.player).toUpperCase()} — ${Number(r.points).toLocaleString()} PTS`;rankings.append(line)});document.querySelector('#papa-section').hidden=!standings.length;leadersOpen.disabled=!standings.length;}}
 catch(err){source.textContent=entries.length?'PREVIOUSLY SYNCED SCORES — LIVE UPDATE UNAVAILABLE':'SCORE FEED UNAVAILABLE — OPEN iSCORED FOR SCORES';}}
 await refresh();setInterval(()=>{if(!document.hidden&&entries.length>1&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches)move(1)},8000);setInterval(refresh,10*60*1000);
})();

// Read-only medal feed. Push notifications and public reactions are separate future features.
(async function initMedals(){
 const feed=document.querySelector('#medal-feed'),status=document.querySelector('#medal-status');
 if(!feed)return;
 async function refresh(){
  try{
   const response=await fetch('./medals.json?refresh='+Date.now(),{cache:'no-store'});
   if(!response.ok)throw Error('Medal feed not yet generated');
   const data=await response.json();const alerts=Array.isArray(data.alerts)?data.alerts:[];
   feed.replaceChildren();
   if(!alerts.length){const empty=document.createElement('p');empty.className='medal-empty';empty.textContent='THE PODIUM IS READY — WAITING FOR THE NEXT NEW MEDAL!';feed.append(empty)}
   alerts.slice(0,20).forEach(a=>{
    if(!['gold','silver','bronze'].includes(a.medal)||typeof a.player!=='string'||typeof a.game!=='string'||!Number.isFinite(Number(a.score)))return;
    const card=document.createElement('article');card.className='medal-card';
    const icon=document.createElement('span');icon.className='medal-icon';icon.textContent=({gold:'🥇',silver:'🥈',bronze:'🥉'})[a.medal];
    const body=document.createElement('div');
    const label=document.createElement('div');label.className='medal-label';label.textContent=a.medal.toUpperCase()+' • '+a.rank+(a.rank===1?'ST':a.rank===2?'ND':'RD')+' PLACE';
    const player=document.createElement('div');player.className='medal-player';player.textContent=a.player.toUpperCase();
    const game=document.createElement('div');game.className='medal-game';game.textContent=a.game;
    const score=document.createElement('div');score.className='medal-score';score.textContent=Number(a.score).toLocaleString('en-US')+' POINTS';
    body.append(label,player,game,score);card.append(icon,body);feed.append(card);
   });
   status.textContent='NEW TOP-3 GAME SCORES ONLY • SYNCED '+(data.updated_at?new Date(data.updated_at).toLocaleString():'WITH iSCORED');
  }catch(e){status.textContent='MEDAL FEED AWAITING FIRST SYNC';}
 }
 await refresh();setInterval(refresh,10*60*1000);
})();
