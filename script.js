const reset=document.querySelector('#reset');reset.addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));let deferredPrompt;window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();deferredPrompt=event;(()=>{const install=document.querySelector('#install');if(install)install.hidden=false})()});document.querySelector('#install')?.addEventListener('click',async()=>{if(!deferredPrompt)return;deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;const install=document.querySelector('#install');if(install)install.hidden=true});if('serviceWorker' in navigator)window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));
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
    body.append(label,player,game,score);card.append(icon,body);arcadeAttachReactions(card,a);arcadeAttachTrashTalk(card,a);feed.append(card);
   });
   status.textContent='NEW TOP-3 GAME SCORES ONLY • SYNCED '+(data.updated_at?new Date(data.updated_at).toLocaleString():'WITH iSCORED');
  }catch(e){status.textContent='MEDAL FEED AWAITING FIRST SYNC';}
 }
 await refresh();setInterval(refresh,10*60*1000);
})();


/* Medal Club social reactions. All writes go through the secured Edge Function. */
const ARCADE_SOCIAL = Object.freeze({
  base: 'https://jrqzwlowxofnyqpmjgkg.supabase.co/functions/v1',
  anon: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpycXp3bG93eG9mbnlxcG1qZ2tnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTQzMTc2MDYsImV4cCI6MjEwOTg5MzYwNn0.hASh2oQMBrPU7JqEEgKHiB5XYng65-1U_0Ot02PsGyI',
  siteKey: '0x4AAAAAAF7pNMnGbksEUOCw'
});
const ARCADE_CHOICES = [
  ['heart','❤️','LOVE IT'], ['invader','👾','LIKE IT'],
  ['joystick','🕹️','GREAT PLAY'], ['gamepad','🎮','GAME ON!'],
  ['quarter','🪙','GIVE PROPS'], ['trophy','🏆','LEGENDARY'],
  ['poop','💩','DISLIKE'], ['angry','😡','SALTY!']
];
let arcadeSocialDialog = null;
let arcadeSocialWidgetId = null;
let arcadeSocialToken = '';
let arcadeSocialCurrent = null;
let arcadeSocialChoice = 'heart';
let arcadeSocialLastFocus = null;
function arcadeDeviceToken() {
  const k='big-daddys-arcade-device-token-v1';
  try {
    let value=localStorage.getItem(k);
    if(value && /^[a-f0-9]{64}$/.test(value))return value;
    const bytes=new Uint8Array(32);crypto.getRandomValues(bytes);
    value=Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('');
    localStorage.setItem(k,value);return value;
  } catch (_) { throw new Error('Device storage unavailable. Enable browser storage to react.'); }
}
function arcadeAttachReactions(card, achievement) {
  const scoreId=Number(achievement.id);
  if(!Number.isSafeInteger(scoreId)||scoreId<=0)return;
  const wrap=document.createElement('div');wrap.className='arcade-reaction-entry';
  const button=document.createElement('button');button.type='button';button.className='arcade-reaction-trigger';
  button.textContent='❤️ GIVE PROPS';button.setAttribute('aria-label','React to '+achievement.player+' on '+achievement.game);
  const totals=document.createElement('div');totals.className='arcade-reaction-totals';
  totals.setAttribute('aria-label','Public reaction totals');
  totals.dataset.scoreId=String(scoreId);
  wrap.append(button,totals);card.children[1].append(wrap);
  queueMicrotask(()=>arcadeLoadReactionTotals(scoreId,totals));

  let pressTimer=null,wasLong=false,downX=0,downY=0;
  button.addEventListener('pointerdown',e=>{
    if(e.button!==0)return;
    wasLong=false;downX=e.clientX;downY=e.clientY;
    pressTimer=setTimeout(()=>{pressTimer=null;wasLong=true;arcadeOpenSocial(scoreId,achievement,button,true);},550);
  });
  button.addEventListener('pointermove',e=>{if(Math.hypot(e.clientX-downX,e.clientY-downY)>15){clearTimeout(pressTimer);pressTimer=null;}});
  ['pointerup','pointercancel','pointerleave'].forEach(type=>button.addEventListener(type,()=>{clearTimeout(pressTimer);pressTimer=null;}));
  button.addEventListener('click',()=>{if(wasLong){wasLong=false;return;}arcadeOpenSocial(scoreId,achievement,button,false);});
  button.addEventListener('contextmenu',e=>e.preventDefault());
}
async function arcadeLoadReactionTotals(scoreId, target) {
  if(!target?.isConnected)return;
  try {
    const response=await fetch(ARCADE_SOCIAL.base+'/social-arcade?score_id='+scoreId,{
      headers:{apikey:ARCADE_SOCIAL.anon,Authorization:'Bearer '+ARCADE_SOCIAL.anon},
      cache:'no-store'
    });
    if(!response.ok)throw Error('Unable to load reactions');
    const data=await response.json();
    if(!target.isConnected)return;
     arcadeRenderTrashTalk(target.closest('.medal-card'),data.comments,scoreId);
     target.replaceChildren();
    for(const [id,emoji,label] of ARCADE_CHOICES){
      const count=Number(data?.reactions?.[id]||0);
      if(!Number.isFinite(count)||count<=0)continue;
      const item=document.createElement('span');item.className='arcade-reaction-count';
      item.textContent=emoji+' '+count;item.title=label+': '+count;
      item.setAttribute('aria-label',label+': '+count);
      target.append(item);
    }
  }catch(_){if(target.isConnected)target.setAttribute('title','Reaction totals temporarily unavailable');}
}
function arcadeRefreshReactionTotals(scoreId){
  document.querySelectorAll('.medal-card').forEach(card=>{
    const target=card.querySelector('.arcade-reaction-totals');
    if(target&&Number(target.dataset.scoreId)===scoreId)arcadeLoadReactionTotals(scoreId,target);
  });
}
function arcadeBuildSocialDialog() {
  if(arcadeSocialDialog)return arcadeSocialDialog;
  const dialog=document.createElement('div');dialog.id='arcade-social-overlay';dialog.className='arcade-social-overlay';dialog.hidden=true;
  dialog.setAttribute('role','dialog');dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-label','Arcade reactions');
  dialog.innerHTML=`<div class="arcade-social-panel">
    <button type="button" id="arcade-social-close" class="arcade-social-close" aria-label="Close reactions">✕</button>
    <h2>👾 GIVE PROPS!</h2><p id="arcade-social-heading"></p>
    <div id="arcade-social-choices" class="arcade-social-choices"></div>
    <label class="arcade-social-label" for="arcade-social-initials">YOUR INITIALS (1–3)</label>
    <input id="arcade-social-initials" maxlength="3" autocomplete="off" placeholder="DON" aria-label="Your arcade initials">
    <div id="arcade-social-captcha" class="arcade-social-captcha"></div>
    <p id="arcade-social-status" class="arcade-social-status" role="status" aria-live="polite"></p>
    <div class="arcade-social-actions"><button type="button" id="arcade-social-save">🪙 SEND REACTION</button>
    <button type="button" id="arcade-social-remove">UNDO MY REACTION</button></div>
    <p class="arcade-social-small">One reaction per device per score. Change or undo anytime.</p>
  </div>`;
  document.body.append(dialog);
  dialog.querySelector('#arcade-social-close').addEventListener('click',arcadeCloseSocial);
  dialog.addEventListener('click',e=>{if(e.target===dialog)arcadeCloseSocial();});
  document.addEventListener('keydown',e=>{if(dialog.hidden)return;if(e.key==='Escape')arcadeCloseSocial();if(e.key==='Tab'){
    const els=[...dialog.querySelectorAll('button:not([disabled]),input:not([disabled])')].filter(el=>el.offsetParent!==null);
    if(!els.length)return;const first=els[0],last=els[els.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  }});
  dialog.querySelector('#arcade-social-initials').addEventListener('input',e=>{e.target.value=e.target.value.toUpperCase().replace(/[^A-Z0-9 ]/g,'').slice(0,3);});
  dialog.querySelector('#arcade-social-save').addEventListener('click',()=>arcadeSendSocial(false));
  dialog.querySelector('#arcade-social-remove').addEventListener('click',()=>arcadeSendSocial(true));
  arcadeSocialDialog=dialog;return dialog;
}
function arcadeSocialStatus(message) {document.getElementById('arcade-social-status').textContent=message;}
function arcadeSetChoice(choice) {
  arcadeSocialChoice=choice;
  document.querySelectorAll('.arcade-social-choice').forEach(b=>{
    const selected=b.dataset.choice===choice;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected));
  });
}
async function arcadeOpenSocial(scoreId,achievement,trigger,showAll) {
  const dialog=arcadeBuildSocialDialog();arcadeSocialLastFocus=trigger;
  arcadeSocialCurrent={scoreId,achievement};arcadeSocialToken='';arcadeSocialWidgetId=null;
  dialog.querySelector('#arcade-social-heading').textContent=achievement.player.toUpperCase()+' • '+achievement.game+' • '+Number(achievement.score).toLocaleString('en-US');
  const choices=dialog.querySelector('#arcade-social-choices');choices.replaceChildren();
  ARCADE_CHOICES.forEach(([id,emoji,label])=>{
    const b=document.createElement('button');b.type='button';b.className='arcade-social-choice';b.dataset.choice=id;
    b.textContent=emoji+' '+label;b.addEventListener('click',()=>arcadeSetChoice(id));choices.append(b);
  });
  arcadeSetChoice('heart');
  const initials=dialog.querySelector('#arcade-social-initials');
  try{initials.value=localStorage.getItem('big-daddys-arcade-reaction-initials')||'';}catch(_){initials.value='';}
  dialog.hidden=false;document.body.classList.add('arcade-social-open');
  arcadeSocialStatus(showAll?'Choose a reaction, enter your initials, and complete verification.':'LOVE IT is selected. You can choose any other reaction.');
  dialog.querySelector('#arcade-social-close').focus();
  const captcha=dialog.querySelector('#arcade-social-captcha');captcha.replaceChildren();
  const start=Date.now();
  const wait=()=>{
    if(dialog.hidden||arcadeSocialCurrent?.scoreId!==scoreId)return;
    if(window.turnstile?.render){
      try{arcadeSocialWidgetId=window.turnstile.render(captcha,{
        sitekey:ARCADE_SOCIAL.siteKey,
        callback:token=>{arcadeSocialToken=token;arcadeSocialStatus('Verification complete. Ready to send!');},
        'expired-callback':()=>{arcadeSocialToken='';arcadeSocialStatus('Verification expired. Complete it again.');},
        'error-callback':()=>{arcadeSocialToken='';arcadeSocialStatus('Verification could not load. Please retry.');}
      });}catch(_){arcadeSocialStatus('Could not load verification. Please reopen reactions.');}
    }else if(Date.now()-start<12000){setTimeout(wait,250);}
    else arcadeSocialStatus('Cloudflare verification did not load. Check your connection.');
  };wait();
  // Read-only count lookup; errors do not prevent posting.
  try{
    const response=await fetch(ARCADE_SOCIAL.base+'/social-arcade?score_id='+scoreId,{
      headers:{apikey:ARCADE_SOCIAL.anon,Authorization:'Bearer '+ARCADE_SOCIAL.anon}
    });
    if(!response.ok)return;const data=await response.json();
    if(dialog.hidden||arcadeSocialCurrent?.scoreId!==scoreId)return;
    if(data?.reactions){choices.querySelectorAll('button').forEach(b=>{
      const count=Number(data.reactions[b.dataset.choice]||0);
      if(count>0)b.textContent+=' ('+count+')';
    });}
  }catch(_){}
}
function arcadeCloseSocial() {
  if(!arcadeSocialDialog)return;
  arcadeSocialDialog.hidden=true;document.body.classList.remove('arcade-social-open');
  if(arcadeSocialWidgetId!==null&&window.turnstile?.remove){try{window.turnstile.remove(arcadeSocialWidgetId);}catch(_){}}
  arcadeSocialWidgetId=null;arcadeSocialToken='';arcadeSocialCurrent=null;
  if(arcadeSocialLastFocus?.isConnected)arcadeSocialLastFocus.focus();
}
async function arcadeSendSocial(remove) {
  const current=arcadeSocialCurrent;if(!current)return;
  const initials=document.getElementById('arcade-social-initials').value.toUpperCase();
  if(!/^[A-Z0-9 ]{1,3}$/.test(initials)||!initials.trim()){arcadeSocialStatus('Enter 1–3 arcade initials.');return;}
  if(!arcadeSocialToken){arcadeSocialStatus('Complete the Cloudflare verification first.');return;}
  const save=document.getElementById('arcade-social-save'),undo=document.getElementById('arcade-social-remove');
  save.disabled=true;undo.disabled=true;arcadeSocialStatus('Sending to the arcade…');
  try{
    const device=arcadeDeviceToken();
    const response=await fetch(ARCADE_SOCIAL.base+'/social-arcade-write',{
      method:'POST',headers:{'Content-Type':'application/json',apikey:ARCADE_SOCIAL.anon,Authorization:'Bearer '+ARCADE_SOCIAL.anon},
      body:JSON.stringify({score_id:current.scoreId,player_initials:initials,device_token:device,
        reaction:remove?null:arcadeSocialChoice,turnstile_token:arcadeSocialToken})
    });
    const data=await response.json().catch(()=>({}));
    if(!response.ok||data.success!==true)throw Error(data.error||'Reaction could not be saved.');
    try{localStorage.setItem('big-daddys-arcade-reaction-initials',initials);}catch(_){}
    arcadeSocialStatus(remove?'Reaction removed!':'Reaction saved! 🏆');
    arcadeRefreshReactionTotals(current.scoreId);
    if(!remove&&arcadeSocialLastFocus?.isConnected)arcadeSocialLastFocus.textContent='❤️ REACTED!';
    setTimeout(()=>{if(arcadeSocialCurrent===current)arcadeCloseSocial();},900);
  }catch(e){arcadeSocialStatus(e.message||'Unable to save. Try again.');}
  finally{
    arcadeSocialToken='';save.disabled=false;undo.disabled=false;
    if(arcadeSocialWidgetId!==null&&window.turnstile?.reset){try{window.turnstile.reset(arcadeSocialWidgetId);}catch(_){}}
  }
}


