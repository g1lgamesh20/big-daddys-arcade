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
  update arcade_private.player_pass_devices set revoked_at=now() where auth_user_id=v_user;
  if public.arcade_operator_is_active_admin(v_user) then
    raise exception 'Revoked operator device was accepted';
  end if;
  if public.arcade_issue_player_pass('PAC',repeat('b',64),now()+interval '7 days',v_user) is distinct from false then
    raise exception 'Revoked operator was allowed to issue';
  end if;
end;
$test$;
select 'Player Pass PostgreSQL smoke test passed' as result;
