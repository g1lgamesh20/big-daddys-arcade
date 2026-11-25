/* Big Daddy's Arcade — Hall of Achievements, Series One.
   Public, read-only discovery gallery. Never claims to award a trophy itself. */
(() => {
  'use strict';
  const dialog=document.getElementById('achievement-showcase-dialog');
  const open=document.getElementById('achievement-showcase-open');
  const close=document.getElementById('achievement-showcase-close');
  const select=document.getElementById('achievement-showcase-player');
  const filters=document.getElementById('achievement-showcase-filters');
  const gallery=document.getElementById('achievement-showcase-gallery');
  const summary=document.getElementById('achievement-showcase-summary');
  if(!dialog||!open||!close||!select||!filters||!gallery||!summary)return;

  const CATEGORIES=[
    {id:'daily',name:'⚔️ Daily Challenge'},
    {id:'thursday',name:'🏆 Thursday Challenge'},
    {id:'monthly',name:'🌟 Game of the Month'},
    {id:'participation',name:'🎮 Participation & Streaks'},
    {id:'gold',name:'🥇 Gold Mastery'},
    {id:'social',name:'💬 Social Achievements'},
    {id:'special',name:'❓ Special Achievements'},
  ];
  const entries=[];
  const add=(id,category,emoji,name,description,kind,threshold=0,status='live',note='')=>{
    entries.push({id,category,emoji,name,description,kind,threshold,status,note});
  };
  add('daily_champion','daily','🥇','Beat the Champion — Gold',
      'Beat the day’s locked starting champion score with a qualifying approved Daily Challenge score. Multiple players can win on the same day. This earns a Gold-level challenge trophy, not a second iScored Gold medal.',
      'daily_champion',0,'live','Requires a pre-event locked champion score. First place in iScored is separate.');
  add('thursday_champion','thursday','🏆','Thursday Champion',
      'Finish with the highest qualifying score for the Thursday Arcade Challenge.','thursday_champion');
  add('gotm_champion','monthly','🌟','Game of the Month Champion',
      'Finish with the top qualifying score in the revealed monthly competition.','gotm_champion');
  add('monthly_benchmark','monthly','🎯','Beat the Benchmark',
      'Exceed 75% of the featured game’s locked starting record with a qualifying approved score.',
      'monthly_benchmark',0,'live','The target is frozen at monthly launch. An exact tie does not beat it.');
  add('monthly_average','monthly','📊','Beat the Average',
      'Beat the arithmetic mean of the best qualifying approved score from each player in the finalized monthly competition.',
      'monthly_average',0,'live','Requires at least three distinct verified participants. Each player counts once; an exact tie with the average does not qualify.');
  for(const [place,name,emoji] of [[1,'Monthly Gold','🥇'],[2,'Monthly Silver','🥈'],[3,'Monthly Bronze','🥉']]){
    add('monthly_podium_'+place,'monthly',emoji,name,
      'Finish in '+(place===1?'first':place===2?'second':'third')+' place in the finalized Game of the Month. Tied players share a rank (1, 1, 3).',
      'monthly_podium',place,'live','Based on highest qualifying approved score per player, after the approval grace period.');
  }
  const daily=[[5,'Getting Started'],[10,'Dedicated Challenger'],[25,'Champion Chaser'],[50,'Never Back Down']];
  const thursday=[[3,'Thursday Regular'],[5,'Thursday Devotee'],[10,'Thursday Veteran'],[25,'Thursday Legend']];
  const monthly=[[3,'Monthly Challenger'],[6,'Half-Year Hero'],[12,'Year-Round Legend'],[24,'Two-Year Titan'],[36,'Three-Year Legend'],[60,'Five-Year Immortal']];
  for(const [kind,items,emoji,label] of [
    ['daily',daily,'🎮','different Daily Challenges'],
    ['thursday',thursday,'🏆','different Thursday Challenges'],
    ['monthly',monthly,'🌟','different monthly competitions']]){
    for(const [threshold,name] of items)
      add(kind+'_participation:'+threshold,'participation',emoji,name,
          'Participate in '+threshold+' '+label+' with qualifying approved scores. Earlier milestones remain earned.',
          kind+'_participation',threshold);
  }
  for(const [kind,items,label] of [
    ['daily',[[3,'Three-Day Streak'],[7,'Seven-Day Streak'],[14,'Two-Week Streak']],'Daily Challenge days'],
    ['thursday',[[3,'Three-Thursday Streak'],[5,'Five-Thursday Streak']],'Thursdays'],
    ['monthly',[[3,'Three-Month Streak'],[6,'Six-Month Streak']],'months']]){
    for(const [threshold,name] of items)
      add(kind+'_streak:'+threshold,'participation','🔥',name,
          'Participate in '+threshold+' consecutive '+label+'. Streaks count verified challenge events, not approval dates.',
          kind+'_streak',threshold);
  }
  for(const [threshold,name,emoji] of [[5,'Champion Slayer','⚔️'],[10,'Champion Hunter','🔥'],[25,'Champion Crusher','👑'],[50,'Legend of Champions','🏆'],[100,'The Unstoppable','💎']])
    add('daily_champion_mastery:'+threshold,'gold',emoji,name,
        'Defeat the locked starting Daily Champion on '+threshold+' different Eastern calendar days with qualifying approved scores. Earlier milestones remain earned.',
        'daily_champion_mastery',threshold);
  for(const [threshold,name,emoji] of [[1,'Golden Encore','🥇'],[5,'Gold Rush','🔥'],[10,'Untouchable','👑']])
    add('golden_encore:'+threshold,'gold',emoji,name,
        'Improve an already-held Gold-leading score on '+threshold+' qualifying occasion'+(threshold===1?'':'s')+'. First-time Gold does not count.',
        'golden_encore',threshold);
  for(const [threshold,name,emoji] of [[1,'Personal Best!','📈'],[5,'Personal Best! x5','🌟'],[10,'Personal Best! x10','💎']])
    add('personal_best_milestone:'+threshold,'gold',emoji,name,
      'Earn '+threshold+' verified score improvement'+(threshold===1?'':'s')+' on your own previous approved scores. Only post-November 20, 2026 evidence counts.',
      'personal_best_milestone',threshold,'live',
      'Each improvement must be a new approved score strictly higher than your earlier recorded best for that game.');
  add('never_give_up','gold','💪','NEVER GIVE UP!',
      'Make five distinct verified unsuccessful score submissions on the same game, then take Gold (#1) with a new verified score.',
      'never_give_up',0,'live',
      'One trophy per player lifetime. Requires an observed Gold takeover and five earlier approved attempts below the previous Gold score.');
  // Social trophies are catalogued as planned until an authenticated,
  // server-verifiable social audit and player identity mapping are deployed.
  // The existing browser-entered initials and device token are NOT award proof.
  const socialMilestones=[
    [1,'Trash Talk Rookie','Props Giver'],
    [5,'Trash Talk Regular','Hi 5!'],
    [10,'Trash Talk Veteran','Good Sport'],
    [25,'Trash Talk Legend','Hype Squad'],
    [50,'Master of Banter','Community Champion'],
    [100,'Arcade Mouthpiece','Props Legend']
  ];
  for(const [days,talkName,propsName] of socialMilestones){
    for(const [kind,name,emoji,description] of [
      ['trash_talk',talkName,'💬','Post qualifying Trash Talk (including community-wide posts)'],
      ['give_props',propsName,'🪙','Give a qualifying positive reaction to another player']
    ]){
      add('social_'+kind+':'+days,'social',emoji,name,
        description+' on '+days+' different Eastern calendar day'+(days===1?'':'s')+'. Only one credit per player per day for this activity; extra posts or reactions that day do not increase progress.',
        'social_'+kind,days,'planned',
        'Server-verified player identity and activity evidence required. Historical posts do not automatically unlock trophies.');
    }
  }
  add('easter_egg','special','❓','Easter Egg',"It's a Secret to Everybody.",'easter_egg',0,
      'planned','Secret discovery achievement. Unlocking mechanism is not displayed.');

  // Wave 2 secret trophies: catalog-only until trustworthy immutable score
  // submission/record-history evidence is available. Never infer from current rank.
  const secretWave2=[
    ['high_five','🖐️','HIGH FIVE!','Five different games. One legendary day. HIGH FIVE!'],
    ['night_owl','🦉','NIGHT OWL','Legends never sleep.'],
    ['back_from_the_dead','🔥','BACK FROM THE DEAD','You thought I was finished?'],
    ['double_trouble','🎮','DOUBLE TROUBLE','Two games. Two crowns. One legend.'],
    ['photo_finish','🎯','PHOTO FINISH','Missed it by THAT much!'],
    ['king_for_a_day','👑','KING FOR A DAY','Enjoy the view while it lasts.'],
    ['treasure_hunter','💎','TREASURE HUNTER','Nobody saw that coming.'],
    ['arcade_hopper','🕹️','ARCADE HOPPER',"Can't pick a favorite!"],
    ['just_in_time','⏰','JUST IN TIME','Talk about cutting it close!']
  ];
  secretWave2.push(['props_machine','🙌','PROPS MACHINE!','Three cheers in one day!']);
  for(const [id,emoji,name,description] of secretWave2){
    const activated=['high_five','night_owl','arcade_hopper','back_from_the_dead','king_for_a_day','double_trouble','photo_finish','treasure_hunter'].includes(id);
    add('secret_'+id,'special',emoji,name,description,'secret_'+id,0,
      activated?'live':'planned',
      activated?'Verified approved-score achievement; unlocks automatically when earned.':
      'Hidden Wave 2 trophy. Awaiting verified historical evidence before automatic issuance.');
  }

  // These are discovery hints only; no client-side action can award a trophy.
  const SECRET_GOALS={
    secret_high_five:'Submit approved scores on five different games in one Eastern day.',
    secret_night_owl:'Submit an approved score between midnight and 3:00 AM Eastern.',
    secret_back_from_the_dead:'Regain a #1 record you previously held and lost.',
    secret_double_trouble:'Take #1 on two different games in one Eastern day.',
    secret_photo_finish:'Submit an approved score strictly below, but within 1% of, an already observed #1 record. The Gold record must have been observed before submission.',
    secret_king_for_a_day:'Be observed holding a #1 record at least 24 hours apart, without a recorded loss of Gold.',
    secret_treasure_hunter:'Establish the first verified #1 on a game previously observed with no approved scores.',
    secret_arcade_hopper:'Submit approved scores on ten different games within seven consecutive days.',
    secret_just_in_time:'Beat the locked starting Daily Champion in the last five minutes before Eastern midnight.',
    secret_props_machine:'Give Props to three different players on one Eastern calendar day.'
  };
  const revealedSecrets=new Set(); // Temporary for this open session, never persisted.
  let awards=[],plays=[],history={},goldState={},players=[],selected='',category='all',previousFocus=null,loading=false;
  const el=(tag,cls,text)=>{
    const node=document.createElement(tag);
    if(cls)node.className=cls;
    if(text!==undefined)node.textContent=text;
    return node;
  };
  const uniqueAwards=(player)=>awards.filter(a=>a && a.player && String(a.player).trim().toUpperCase()===player);
  const awardsOf=(player,type)=>uniqueAwards(player).filter(a=>a.type===type);
  function count(player,kind){
    const fromHistory=history?.players?.[player]?.participation?.[kind];
    if(Number.isInteger(fromHistory)&&fromHistory>=0)return fromHistory;
    const values=new Set();
    for(const p of plays)if(p?.kind===kind&&String(p.player||'').toUpperCase()===player){
      const day=kind==='monthly'?String(p.event_month||p.date||'').slice(0,7):String(p.date||'');
      if(day)values.add(day);
    }
    for(const a of uniqueAwards(player)){
      const map={daily_champion:'daily',thursday_champion:'thursday',gotm_champion:'monthly'};
      if(map[a.type]!==kind)continue;
      const day=kind==='monthly'?String(a.event_month||a.date||'').slice(0,7):String(a.date||'');
      if(day)values.add(day);
    }
    return values.size;
  }
  function streak(player,kind){
    const n=history?.players?.[player]?.longest_verified_streaks?.[kind];
    return Number.isInteger(n)&&n>=0?n:0;
  }
  function goldImprovements(player){
    const rows=Array.isArray(goldState.improvements)?goldState.improvements:[];
    return new Set(rows.filter(e=>e&&String(e.player||'').toUpperCase()===player)
      .map(e=>String(e.score_id||'')).filter(Boolean)).size;
  }
  function unlocked(player,entry){
    const playerAwards=uniqueAwards(player);
    if(entry.kind==='daily_champion'||entry.kind==='thursday_champion'||entry.kind==='gotm_champion')
      return playerAwards.some(a=>a.type===entry.kind);
    if(entry.kind==='monthly_benchmark')
      return playerAwards.some(a=>a.type==='gotm_beat_average');
    if(entry.kind==='monthly_average')
      return playerAwards.some(a=>a.type==='gotm_beat_player_average');
    if(entry.kind==='monthly_podium')
      return playerAwards.some(a=>a.type==='gotm_podium_'+entry.threshold);
    if(entry.kind==='personal_best_milestone')
      return playerAwards.some(a=>a.id==='personal_best_milestone:'+player+':'+entry.threshold);
    if(entry.kind==='never_give_up')
      return playerAwards.some(a=>a.type==='never_give_up'||a.id==='never_give_up:'+player);
    if(entry.kind==='daily_champion_mastery')
      return playerAwards.some(a=>a.id==='daily_champion_mastery:'+player+':'+entry.threshold);
    if(entry.kind==='golden_encore')
      return playerAwards.some(a=>a.id==='golden_encore:'+player+':'+entry.threshold);
    if(entry.kind.endsWith('_participation')||entry.kind.endsWith('_streak'))
      return playerAwards.some(a=>a.id===entry.kind.replace('_participation','_participation').replace('_streak','_streak')+':'+player+':'+entry.threshold);
    if(entry.kind.startsWith('secret_') || entry.kind==='easter_egg')
      return playerAwards.some(a=>a.type===entry.kind || a.id===entry.kind+':'+player);
    return false;
  }
  function progress(player,entry){
    if(entry.kind==='daily_champion_mastery')return new Set(awardsOf(player,'daily_champion').map(a=>String(a.date||'')).filter(Boolean)).size;
    if(entry.kind==='golden_encore')return goldImprovements(player);
    if(entry.kind.endsWith('_participation'))return count(player,entry.kind.split('_')[0]);
    if(entry.kind.endsWith('_streak'))return streak(player,entry.kind.split('_')[0]);
    return 0;
  }
  function createTile(entry){
    const won=Boolean(selected)&&unlocked(selected,entry);
    const planned=entry.status==='planned';
    const secret=entry.kind.startsWith('secret_') || entry.kind==='easter_egg';
    const concealed=secret&&!won&&!revealedSecrets.has(entry.id);
    const tile=el('article','achievement-tile'+(won?' achievement-tile-earned':'')+(planned?' achievement-tile-planned':''));
    // Compact by default: no descriptions, progress bars or notes are
    // mounted until the player actually taps an achievement.
    const toggle=el('button','achievement-tile-toggle');
    toggle.type='button';
    toggle.setAttribute('aria-expanded','false');
    toggle.setAttribute('aria-label',concealed?'Show mystery achievement':'Show details for '+entry.name);
    const glyph=el('span','achievement-tile-glyph',concealed?'❓':entry.emoji);
    glyph.setAttribute('aria-hidden','true');
    const title=el('span','achievement-tile-name',concealed?'Secret Achievement':entry.name);
    const status=el('span','achievement-tile-status',won?'★ UNLOCKED':planned?'COMING SOON':'🔒 LOCKED');
    const chevron=el('span','achievement-tile-chevron','⌄');
    chevron.setAttribute('aria-hidden','true');
    toggle.append(glyph,title,status,chevron);
    const detail=el('div','achievement-tile-details');
    detail.hidden=true;
    const reveal=()=>{
      if(!secret||won||revealedSecrets.has(entry.id))return;
      revealedSecrets.add(entry.id);
      // Rebuild this tile so the newly revealed title and goal appear together.
      tile.replaceWith(createTile(entry));
      const refreshed=[...gallery.querySelectorAll('.achievement-tile')].find(t=>t.querySelector('.achievement-tile-name')?.textContent===entry.name);
      if(refreshed){const b=refreshed.querySelector('.achievement-tile-toggle');b?.focus();b?.click();}
    };
    if(secret&&!won){
      let holdTimer=null;
      const cancel=()=>{if(holdTimer!==null){clearTimeout(holdTimer);holdTimer=null;}};
      const start=()=>{cancel();if(!revealedSecrets.has(entry.id))holdTimer=setTimeout(()=>{holdTimer=null;reveal();},7000);};
      toggle.addEventListener('pointerdown',e=>{if(e.button!==0)return;start();});
      for(const event of ['pointerup','pointercancel','pointerleave','blur','contextmenu'])toggle.addEventListener(event,cancel);
      toggle.addEventListener('contextmenu',e=>{e.preventDefault();});
      toggle.addEventListener('keydown',e=>{if(e.key===' '||e.key==='Enter'){if(e.repeat)return;start();}});
      toggle.addEventListener('keyup',e=>{if(e.key===' '||e.key==='Enter')cancel();});
      toggle.style.userSelect='none';toggle.style.webkitUserSelect='none';
      toggle.style.webkitTouchCallout='none';
    }
    toggle.addEventListener('click',()=>{
      const expanding=detail.hidden;
      if(expanding&&!detail.dataset.built){
        detail.append(el('p','achievement-tile-desc',concealed?'A mystery trophy. Its name and unlock condition are hidden until earned.':entry.description));
        if(secret&&!concealed&&entry.kind!=='easter_egg'&&SECRET_GOALS[entry.id])
          detail.append(el('p','achievement-tile-desc',SECRET_GOALS[entry.id]));
        if(entry.threshold&&!planned&&(entry.kind==='golden_encore'||entry.kind==='daily_champion_mastery'||entry.kind.endsWith('_participation')||entry.kind.endsWith('_streak'))){
          const n=selected?progress(selected,entry):0;
          detail.append(el('p','achievement-tile-progress',
            selected?'PROGRESS: '+Math.min(n,entry.threshold)+' / '+entry.threshold:'SELECT A PLAYER TO SEE PROGRESS'));
          if(selected){
            const bar=el('div','achievement-tile-track');
            bar.setAttribute('role','progressbar');
            bar.setAttribute('aria-label',entry.name+' progress');
            bar.setAttribute('aria-valuemin','0');
            bar.setAttribute('aria-valuemax',String(entry.threshold));
            bar.setAttribute('aria-valuenow',String(Math.min(n,entry.threshold)));
            const fill=el('div','achievement-tile-fill');
            fill.style.width=(Math.min(100,100*n/entry.threshold))+'%';
            bar.append(fill);detail.append(bar);
          }
        }
        if(won){
          const matches=uniqueAwards(selected).filter(a=>{
            if(entry.kind==='daily_champion'||entry.kind==='thursday_champion'||entry.kind==='gotm_champion')
              return a.type===entry.kind;
            if(entry.kind==='monthly_benchmark')return a.type==='gotm_beat_average';
            if(entry.kind==='monthly_average')return a.type==='gotm_beat_player_average';
            if(entry.kind==='monthly_podium')return a.type==='gotm_podium_'+entry.threshold;
            // Award IDs are kind:PLAYER:threshold for milestones, but
            // secret achievements use kind:PLAYER without a threshold.
            if(entry.kind.startsWith('secret_') || entry.kind==='easter_egg')
              return a.type===entry.kind || a.id===entry.kind+':'+selected;
            if(entry.kind==='personal_best_milestone')
              return a.id==='personal_best_milestone:'+selected+':'+entry.threshold;
            if(entry.kind==='never_give_up')
              return a.type==='never_give_up'||a.id==='never_give_up:'+selected;
            if(entry.kind==='daily_champion_mastery'||entry.kind==='golden_encore'||
               entry.kind.endsWith('_participation')||entry.kind.endsWith('_streak'))
              return a.id===entry.kind+':'+selected+':'+entry.threshold;
            return a.id===entry.id;
          });
          if(matches[0]?.date)detail.append(el('p','achievement-tile-earned-date','EARNED '+matches[0].date));
        }
        if(entry.note&&!concealed&&(!secret||won))detail.append(el('p','achievement-tile-note',entry.note));
        detail.dataset.built='yes';
      }
      detail.hidden=!expanding;
      toggle.setAttribute('aria-expanded',String(expanding));
      toggle.setAttribute('aria-label',concealed?'Mystery achievement':(expanding?'Hide details for ':'Show details for ')+entry.name);
      tile.classList.toggle('achievement-tile-expanded',expanding);
    });
    tile.append(toggle,detail);
    return tile;
  }
  function drawFilters(){
    filters.replaceChildren();
    for(const c of [{id:'all',name:'ALL'},...CATEGORIES]){
      const button=el('button','achievement-filter'+(category===c.id?' is-active':''),c.name);
      button.type='button';button.setAttribute('aria-pressed',category===c.id?'true':'false');
      button.addEventListener('click',()=>{category=c.id;drawFilters();draw();});
      filters.append(button);
    }
  }
  function draw(){
    gallery.replaceChildren();
    const available=entries.filter(e=>e.status==='live');
    const total=selected?available.filter(e=>unlocked(selected,e)).length:0;
    summary.textContent=selected?
      selected+' • '+total+' / '+available.length+' ACTIVE ACHIEVEMENTS UNLOCKED • '+entries.filter(e=>e.status==='planned').length+' COMING SOON':
      'SELECT A PLAYER TO EXPLORE PERSONAL TROPHY PROGRESS • '+available.length+' ACTIVE ACHIEVEMENTS • '+entries.filter(e=>e.status==='planned').length+' COMING SOON';
    for(const group of CATEGORIES){
      if(category!=='all'&&category!==group.id)continue;
      const list=entries.filter(e=>e.category===group.id);
      const section=el('section','achievement-gallery-group');
      section.append(el('h3','achievement-gallery-heading',group.name));
      const grid=el('div','achievement-gallery-grid');
      for(const entry of list)grid.append(createTile(entry));
      section.append(grid);gallery.append(section);
    }
  }
  async function loadData(){
    if(loading)return;
    loading=true;
    try{
      const [rawAwards,rawHistory,rawLegends,rawGold]=await Promise.all([
        fetch('./verified-challenge-awards.json?showcase='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).catch(()=>null),
        fetch('./unified-achievement-history.json?showcase='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})),
        fetch('./legends.json?showcase='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})),
        fetch('./golden-encore-state.json?showcase='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():{}).catch(()=>({})),
      ]);
      if(rawAwards?.schema_version===1&&Array.isArray(rawAwards.awards)){
        const seen=new Set();
        awards=rawAwards.awards.filter(a=>{
          if(!a||typeof a.id!=='string'||!a.id||seen.has(a.id))return false;
          seen.add(a.id);return true;
        });
        plays=Array.isArray(rawAwards.verified_plays)?rawAwards.verified_plays:[];
      }
      history=rawHistory?.schema_version===1?rawHistory:{};
      goldState=rawGold?.schema_version===1?rawGold:{};
      const roster=new Set();
      for(const person of (Array.isArray(rawLegends?.standings)?rawLegends.standings:[]))
        if(person?.player)roster.add(String(person.player).trim().toUpperCase());
      for(const a of awards)if(a?.player)roster.add(String(a.player).trim().toUpperCase());
      for(const p of plays)if(p?.player)roster.add(String(p.player).trim().toUpperCase());
      players=[...roster].filter(Boolean).sort();
      const previous=selected;
      select.replaceChildren(el('option','', 'SELECT A PLAYER'));
      select.firstChild.value='';
      for(const name of players){const option=el('option','',name);option.value=name;select.append(option);}
      selected=players.includes(previous)?previous:'';
      select.value=selected;
    }finally{loading=false;draw();}
  }
  function show(){
    previousFocus=document.activeElement;
    dialog.hidden=false;
    document.body.classList.add('achievement-showcase-open');
    drawFilters();draw();close.focus();loadData();
  }
  function hide(){
    dialog.hidden=true;
    document.body.classList.remove('achievement-showcase-open');
    previousFocus?.focus?.();
  }
  open.addEventListener('click',show);
  close.addEventListener('click',hide);
  dialog.addEventListener('click',e=>{if(e.target===dialog)hide();});
  select.addEventListener('change',()=>{selected=select.value;draw();});
  dialog.addEventListener('keydown',e=>{
    if(e.key==='Escape'){e.preventDefault();hide();return;}
    if(e.key!=='Tab')return;
    const items=[...dialog.querySelectorAll('button:not([disabled]),select:not([disabled])')];
    if(!items.length)return;
    const first=items[0],last=items[items.length-1];
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}
  });
  document.addEventListener('visibilitychange',()=>{if(!document.hidden&&!dialog.hidden)loadData();});
})();
