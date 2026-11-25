/* Easter Egg discovery: preserves the existing five-second Test Lab unlock. */
(() => {
 'use strict';
 const endpoint='https://jrqzwlowxofnyqpmjgkg.supabase.co/functions/v1/arcade-easter-egg';
 const invader=document.getElementById('arcade-secret-invader');
 if(!invader)return;
 const mask=document.createElement('div');
 mask.id='arcade-egg-backdrop';
 mask.hidden=true;
 mask.innerHTML='<section role="dialog" aria-modal="true" aria-labelledby="arcade-egg-title" class="arcade-egg-panel"><div class="arcade-egg-icon" aria-hidden="true">🥚✨</div><h2 id="arcade-egg-title">SECRET DISCOVERED!</h2><p>It\'s a Secret to Everybody.</p><form id="arcade-egg-form"><label for="arcade-egg-initials">ENTER YOUR iSCORED INITIALS</label><input id="arcade-egg-initials" maxlength="3" autocomplete="off" autocapitalize="characters" required pattern="[A-Za-z0-9 ]{1,3}" placeholder="AAA"><button type="submit">🏆 CLAIM EASTER EGG</button></form><p id="arcade-egg-feedback" role="status" aria-live="polite"></p><button type="button" id="arcade-egg-close">CONTINUE TO TEST LAB ▶</button></section>';
 document.body.append(mask);
 const form=mask.querySelector('#arcade-egg-form'), input=mask.querySelector('#arcade-egg-initials');
 const feedback=mask.querySelector('#arcade-egg-feedback'), close=mask.querySelector('#arcade-egg-close'), submit=form.querySelector('button');
 const dismiss=()=>{mask.hidden=true;feedback.textContent='';form.hidden=false;submit.disabled=false;};
 close.addEventListener('click',dismiss);
 mask.addEventListener('keydown',e=>{if(e.key==='Escape'){e.preventDefault();dismiss()}});
 const launch=()=>{
   mask.hidden=false; form.hidden=false; feedback.textContent='';submit.disabled=false;input.value='';
   input.focus();
 };
 window.addEventListener('arcade-easter-egg-discovered',launch);
 form.addEventListener('submit',async e=>{
   e.preventDefault();const initials=input.value.trim().toUpperCase();
   if(!/^[A-Z0-9 ]{1,3}$/.test(initials)||!initials.trim()){feedback.textContent='Enter your iScored initials.';return}
   submit.disabled=true;feedback.textContent='SAVING YOUR TROPHY...';
   try{
     const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({initials}),signal:AbortSignal.timeout(12000)});
     const data=await response.json();
     if(!response.ok||!data.ok)throw new Error(data.error||'Could not save the trophy.');
     feedback.textContent=data.new_award?'🏆 ACHIEVEMENT UNLOCKED! EASTER EGG • '+initials:'🏆 '+initials+' ALREADY UNLOCKED THIS EASTER EGG!';
     form.hidden=true;
     window.dispatchEvent(new CustomEvent('arcade-easter-egg-earned',{detail:{player:initials,claimed_at:data.claimed_at}}));
   }catch(err){feedback.textContent=err.message||'Connection problem. Please try again.';}
   finally{submit.disabled=false}
 });
})();