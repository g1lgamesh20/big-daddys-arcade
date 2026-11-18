/* iScored game marqu​ee: only reveal a fully loaded image.
   Uses the two image URL paths observed in the public-room HAR.
   If both fail, preserve the existing game title and score, without
   showing a broken image placeholder or inventing replacement artwork. */
(() => {
  'use strict';
  const pending=new WeakMap();
  const validId=(value)=>/^\d{1,12}$/.test(String(value||''));
  window.arcadeShowGameMarquee=(slot,gameId,gameName,className='arcade-game-marquee')=>{
    if(!slot)return;
    const token={};
    pending.set(slot,token);
    const id=String(gameId||'');
    if(!validId(id))return;
    const paths=[
      'https://www.iscored.info/images/games/game'+id,
      'https://www.iscored.info/community/images/games/game'+id
    ];
    let attempt=0;
    const tryNext=()=>{
      if(pending.get(slot)!==token||attempt>=paths.length)return;
      const image=new Image();
      image.alt=String(gameName||'Featured game')+' arcade marquee';
      image.className=className;
      // Important: lazy-loading detached images may not start loading.
      // Preload eagerly, off-DOM, and insert only after onload succeeds.
      image.decoding='async';
      image.onload=()=>{
        if(pending.get(slot)!==token)return;
        if(image.naturalWidth>0&&image.naturalHeight>0)
          slot.insertBefore(image,slot.firstChild);
        else tryNext();
      };
      image.onerror=tryNext;
      image.src=paths[attempt++];
    };
    tryNext();
  };
})();