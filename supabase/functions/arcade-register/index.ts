// Staged only. Deploy only after Supabase migration + security review.
// This endpoint redeems an operator-issued code once and links the current
// device to an iScored player's initials. No password or recurring sign-in.
// Existing Trash Talk and Give Props continue working unchanged.
//
// Secrets: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, TURNSTILE_SECRET_KEY
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';

const ORIGIN='https://g1lgamesh20.github.io';
const CORS={
  'Access-Control-Allow-Origin':ORIGIN,
  'Access-Control-Allow-Headers':'authorization, x-client-info, apikey, content-type',
  'Access-Control-Allow-Methods':'POST, OPTIONS',
  'Content-Type':'application/json',
  'Cache-Control':'no-store'
};
function reply(status:number,body:Record<string,unknown>){
  return new Response(JSON.stringify(body),{status,headers:CORS});
}
async function sha256(value:string){
  const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
}
Deno.serve(async request=>{
  if(request.method==='OPTIONS')return new Response(null,{headers:CORS});
  if(request.method!=='POST')return reply(405,{success:false,error:'POST required'});
  if(request.headers.get('Origin')!==ORIGIN)return reply(403,{success:false,error:'Invalid origin'});
  const url=Deno.env.get('SUPABASE_URL');
  const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  const captchaSecret=Deno.env.get('TURNSTILE_SECRET_KEY');
  if(!url||!key||!captchaSecret)return reply(503,{success:false,error:'Registration not configured'});
  let data:Record<string,unknown>;
  try{
    if(Number(request.headers.get('content-length')||0)>4096)
      return reply(413,{success:false,error:'Payload too large'});
    data=await request.json();
  }catch{return reply(400,{success:false,error:'Invalid request'});}
  const code=typeof data?.code==='string'?data.code.trim().toUpperCase():'';
  const device=typeof data?.device_token==='string'?data.device_token:'';
  const captcha=typeof data?.turnstile_token==='string'?data.turnstile_token:'';
  if(!/^[A-Z2-7]{20,40}$/.test(code)||!/^[a-f0-9]{64}$/.test(device)
    ||captcha.length<10||captcha.length>2048)
    return reply(400,{success:false,error:'Invalid code or device'});
  const response=await fetch('https://challenges.cloudflare.com/turnstile/v0/siteverify',{
    method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:new URLSearchParams({secret:captchaSecret,response:captcha})
  }).catch(()=>null);
  if(!response?.ok)return reply(503,{success:false,error:'Verification unavailable'});
  let verified:Record<string,unknown>;
  try{verified=await response.json()}catch{return reply(503,{success:false,error:'Verification unavailable'});}
  // Validate Turnstile hostname; siteverify success alone isn't enough.
  if(verified.success!==true||verified.hostname!=='g1lgamesh20.github.io')
    return reply(403,{success:false,error:'Verification failed'});
  const client=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data:rows,error}=await client.rpc('arcade_redeem_registration',{
    p_code_digest:await sha256(code),
    p_device_digest:await sha256(device)
  });
  if(error)return reply(503,{success:false,error:'Registration unavailable'});
  const result=Array.isArray(rows)?rows[0]:null;
  if(result?.redeemed===true&&typeof result.linked_player==='string'){
    return reply(200,{success:true,player:result.linked_player});
  }
  // Do not identify whether a valid code exists.
  return reply(result?.outcome==='rate_limited'?429:400,
    {success:false,error:result?.outcome==='already_linked'
      ?'This device is already registered. Contact the arcade operator to change it.'
      :'Code invalid, expired, or already used.'});
});
