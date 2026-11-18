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
    {id:'special',name:'❓ Special Achievements'},
  ];
  const entries=[];
  const add=(id,category,emoji,name,description,kind,threshold=0,status='live',note='')=>{
    entries.push({id,category,emoji,name,description,kind,threshold,status,note});
  };
  add('daily_champion','daily','⚔️','Beat the Champion',
      'Beat the day’s locked starting champion score with a qualifying approved Daily Challenge score. Multiple players can win on the same day.',
      'daily_champion',0,'live','Requires a pre-event locked champion score. First place in iScored is separate.');
  add('thursday_champion','thursday','🏆','Thursday Champion',
      'Finish with the highest qualifying score for the Thursday Arcade Challenge.','thursday_champion');
  add('gotm_champion','monthly','🌟','Game of the Month Champion',
      'Finish with the top qualifying score in the revealed monthly competition.','gotm_champion');
  add('monthly_average','monthly','🎯','Beat the Average',
      'Beat the month’s locked average-based target.','monthly_average',0,'planned',
      'Concept approved; separate achievement awarding is not active yet.');
  for(const [place,name,emoji] of [[1,'Monthly Gold','🥇'],[2,'Monthly Silver','🥈'],[3,'Monthly Bronze','🥉']]){
    add('monthly_podium_'+place,'monthly',emoji,name,
      'Finish in '+(place===1?'first':place===2?'second':'third')+' place in a finalized Game of the Month.',
      'monthly_podium',place,'planned','Monthly podium-specific trophy awarding is still planned.');
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
  for(const [threshold,name,emoji] of [[1,'Golden Encore','🥇'],[5,'Gold Rush','🔥'],[10,'Untouchable','👑']])
    add('golden_encore:'+threshold,'gold',emoji,name,
        'Improve an already-held Gold-leading score on '+threshold+' qualifying occasion'+(threshold===1?'':'s')+'. First-time Gold does not count.',
        'golden_encore',threshold);
  add('easter_egg','special','❓','Easter Egg',"It's a Secret to Everybody.",'easter_egg',0,
      'planned','Secret discovery achievement. Unlocking mechanism is not displayed.');

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
    if(entry.kind==='golden_encore')
      return playerAwards.some(a=>a.id==='golden_encore:'+player+':'+entry.threshold);
    if(entry.kind.endsWith('_participation')||entry.kind.endsWith('_streak'))
      return playerAwards.some(a=>a.id===entry.kind.replace('_participation','_participation').replace('_streak','_streak')+':'+player+':'+entry.threshold);
    return false;
  }
  function progress(player,entry){
    if(entry.kind==='golden_encore')return goldImprovements(player);
    if(entry.kind.endsWith('_participation'))return count(player,entry.kind.split('_')[0]);
    if(entry.kind.endsWith('_streak'))return streak(player,entry.kind.split('_')[0]);
    return 0;
  }
  function createTile(entry){
    const won=Boolean(selected)&&unlocked(selected,entry);
    const planned=entry.status==='planned';
    const tile=el('article','achievement-tile'+(won?' achievement-tile-earned':'')+(planned?' achievement-tile-planned':''));
    const upper=el('div','achievement-tile-top');
    const glyph=el('span','achievement-tile-glyph',entry.emoji);glyph.setAttribute('aria-hidden','true');
    const status=el('span','achievement-tile-status',planned?'COMING SOON':won?'★ UNLOCKED':'🔒 LOCKED');
    upper.append(glyph,status);
    const title=el('h4','achievement-tile-name',entry.name);
    const desc=el('p','achievement-tile-desc',entry.description);
    tile.append(upper,title,desc);
    if(entry.threshold && !planned){
      const n=selected?progress(selected,entry):0;
      const line=el('p','achievement-tile-progress',
        selected?'PROGRESS: '+Math.min(n,entry.threshold)+' / '+entry.threshold:'SELECT A PLAYER TO SEE PROGRESS');
      tile.append(line);
      if(selected){
        const bar=el('div','achievement-tile-track');
        bar.setAttribute('role','progressbar');bar.setAttribute('aria-label',entry.name+' progress');
        bar.setAttribute('aria-valuemin','0');bar.setAttribute('aria-valuemax',String(entry.threshold));
        bar.setAttribute('aria-valuenow',String(Math.min(n,entry.threshold)));
        const fill=el('div','achievement-tile-fill');
        fill.style.width=(Math.min(100,100*n/entry.threshold))+'%';
        bar.append(fill);tile.append(bar);
      }
    }
    if(won){
      const matches=uniqueAwards(selected).filter(a=>{
        if(entry.kind==='daily_champion'||entry.kind==='thursday_champion'||entry.kind==='gotm_champion')
          return a.type===entry.kind;
        return a.id===entry.id.replace(':',':'+selected+':');
      });
      const first=matches[0];
      if(first?.date)tile.append(el('p','achievement-tile-earned-date','EARNED '+first.date));
    }
    if(entry.note)tile.append(el('p','achievement-tile-note',entry.note));
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
