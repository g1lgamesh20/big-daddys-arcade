#!/usr/bin/env node
// Offline Edge Function contract tests. No Supabase, Cloudflare, or production calls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const { webcrypto } = require('node:crypto');
const source = fs.readFileSync('supabase/functions/player-pass-redeem/index.ts', 'utf8')
  .replace(/^import .*;\s*$/gm, '')
  .replace(/: Request\b/g, '')
  .replace(/: number\b/g, '')
  .replace(/: string\b/g, '')
  .replace(/: Record<string, unknown>/g, '')
  .replace(/: Uint8Array/g, '')
  .replace(/: Promise<string>/g, '')
  .replace(/let body: \{[^}]+\};/, 'let body;');
const settings = {
  SUPABASE_URL: 'https://example.invalid',
  SUPABASE_SERVICE_ROLE_KEY: 'test-service-key',
  SUPABASE_ANON_KEY: 'test-anon-key',
  PLAYER_PASS_PEPPER: 'test-only-pepper-with-32-or-more-characters',
  TURNSTILE_SECRET_KEY: 'test-secret',
  PLAYER_PASS_OPERATOR_USER_ID: 'approved-operator',
};
async function exercise({ origin='https://g1lgamesh20.github.io', method='POST',
  token='valid-token', initials='PAC', code='PACMAN-AB12',
  challenge='test-challenge', turnstile={success:true,hostname:'g1lgamesh20.github.io'},
  user={id:'player-1',is_anonymous:true,app_metadata:{providers:['anonymous']}},
  failVerify=false, dbFailure=false, noMatchingCode=false, missingPepper=false,
  expectedStatus, expectedRpc=0, expectedVerify }) {
  let handler, rpcCalls=0, verifyCalls=0;
  const context = {
    Deno: { env: { get: name => missingPepper && name === 'PLAYER_PASS_PEPPER' ? undefined : settings[name] }, serve: fn => { handler=fn; } },
    createClient: (_url,key) => key === settings.SUPABASE_ANON_KEY
      ? {auth:{getUser:async value => value === 'valid-token' ? {data:{user}} : {error:'invalid',data:{}}}}
      : {rpc:async () => {rpcCalls++;return dbFailure ? {error:{code:'TEST_ERROR'}} :
          {data:noMatchingCode ? [] : [{player_id:'player-id',iscored_handle:initials}]};}},
    fetch: async (_url, options) => {
      verifyCalls++;
      assert.equal(options.method,'POST');
      return failVerify ? {ok:false} : {ok:true,json:async()=>turnstile};
    },
    crypto:webcrypto, TextEncoder, Uint8Array, Response, URLSearchParams,
    AbortSignal, console,
  };
  vm.runInNewContext(source,context,{filename:'player-pass-redeem/index.ts'});
  const request = new Request('https://example.invalid/functions/v1/player-pass-redeem',{
    method,headers:{origin,'content-type':'application/json',authorization:'Bearer '+token},
    ...(method === 'POST' ? {body:JSON.stringify({initials,code,turnstile_token:challenge})} : {}),
  });
  const response = await handler(request);
  assert.equal(response.status,expectedStatus);
  assert.equal(rpcCalls,expectedRpc,'Unexpected privileged database call');
  if (expectedVerify !== undefined) assert.equal(verifyCalls,expectedVerify,'Unexpected Turnstile request');
  return {verifyCalls,body:await response.json()};
}
(async()=>{
  await exercise({origin:'https://evil.invalid',expectedStatus:403});
  await exercise({token:'invalid',expectedStatus:401});
  await exercise({initials:'DON',expectedStatus:403});
  await exercise({initials:'DON',user:{id:'approved-operator',is_anonymous:true,app_metadata:{providers:['github']}},expectedStatus:403});
  await exercise({initials:'DON',user:{id:'approved-operator',is_anonymous:false,app_metadata:{providers:['github']}},expectedStatus:200,expectedRpc:1});
  await exercise({challenge:'',expectedStatus:403});
  await exercise({turnstile:{success:false,hostname:'g1lgamesh20.github.io'},expectedStatus:403});
  await exercise({turnstile:{success:true,hostname:'evil.invalid'},expectedStatus:403});
  await exercise({failVerify:true,expectedStatus:503});
  await exercise({missingPepper:true,expectedStatus:503,expectedVerify:0});
  await exercise({code:'INVALID',expectedStatus:400,expectedVerify:0});
  await exercise({challenge:'',expectedStatus:403,expectedVerify:0});
  await exercise({dbFailure:true,expectedStatus:429,expectedRpc:1,expectedVerify:1});
  await exercise({noMatchingCode:true,expectedStatus:429,expectedRpc:1,expectedVerify:1});
  await exercise({expectedStatus:200,expectedRpc:1,expectedVerify:1});
  console.log('Player Pass isolated Edge auth/Turnstile contract tests passed.');
})().catch(err=>{console.error(err);process.exitCode=1;});
