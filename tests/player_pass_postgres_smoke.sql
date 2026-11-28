-- PostgreSQL smoke tests in an isolated GitHub Actions database only.
-- Fixture identities are synthetic; never connect this file to production.
\set ON_ERROR_STOP on
create role anon nologin;
create role authenticated nologin;
create role service_role nologin;
create schema auth;
create table auth.users (
  id uuid primary key,
  is_anonymous boolean not null,
  raw_app_meta_data jsonb not null
);
create function auth.uid() returns uuid language sql stable as $$select null::uuid$$;

\ir ../supabase/migrations/20261127_player_pass_foundation_REVIEW_ONLY.sql
\ir ../supabase/migrations/20261127_player_pass_admin_role_REVIEW_ONLY.sql
\ir ../supabase/migrations/20261127_player_pass_issue_REVIEW_ONLY.sql
\ir ../supabase/migrations/20261127_player_pass_limited_redeem_REVIEW_ONLY.sql

insert into auth.users values
 ('11111111-1111-4111-8111-111111111111',false,'{"providers":["github"]}'),
 ('22222222-2222-4222-8222-222222222222',true,'{"providers":["anonymous"]}');
insert into arcade_private.player_pass_players(iscored_handle) values('DON'),('PAC');
do $test$
declare
  v_don uuid;
  v_user uuid := '11111111-1111-4111-8111-111111111111';
begin
  select id into strict v_don from arcade_private.player_pass_players where iscored_handle='DON';
  if public.arcade_operator_is_active_admin(v_user) then
    raise exception 'Unenrolled operator was accepted';
  end if;
  insert into arcade_private.player_pass_devices(player_id,auth_user_id) values(v_don,v_user);
  if public.arcade_operator_is_active_admin(v_user) then
    raise exception 'Device without grant was accepted';
  end if;
  insert into arcade_private.player_pass_admins(player_id,granted_by) values(v_don,'smoke-test');
  if not public.arcade_operator_is_active_admin(v_user) then
    raise exception 'Verified active operator was rejected';
  end if;
  if public.arcade_issue_player_pass('PAC',repeat('a',64),now()+interval '7 days',v_user) is distinct from true then
    raise exception 'Authorized operator issuance failed';
  end if;
  -- A real redemption: valid PAC code, atomic consumption, and replay rejection.
  insert into arcade_private.player_pass_codes(player_id,code_digest,expires_at,created_by)
  select id,repeat('c',64),now()+interval '7 days','smoke-test'
  from arcade_private.player_pass_players where iscored_handle='PAC';
  if (select count(*) from public.arcade_redeem_player_pass_limited(
    '22222222-2222-4222-8222-222222222222','PAC',repeat('c',64),repeat('d',64))) <> 1 then
    raise exception 'First valid code redemption failed';
  end if;
  if (select count(*) from public.arcade_redeem_player_pass_limited(
    '22222222-2222-4222-8222-222222222222','PAC',repeat('c',64),repeat('d',64))) <> 0 then
    raise exception 'Replayed code was accepted';
  end if;
  if (select count(*) from arcade_private.player_pass_codes
      where code_digest=repeat('c',64) and redeemed_at is not null
        and redeemed_by='22222222-2222-4222-8222-222222222222') <> 1 then
    raise exception 'Code was not atomically marked redeemed';
  end if;
  -- A revoked code cannot activate a new device.
  insert into arcade_private.player_pass_codes(player_id,code_digest,expires_at,revoked_at)
  select id,repeat('e',64),now()+interval '7 days',now()
  from arcade_private.player_pass_players where iscored_handle='PAC';
  if (select count(*) from public.arcade_redeem_player_pass_limited(
    v_user,'PAC',repeat('e',64),repeat('f',64))) <> 0 then
    raise exception 'Revoked code was accepted';
  end if;
  update arcade_private.player_pass_devices set revoked_at=now() where auth_user_id=v_user;
  if public.arcade_operator_is_active_admin(v_user) then
    raise exception 'Revoked operator device was accepted';
  end if;
  if public.arcade_issue_player_pass('PAC',repeat('b',64),now()+interval '7 days',v_user) is distinct from false then
    raise exception 'Revoked operator was allowed to issue';
  end if;
end;
$test$;
-- Separate synthetic users test expiry and rate limits without touching live Auth.
insert into auth.users values
 ('33333333-3333-4333-8333-333333333333',true,'{"providers":["anonymous"]}'),
 ('44444444-4444-4444-8444-444444444444',true,'{"providers":["anonymous"]}');
insert into arcade_private.player_pass_codes(player_id,code_digest,issued_at,expires_at)
select id,repeat('1',64),now()-interval '8 days',now()-interval '1 minute'
from arcade_private.player_pass_players where iscored_handle='PAC';
insert into arcade_private.player_pass_codes(player_id,code_digest,expires_at)
select id,repeat('2',64),now()+interval '7 days'
from arcade_private.player_pass_players where iscored_handle='PAC';
do $limits$
declare
  v_i integer;
  v_count integer;
