/* Authentic iScored artwork, keyed by the game's scorekeeping GameID.
   Do not infer image ID from GameID: community art may have a different ID.
   Only vetted GameLogo paths in game-logo-map.json are ever requested.
   Images load off-DOM; a missing/blocked image leaves the neon title intact. */
(() => {
  'use strict';
  const pending=new WeakMap();
  const validId=value=>/^\d{1,12}$/.test(String(value||''));
  const safeLogo=path=>typeof path==='string' &&
    /^\/(?:community\/)?images\/games\/game\d{1,12}$/.test(path);
  const base='https://www.iscored.info';
  let mapPromise;
  const getMap=()=>{
    if(!mapPromise){
      mapPromise=fetch('./game-logo-map.json',{cache:'no-store'})
        .then(r=>{if(!r.ok)throw Error('Marquee map unavailable');return r.json();})
        .then(data=>data&&typeof data==='object'&&!Array.isArray(data)?data:{})
        .catch(()=>({}));
    }
    return mapPromise;
  };
  window.arcadeShowGameMarquee=(slot,gameId,gameName,className='arcade-game-marquee')=>{
    if(!slot)return;
    const token={};
    pending.set(slot,token);
    const id=String(gameId||'');
    if(!validId(id))return;
    getMap().then(map=>{
      if(pending.get(slot)!==token || !Object.prototype.hasOwnProperty.call(map,id))return;
      const path=map[id];
      if(!safeLogo(path))return;
      const image=new Image();
      image.alt=String(gameName||'Featured game')+' arcade marquee';
      image.className=className;
      image.decoding='async';
      image.onload=()=>{
        if(pending.get(slot)!==token)return;
        if(image.naturalWidth>0&&image.naturalHeight>0)
          slot.insertBefore(image,slot.firstChild);
      };
      image.onerror=()=>{}; // No broken placeholder, no guessed URLs.
      image.src=base+path;
    });
  };
})();