/* TRASH TALK — additive Medal Club comments. GIVE PROPS remains unchanged. */
const ARCADE_TRASH_INITIALS_KEY='big-daddys-arcade-reaction-initials';
const ARCADE_TRASH_OWNED_KEY='big-daddys-arcade-owned-comments-v1';
let arcadeTrashDialog=null,arcadeTrashWidget=null,arcadeTrashCaptcha='',arcadeTrashCurrent=null,arcadeTrashLastFocus=null;
function arcadeTrashOwned(){try{const ids=JSON.parse(localStorage.getItem(ARCADE_TRASH_OWNED_KEY)||'[]');return Array.isArray(ids)?ids.filter(Number.isSafeInteger):[];}catch(_){return [];}}
function arcadeTrashSaveOwned(ids){try{localStorage.setItem(ARCADE_TRASH_OWNED_KEY,JSON.stringify([...new Set(ids)].slice(-500)));}catch(_){}}
function arcadeAttachTrashTalk(card,achievement){
 const scoreId=Number(achievement.id);if(!Number.isSafeInteger(scoreId)||scoreId<=0)return;
 const wrap=document.createElement('section');wrap.className='arcade-trash';wrap.dataset.scoreId=String(scoreId);
 const title=document.createElement('div');title.className='arcade-trash-title';title.textContent='💬 TRASH TALK';
 const entries=document.createElement('div');entries.className='arcade-trash-entries';entries.textContent='LOADING TRASH TALK…';
 const actions=document.createElement('div');actions.className='arcade-trash-actions';
 const more=document.createElement('button');more.type='button';more.className='arcade-trash-more';more.hidden=true;more.textContent='VIEW ALL COMMENTS';
 const add=document.createElement('button');add.type='button';add.className='arcade-trash-add';add.textContent='+ ADD TRASH TALK';
 more.addEventListener('click',()=>{wrap.classList.toggle('arcade-trash-expanded');more.textContent=wrap.classList.contains('arcade-trash-expanded')?'SHOW LESS':'VIEW ALL COMMENTS';});
 add.addEventListener('click',()=>arcadeOpenTrash(scoreId,achievement,add,null));
 actions.append(more,add);wrap.append(title,entries,actions);card.children[1].append(wrap);
}
function arcadeRenderTrashTalk(card,comments,scoreId){
 const wrap=card?.querySelector('.arcade-trash');if(!wrap||Number(wrap.dataset.scoreId)!==scoreId)return;
 const entries=wrap.querySelector('.arcade-trash-entries'),more=wrap.querySelector('.arcade-trash-more');entries.replaceChildren();
 if(!Array.isArray(comments)){entries.textContent='COMMENTS TEMPORARILY UNAVAILABLE';more.hidden=true;return;}
 const owned=new Set(arcadeTrashOwned());
 if(!comments.length){const empty=document.createElement('p');empty.className='arcade-trash-empty';empty.textContent='NO TRASH TALK YET. START THE RIVALRY!';entries.append(empty);}
 comments.forEach((comment,index)=>{
  if(!comment||!Number.isSafeInteger(Number(comment.id))||typeof comment.message!=='string')return;
  const row=document.createElement('div');row.className='arcade-trash-comment';if(index>=2)row.classList.add('arcade-trash-extra');
  const name=document.createElement('strong');name.textContent=String(comment.player_initials||'???').slice(0,3);
  const msg=document.createElement('span');msg.className='arcade-trash-message';msg.textContent=comment.message;
  row.append(name,msg);
  if(owned.has(Number(comment.id))){const del=document.createElement('button');del.type='button';del.className='arcade-trash-delete';del.textContent='DELETE';del.setAttribute('aria-label','Delete your comment');del.addEventListener('click',()=>arcadeOpenTrash(scoreId,null,del,Number(comment.id)));row.append(del);}
  entries.append(row);
 });
 more.hidden=comments.length<=2;if(more.hidden)wrap.classList.remove('arcade-trash-expanded');
 more.textContent=wrap.classList.contains('arcade-trash-expanded')?'SHOW LESS':'VIEW ALL COMMENTS ('+comments.length+')';
}
function arcadeBuildTrashDialog(){
 if(arcadeTrashDialog)return arcadeTrashDialog;
 const overlay=document.createElement('div');overlay.className='arcade-social-overlay';overlay.id='arcade-trash-overlay';overlay.hidden=true;overlay.setAttribute('role','dialog');overlay.setAttribute('aria-modal','true');overlay.setAttribute('aria-label','Trash Talk');
 overlay.innerHTML=`<div class="arcade-social-panel arcade-trash-panel"><button type="button" class="arcade-social-close" id="arcade-trash-close" aria-label="Close Trash Talk">✕</button><h2>💬 TRASH TALK</h2><p id="arcade-trash-heading"></p><div id="arcade-trash-post-fields"><label class="arcade-social-label" for="arcade-trash-initials">YOUR INITIALS (1–3)</label><input id="arcade-trash-initials" maxlength="3" autocomplete="off" placeholder="DON"><label class="arcade-social-label" for="arcade-trash-message">YOUR TRASH TALK (160 CHARACTERS MAX)</label><textarea id="arcade-trash-message" maxlength="160" rows="4" placeholder="Bring your best arcade banter!"></textarea><div id="arcade-trash-counter">0 / 160</div></div><p id="arcade-trash-delete-prompt" hidden>Delete this comment from this device?</p><div id="arcade-trash-captcha" class="arcade-social-captcha"></div><p id="arcade-trash-status" class="arcade-social-status" role="status" aria-live="polite"></p><div class="arcade-social-actions"><button type="button" id="arcade-trash-submit">POST TRASH TALK</button><button type="button" id="arcade-trash-cancel">CANCEL</button></div><p class="arcade-social-small">Keep it friendly. Maximum 160 characters. You can delete comments from the device that posted them.</p></div>`;
 document.body.append(overlay);overlay.querySelector('#arcade-trash-close').addEventListener('click',arcadeCloseTrash);overlay.querySelector('#arcade-trash-cancel').addEventListener('click',arcadeCloseTrash);overlay.addEventListener('click',e=>{if(e.target===overlay)arcadeCloseTrash();});
 overlay.querySelector('#arcade-trash-initials').addEventListener('input',e=>{e.target.value=e.target.value.toUpperCase().replace(/[^A-Z0-9 ]/g,'').slice(0,3);});
 overlay.querySelector('#arcade-trash-message').addEventListener('input',e=>{overlay.querySelector('#arcade-trash-counter').textContent=e.target.value.length+' / 160';});
 overlay.querySelector('#arcade-trash-submit').addEventListener('click',arcadeSubmitTrash);
 overlay.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();arcadeCloseTrash();}if(e.key!=='Tab')return;const els=[...overlay.querySelectorAll('button:not([disabled]),input:not([disabled]),textarea:not([disabled])')].filter(el=>el.getClientRects().length);if(!els.length)return;const first=els[0],last=els[els.length-1];if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}});
 arcadeTrashDialog=overlay;return overlay;
}
function arcadeTrashStatus(msg){const el=arcadeTrashDialog?.querySelector('#arcade-trash-status');if(el)el.textContent=msg;}
function arcadeOpenTrash(scoreId,achievement,trigger,commentId){
 const overlay=arcadeBuildTrashDialog();arcadeTrashCurrent={scoreId,commentId};arcadeTrashLastFocus=trigger;arcadeTrashCaptcha='';arcadeTrashWidget=null;
 const deleting=Number.isSafeInteger(commentId);overlay.querySelector('#arcade-trash-post-fields').hidden=deleting;overlay.querySelector('#arcade-trash-delete-prompt').hidden=!deleting;
 overlay.querySelector('#arcade-trash-submit').textContent=deleting?'DELETE MY COMMENT':'POST TRASH TALK';overlay.querySelector('#arcade-trash-submit').disabled=false;
 overlay.querySelector('#arcade-trash-heading').textContent=achievement?achievement.player.toUpperCase()+' • '+achievement.game:'REMOVE YOUR TRASH TALK';
 const initials=overlay.querySelector('#arcade-trash-initials');try{initials.value=localStorage.getItem(ARCADE_TRASH_INITIALS_KEY)||'';}catch(_){initials.value='';}
 overlay.querySelector('#arcade-trash-message').value='';overlay.querySelector('#arcade-trash-counter').textContent='0 / 160';
 overlay.hidden=false;document.body.classList.add('arcade-social-open');overlay.querySelector('#arcade-trash-close').focus();arcadeTrashStatus('Complete Cloudflare verification to continue.');
 const captcha=overlay.querySelector('#arcade-trash-captcha');captcha.replaceChildren();const started=Date.now();
 const wait=()=>{if(overlay.hidden||arcadeTrashCurrent?.scoreId!==scoreId||arcadeTrashCurrent?.commentId!==commentId)return;
  if(window.turnstile?.render){try{arcadeTrashWidget=window.turnstile.render(captcha,{sitekey:ARCADE_SOCIAL.siteKey,callback:token=>{arcadeTrashCaptcha=token;arcadeTrashStatus('Verification complete. Ready!');},'expired-callback':()=>{arcadeTrashCaptcha='';arcadeTrashStatus('Verification expired. Please retry.');},'error-callback':()=>{arcadeTrashCaptcha='';arcadeTrashStatus('Verification failed. Please retry.');}});}catch(_){arcadeTrashStatus('Could not load verification. Reopen Trash Talk.');}}
  else if(Date.now()-started<12000)setTimeout(wait,250);else arcadeTrashStatus('Cloudflare verification did not load.');};wait();
}
function arcadeCloseTrash(){if(!arcadeTrashDialog)return;arcadeTrashDialog.hidden=true;document.body.classList.remove('arcade-social-open');if(arcadeTrashWidget!==null&&window.turnstile?.remove){try{window.turnstile.remove(arcadeTrashWidget);}catch(_){}}arcadeTrashWidget=null;arcadeTrashCaptcha='';arcadeTrashCurrent=null;if(arcadeTrashLastFocus?.isConnected)arcadeTrashLastFocus.focus();}
async function arcadeSubmitTrash(){
 const current=arcadeTrashCurrent;if(!current)return;const deleting=Number.isSafeInteger(current.commentId);
 const initials=arcadeTrashDialog.querySelector('#arcade-trash-initials').value.toUpperCase().trim(),message=arcadeTrashDialog.querySelector('#arcade-trash-message').value.trim();
 if(!deleting&&(!/^[A-Z0-9 ]{1,3}$/.test(initials)||!initials.trim())){arcadeTrashStatus('Enter 1–3 arcade initials.');return;}
 if(!deleting&&(!message||message.length>160)){arcadeTrashStatus('Enter 1–160 characters of Trash Talk.');return;}
 if(!arcadeTrashCaptcha){arcadeTrashStatus('Complete Cloudflare verification first.');return;}
 const submit=arcadeTrashDialog.querySelector('#arcade-trash-submit');submit.disabled=true;arcadeTrashStatus(deleting?'Deleting comment…':'Posting Trash Talk…');
 try{
  const body={action:deleting?'delete':'post',score_id:current.scoreId,device_token:arcadeDeviceToken(),turnstile_token:arcadeTrashCaptcha};
  if(deleting)body.comment_id=current.commentId;else{body.player_initials=initials;body.message=message;}
  const response=await fetch(ARCADE_SOCIAL.base+'/social-arcade-comments-write',{method:'POST',headers:{'Content-Type':'application/json',apikey:ARCADE_SOCIAL.anon,Authorization:'Bearer '+ARCADE_SOCIAL.anon},body:JSON.stringify(body)});
  const data=await response.json().catch(()=>({}));if(!response.ok||data.success!==true)throw Error(data.error||'Unable to save Trash Talk.');
  const owned=arcadeTrashOwned();if(deleting)arcadeTrashSaveOwned(owned.filter(id=>id!==current.commentId));else{arcadeTrashSaveOwned([...owned,Number(data.comment_id)]);try{localStorage.setItem(ARCADE_TRASH_INITIALS_KEY,initials);}catch(_){}}
  arcadeTrashStatus(deleting?'Comment deleted!':'Trash Talk posted! 👾');arcadeRefreshReactionTotals(current.scoreId);
  setTimeout(()=>{if(arcadeTrashCurrent===current)arcadeCloseTrash();},850);
 }catch(e){arcadeTrashStatus(e.message||'Unable to save Trash Talk.');}
 finally{arcadeTrashCaptcha='';submit.disabled=false;if(arcadeTrashWidget!==null&&window.turnstile?.reset){try{window.turnstile.reset(arcadeTrashWidget);}catch(_){}}}
}
