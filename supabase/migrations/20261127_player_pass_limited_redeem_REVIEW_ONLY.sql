-- REVIEW ONLY. Apply AFTER private schema migration; do not run before Edge Function review.
-- Database-backed attempt counting survives edge instance restarts.
create table if not exists arcade_private.player_pass_attempts (
  scope text not null check (scope in ('user','ip','handle')),
  subject_hash text not null,
  window_start timestamptz not null,
  attempts integer not null default 0,
  primary key(scope, subject_hash, window_start)
);
alter table arcade_private.player_pass_attempts enable row level security;
revoke all on arcade_private.player_pass_attempts from public,anon,authenticated;
grant select,insert,update,delete on arcade_private.player_pass_attempts to service_role;

-- Return no rows on invalid/replayed/expired codes or exhausted attempt budget.
-- All checks, counting and redemption occur in one transaction.
create or replace function public.arcade_redeem_player_pass_limited(
  p_auth_user_id uuid, p_iscored_handle text, p_code_digest text, p_ip_digest text
) returns table (player_id uuid, device_id uuid, iscored_handle text)
language plpgsql security definer set search_path = ''
as $$
declare
  v_window timestamptz := date_trunc('hour',now());
  v_user_hash text;
  v_user_attempts integer;
  v_ip_attempts integer;
  v_handle_attempts integer;
  v_handle_hash text;
  v_code arcade_private.player_pass_codes%rowtype;
  v_player arcade_private.player_pass_players%rowtype;
  v_device uuid;
begin
  if p_auth_user_id is null or p_iscored_handle is null or
     p_code_digest is null or p_ip_digest is null or
     p_code_digest !~ '^[a-f0-9]{64}$' or p_ip_digest !~ '^[a-f0-9]{64}$'
  then return; end if;
  v_user_hash := md5(p_auth_user_id::text);
  v_handle_hash := md5(upper(trim(p_iscored_handle)));

  -- Serialize requests per user AND per IP, preventing concurrent guess bursts.
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('pass-user:' || v_user_hash,0));
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('pass-ip:' || p_ip_digest,0));
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended('pass-handle:' || v_handle_hash,0));

  insert into arcade_private.player_pass_attempts(scope,subject_hash,window_start,attempts)
    values('user',v_user_hash,v_window,1)
    on conflict(scope,subject_hash,window_start)
    do update set attempts=arcade_private.player_pass_attempts.attempts+1
    returning attempts into v_user_attempts;
  insert into arcade_private.player_pass_attempts(scope,subject_hash,window_start,attempts)
    values('ip',p_ip_digest,v_window,1)
    on conflict(scope,subject_hash,window_start)
    do update set attempts=arcade_private.player_pass_attempts.attempts+1
    returning attempts into v_ip_attempts;
  -- Per-handle throttling prevents anonymous-account churn and distributed
  -- IP changes from bypassing all limits for a targeted player's short code.
  insert into arcade_private.player_pass_attempts(scope,subject_hash,window_start,attempts)
    values('handle',v_handle_hash,v_window,1)
    on conflict(scope,subject_hash,window_start)
    do update set attempts=arcade_private.player_pass_attempts.attempts+1
    returning attempts into v_handle_attempts;
  -- 5 attempts/user, 20/IP, 10/target handle per hour.
  if v_user_attempts > 5 or v_ip_attempts > 20 or v_handle_attempts > 10 then return; end if;

  select * into v_code from arcade_private.player_pass_codes c
    where c.code_digest=p_code_digest for update;
  if not found or v_code.redeemed_at is not null or v_code.revoked_at is not null
     or v_code.expires_at <= now() then return; end if;
  select * into v_player from arcade_private.player_pass_players p
    where p.id=v_code.player_id and p.iscored_handle=upper(trim(p_iscored_handle));
  if not found then return; end if;
  -- Defense in depth: the database independently restricts DON redemption to
  -- a GitHub-backed Auth identity. The Edge Function must additionally
  -- enforce the exact operator UUID from its server-only allowlist.
  if v_player.iscored_handle = 'DON' then
    if not exists (
      select 1 from auth.users u
      where u.id = p_auth_user_id
        and u.is_anonymous is false
        and u.raw_app_meta_data->'providers' ? 'github'
    ) then return; end if;
  end if;
  if not exists(select 1 from auth.users u where u.id=p_auth_user_id) then return; end if;
  if exists(select 1 from arcade_private.player_pass_devices d
    where d.auth_user_id=p_auth_user_id) then return; end if;

  insert into arcade_private.player_pass_devices(player_id,auth_user_id)
    values(v_player.id,p_auth_user_id) returning id into v_device;
  update arcade_private.player_pass_codes c set redeemed_at=now(),redeemed_by=p_auth_user_id
    where c.id=v_code.id;
  insert into arcade_private.player_pass_audit(player_id,device_id,event_type)
    values(v_player.id,v_device,'device_activated');
  return query select v_player.id,v_device,v_player.iscored_handle;
end;
$$;
revoke all on function public.arcade_redeem_player_pass_limited(uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.arcade_redeem_player_pass_limited(uuid,text,text,text) to service_role;
-- NOTE: Before deployment review all SECURITY DEFINER privileges and public schema exposure.
-- NOTE: Rate limits now also apply per target handle across accounts/IPs.
-- CAPTCHA and abuse monitoring remain mandatory for four-character codes.
-- Targeted handle throttling can cause temporary denial of service; operator
-- should have a controlled recovery/issuance path before production activation.
