const reset=document.querySelector('#reset');reset.addEventListener('click',()=>{window.scrollTo({top:0,behavior:'smooth'});});let deferredPrompt;window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();deferredPrompt=event;document.querySelector('#install').hidden=false});document.querySelector('#install').addEventListener('click',async()=>{if(!deferredPrompt)return;deferredPrompt.prompt();await deferredPrompt.userChoice;deferredPrompt=null;document.querySelector('#install').hidden=true});if('serviceWorker' in navigator){window.addEventListener('load',()=>navigator.serviceWorker.register('./sw.js').catch(()=>{}));}

// Optional verified score feed. Never place iScored API credentials in this public PWA.
(async function initLegends(){
 const panel=document.querySelector('#legend-spotlight'),controls=document.querySelector('#legend-controls'),counter=document.querySelector('#legend-counter'),source=document.querySelector('#legend-source');
 try {
  const response=await fetch('./legends.json',{cache:'no-store'});
  if(!response.ok)throw new Error('Feed unavailable');
  const data=await response.json();
  const entries=Array.isArray(data.entries)?data.entries.filter(e=>e && typeof e.player==='string' && typeof e.game==='string' && (typeof e.score==='string'||typeof e.score==='number')):[];
  if(!entries.length)return;
  let position=0;const safe=(v)=>String(v).toUpperCase();
  function render(){const e=entries[position];panel.replaceChildren();const h=document.createElement('p');h.className='legend-headline';h.textContent=safe(e.player);const g=document.createElement('p');g.className='legend-detail';g.textContent=safe(e.game);const sc=document.createElement('p');sc.className='legend-score';sc.textContent=String(e.score);panel.append(h,g,sc);counter.textContent=`${position+1} / ${entries.length}`;}
  document.querySelector('#legend-prev').addEventListener('click',()=>{position=(position+entries.length-1)%entries.length;render()});
  document.querySelector('#legend-next').addEventListener('click',()=>{position=(position+1)%entries.length;render()});
  controls.hidden=entries.length<2;source.textContent=data.updated_at?`SCORES UPDATED ${new Date(data.updated_at).toLocaleDateString()}`:'FEATURED APPROVED SCORES';render();
  if(entries.length>1&&!window.matchMedia('(prefers-reduced-motion: reduce)').matches){setInterval(()=>{if(!document.hidden){position=(position+1)%entries.length;render()}},8000)}
 }catch(e){source.textContent='LIVE SCORES UNAVAILABLE — VIEW VERIFIED SCORES ON iSCORED.';}
})();
