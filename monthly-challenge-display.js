/* Only show published monthly data after its 9 AM Eastern reveal gate.
   Never use sealed state in the browser. */
(() => {
 const slide=document.getElementById('showcase-monthly');
 if(!slide)return;
 const spotlight=slide.querySelector('.legend-spotlight');
 const note=slide.querySelector('.legends-note');
 const kicker=slide.querySelector('.arcade-showcase-kicker');
 if(!spotlight)return;
 const etParts=()=>{
  const parts=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date());
  const o={};for(const p of parts)o[p.type]=p.value;
  return {month:o.year+'-'+o.month,day:Number(o.day),hour:Number(o.hour),minute:Number(o.minute)};
 };
 const add=(cls,text)=>{
   const p=document.createElement('p');p.className=cls;p.textContent=text;spotlight.append(p);return p;
 };
 let last=null;
 function draw(){
  const et=etParts();
  const canReveal=et.day>=1&&(et.day>1||et.hour>=9);
  if(!last||last.month!==et.month||!canReveal){
    const countdown=document.getElementById('monthly-countdown');
    if(countdown && spotlight.dataset.monthlyPublished!=='yes'){
      if(et.day===1&&et.hour>=9){
        countdown.textContent='AWAITING OFFICIAL LAUNCH';
      }else{
        const year=Number(et.month.slice(0,4)), mon=Number(et.month.slice(5));
        const revealDay=et.day===1?{year,mon}:{year:mon===12?year+1:year,mon:mon===12?1:mon+1};
        const approx=new Date(Date.UTC(revealDay.year,revealDay.mon-1,1,14));
        const zoneName=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',timeZoneName:'shortOffset'}).formatToParts(approx).find(p=>p.type==='timeZoneName')?.value||'GMT-5';
        const match=zoneName.match(/[+-](\\d{1,2})(?::(\\d{2}))?/);
        const tzHours=match?Number(match[1])*(zoneName.includes('-')?-1:1):-5;
        const target=Date.UTC(revealDay.year,revealDay.mon-1,1,9-tzHours);
        const secs=Math.max(0,Math.floor((target-Date.now())/1000));
        const days=Math.floor(secs/86400),hours=Math.floor(secs%86400/3600),minutes=Math.floor(secs%3600/60);
        countdown.textContent=days+'D '+hours+'H '+minutes+'M UNTIL REVEAL';
      }
    }
    // Preserve the existing countdown and mystery copy before release.
    if(spotlight.dataset.monthlyPublished==='yes'){
      spotlight.replaceChildren();
      add('legend-headline','MYSTERY GAME REVEAL');
      add('legend-score','AWAITING OFFICIAL REVEAL');
      add('legend-detail','A NEW GAME IS REVEALED AT 9 AM EASTERN ON THE 1ST');
      spotlight.dataset.monthlyPublished='no';
    }
    return;
  }
  if(spotlight.dataset.monthlyReleaseTime===last.updated_at)return;
  spotlight.replaceChildren();
  spotlight.dataset.monthlyPublished='yes';
  spotlight.dataset.monthlyReleaseTime=last.updated_at;
  kicker.textContent='THE FEATURED GAME IS LIVE!';
  // iScored's actual per-game logo URL, verified from the operator's
  // browser HAR (e.g. /images/games/game49994 is the Pac-Man marquee).
  // Only request artwork after the site's Eastern-time reveal gate has passed
  // AND the already-published monthly feed has identified this month's game.
  // Missing or inaccessible logos are optional: preserve neon text instead.
  const id=String(last.game_id||'');
  if(/^\\d{1,12}$/.test(id)){
    const marquee=document.createElement('img');
    marquee.className='monthly-marquee';
    marquee.alt=String(last.game||'Featured game')+' arcade marquee';
    marquee.loading='lazy';
    marquee.decoding='async';
    marquee.referrerPolicy='no-referrer';
    marquee.onerror=()=>{marquee.remove();};
    marquee.src='https://www.iscored.info/images/games/game'+id;
    spotlight.append(marquee);
  }
  add('legend-headline',String(last.game||'FEATURED GAME').toUpperCase());
  add('legend-detail','STARTING RECORD: '+Number(last.starting_record).toLocaleString('en-US'));
  add('legend-score','BEAT THE BENCHMARK: '+Number(last.benchmark).toLocaleString('en-US'));
  add('legend-detail','PROVISIONAL STANDINGS — SCORES AWAIT VERIFICATION');
  const names=(Array.isArray(last.leaderboard)?last.leaderboard:[]).slice(0,3);
  if(names.length)for(const row of names)add('legend-detail','#'+row.rank+' '+String(row.player||'').toUpperCase()+' — '+Number(row.score).toLocaleString('en-US'));
  else add('legend-detail','BE THE FIRST TO ENTER THE MONTHLY LEADERBOARD!');
  note.textContent='ONE CREDIT ONLY! NO CONTINUES! • SUBMIT SCORES IN ALL CAPS!!! • NO OFFICIAL AWARDS YET';
 }
 async function poll(){
  try{
   const response=await fetch('./monthly-challenge-live.json?refresh='+Date.now(),{cache:'no-store'});
   if(!response.ok)return;
   const data=await response.json();
   if(data&&data.schema_version===1&&data.status==='provisional'
      &&typeof data.game==='string'&&/^\\d{1,12}$/.test(String(data.game_id||''))
      &&Number.isSafeInteger(data.starting_record)
      &&Number.isSafeInteger(data.benchmark)&&Array.isArray(data.leaderboard))
     last=data;
  }catch(_){}
  draw();
 }
 poll();setInterval(poll,5*60*1000);setInterval(draw,30*1000);
})();
