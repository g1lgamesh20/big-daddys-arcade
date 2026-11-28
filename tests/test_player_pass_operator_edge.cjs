#!/usr/bin/env node
// Isolated operator endpoint tests: never contacts Supabase or production.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {webcrypto}=require('node:crypto');
const source=fs.readFileSync('supabase/functions/player-pass-operator/index.ts','utf8')
 .replace(/^import .*;\s*$/gm,'')
 .replace(/: Request\b/g,'').replace(/: number\b/g,'')
 .replace(/: Record<string, unknown>/g,'').replace(/: string\b/g,'')
 .replace(/: Promise<string>/g,'').replace(/let body: Record<string, unknown>;/,'let body;');
const env={SUPABASE_URL:'https://example.invalid',SUPABASE_ANON_KEY:'anon',
 SUPABASE_SERVICE_ROLE_KEY:'service',PLAYER_PASS_PEPPER:'test-only-pepper-with-more-than-32-characters',
 PLAYER_PASS_OPERATOR_USER_ID:'don-id'};
async function check({origin='https://g1lgamesh20.github.io',token='valid',user={
 id:'don-id',is_anonymous:false,app_metadata:{providers:['github']}},role=true,
 initials='PAC',prefix='PACMAN',issued=true,expected,expectedIssue=0}){
 let handler,issuedCalls=0;
 const ctx={Deno:{env:{get:k=>env[k]},serve:fn=>{handler=fn;}},
  createClient:(_url,key)=>key==='anon'?{auth:{getUser:async t=>
    t==='valid'?{data:{user},error:null}:{data:{},error:{message:'invalid'}}}}:
    {rpc:async(name)=>{
      if(name==='arcade_operator_is_active_admin')return {data:role,error:null};
      if(name==='arcade_issue_player_pass'){issuedCalls++;return {data:issued,error:null};}
      throw Error('unexpected RPC '+name);
    }},
  crypto:webcrypto,TextEncoder,Uint8Array,Response,URLSearchParams,console,Date};
 vm.runInNewContext(source,ctx,{filename:'player-pass-operator/index.ts'});
 const response=await handler(new Request('https://example.invalid/functions/v1/player-pass-operator',{
 method:'POST',headers:{origin,'content-type':'application/json',authorization:'Bearer '+token},
 body:JSON.stringify({initials,prefix})}));
 assert.equal(response.status,expected);
 assert.equal(issuedCalls,expectedIssue,'Unexpected privileged issuance');
 if(expected===200){const body=await response.json();assert.match(body.code,/^PACMAN-[A-Z2-9]{4}$/);}
}
(async()=>{
 await check({origin:'https://evil.invalid',expected:403});
 await check({token:'invalid',expected:403});
 await check({user:{id:'other',is_anonymous:false,app_metadata:{providers:['github']}},expected:403});
 await check({user:{id:'don-id',is_anonymous:true,app_metadata:{providers:['github']}},expected:403});
 await check({user:{id:'don-id',is_anonymous:false,app_metadata:{providers:['anonymous']}},expected:403});
 await check({role:false,expected:403});
 await check({initials:'BAD!',expected:400});
 await check({prefix:'UNAPPROVED',expected:400});
 await check({issued:false,expected:404,expectedIssue:1});
 await check({expected:200,expectedIssue:1});
 console.log('Player Pass isolated operator authorization tests passed.');
})().catch(e=>{console.error(e);process.exitCode=1;});