begin
  if (select count(*) from public.arcade_redeem_player_pass_limited(
    '33333333-3333-4333-8333-333333333333','PAC',repeat('1',64),repeat('3',64))) <> 0 then
    raise exception 'Expired code was accepted';
  end if;
  -- Five invalid guesses exhaust the per-user budget; the sixth is blocked
  -- even if it presents a valid, unredeemed code.
  for v_i in 1..5 loop
    perform * from public.arcade_redeem_player_pass_limited(
      '33333333-3333-4333-8333-333333333333','PAC',
      md5(v_i::text) || md5('guess' || v_i::text),repeat('4',64));
  end loop;
  if (select count(*) from public.arcade_redeem_player_pass_limited(
    '33333333-3333-4333-8333-333333333333','PAC',repeat('2',64),repeat('4',64))) <> 0 then
    raise exception 'Per-user attempt limit failed';
  end if;
  select attempts into strict v_count
  from arcade_private.player_pass_attempts
  where scope='user'
    and subject_hash=md5('33333333-3333-4333-8333-333333333333')
    and window_start=date_trunc('hour',now());
  if v_count <> 7 then raise exception 'Attempt count incorrect: %',v_count; end if;
  -- The shared PAC handle is now at its hourly cap (10 attempts).
  -- Switching accounts or IPs must not bypass that limit.
  if (select count(*) from public.arcade_redeem_player_pass_limited(
    '44444444-4444-4444-8444-444444444444','PAC',repeat('2',64),repeat('5',64))) <> 0 then
    raise exception 'Shared per-handle attempt limit was bypassed';
  end if;
  -- A different player's handle remains independently eligible.
  insert into arcade_private.player_pass_players(iscored_handle) values('GAL');
  insert into arcade_private.player_pass_codes(player_id,code_digest,expires_at)
  select id,repeat('6',64),now()+interval '7 days'
  from arcade_private.player_pass_players where iscored_handle='GAL';
  if (select count(*) from public.arcade_redeem_player_pass_limited(
    '44444444-4444-4444-8444-444444444444','GAL',repeat('6',64),repeat('5',64))) <> 1 then
    raise exception 'Independent player was incorrectly blocked';
  end if;
end;
$limits$;
-- Independent authorization regression: an active device is not enough if
-- its admin grant is revoked, or its GitHub identity is no longer verified.
insert into auth.users values
 ('55555555-5555-4555-8555-555555555555',false,'{"providers":["github"]}');
insert into arcade_private.player_pass_devices(player_id,auth_user_id)
select id,'55555555-5555-4555-8555-555555555555'
from arcade_private.player_pass_players where iscored_handle='DON';
do $revocation$
declare v_operator uuid := '55555555-5555-4555-8555-555555555555';
begin
  -- Existing DON grant from first fixture remains active.
  if not public.arcade_operator_is_active_admin(v_operator) then
    raise exception 'Second verified DON device was incorrectly denied';
  end if;
  update auth.users set raw_app_meta_data='{"providers":["email"]}'
  where id=v_operator;
  if public.arcade_operator_is_active_admin(v_operator) then
    raise exception 'Non-GitHub identity was granted operator privileges';
  end if;
  update auth.users set raw_app_meta_data='{"providers":["github"]}'
  where id=v_operator;
  update arcade_private.player_pass_admins set revoked_at=now()
  where player_id=(select id from arcade_private.player_pass_players where iscored_handle='DON');
  if public.arcade_operator_is_active_admin(v_operator) then
    raise exception 'Revoked admin grant was still authorized';
  end if;
  if public.arcade_issue_player_pass('GAL',repeat('7',64),now()+interval '7 days',v_operator) then
    raise exception 'Revoked admin grant issued a new code';
  end if;
end;
$revocation$;
-- Authorization boundary: public/anonymous clients cannot call privileged RPCs
-- or access the private Player Pass schema, even with a valid Auth session.
do $permissions$
declare
  v_role text;
  v_rpc text;
begin
  foreach v_role in array array['anon','authenticated'] loop
    if pg_catalog.has_schema_privilege(v_role,'arcade_private','USAGE') then
      raise exception '% can access private Player Pass schema',v_role;
    end if;
    foreach v_rpc in array array[
      'public.arcade_redeem_player_pass_limited(uuid,text,text,text)',
      'public.arcade_issue_player_pass(text,text,timestamptz,uuid)',
      'public.arcade_operator_is_active_admin(uuid)'
    ] loop
      if pg_catalog.has_function_privilege(v_role,v_rpc,'EXECUTE') then
        raise exception '% can execute privileged RPC %',v_role,v_rpc;
      end if;
    end loop;
  end loop;
  if not pg_catalog.has_function_privilege(
    'authenticated','public.arcade_my_player_pass_role()','EXECUTE') then
    raise exception 'Authenticated players cannot query their own Player Pass role';
  end if;
  if pg_catalog.has_function_privilege(
    'anon','public.arcade_my_player_pass_role()','EXECUTE') then
    raise exception 'Anonymous public API can query Player Pass role';
  end if;
end;
$permissions$;
-- Device revocation is scoped to one device; it must not disable another
-- still-active, independently enrolled device for the same operator.
do $device_scope$
declare
  v_second uuid := '55555555-5555-4555-8555-555555555555';
  v_first uuid := '11111111-1111-4111-8111-111111111111';
begin
  update arcade_private.player_pass_admins set revoked_at=null
  where player_id=(select id from arcade_private.player_pass_players where iscored_handle='DON');
  if public.arcade_operator_is_active_admin(v_first) then
    raise exception 'Previously revoked first device regained operator privileges';
  end if;
  if not public.arcade_operator_is_active_admin(v_second) then
    raise exception 'Active second device lost privileges due to first-device revocation';
  end if;
end;
$device_scope$;
select 'Player Pass PostgreSQL smoke test passed' as result;
