-- Stage 1 review-only: atomic code redemption.
-- Run only after the private schema migration and after the backend Edge Function
-- is ready. This function must never be executable by anon/authenticated.
-- The Edge Function must verify the caller's Supabase JWT using auth.getUser()
-- and pass that verified user's ID, not an arbitrary browser-provided ID.
create or replace function public.arcade_redeem_player_pass(
  p_auth_user_id uuid,
  p_iscored_handle text,
  p_code_digest text
) returns table (player_id uuid, device_id uuid, iscored_handle text)
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_code arcade_private.player_pass_codes%rowtype;
  v_player arcade_private.player_pass_players%rowtype;
  v_device_id uuid;
begin
  if p_auth_user_id is null or p_iscored_handle is null or p_code_digest !~ '^[a-f0-9]{64}$' then
    raise exception 'Invalid player pass';
  end if;
  select * into v_code from arcade_private.player_pass_codes c
    where c.code_digest = p_code_digest for update;
  if not found or v_code.revoked_at is not null or v_code.redeemed_at is not null
     or v_code.expires_at <= now() then
    raise exception 'Invalid player pass';
  end if;
  select * into v_player from arcade_private.player_pass_players p
    where p.id = v_code.player_id and p.iscored_handle = upper(trim(p_iscored_handle));
  if not found then raise exception 'Invalid player pass'; end if;
  if not exists (select 1 from auth.users u where u.id = p_auth_user_id) then
    raise exception 'Invalid player pass';
  end if;
  if exists (select 1 from arcade_private.player_pass_devices d where d.auth_user_id = p_auth_user_id) then
    raise exception 'Device already registered';
  end if;
  insert into arcade_private.player_pass_devices(player_id,auth_user_id)
    values(v_player.id,p_auth_user_id) returning id into v_device_id;
  update arcade_private.player_pass_codes c
    set redeemed_at=now(), redeemed_by=p_auth_user_id where c.id=v_code.id;
  insert into arcade_private.player_pass_audit(player_id,device_id,event_type)
    values(v_player.id,v_device_id,'device_activated');
  return query select v_player.id,v_device_id,v_player.iscored_handle;
end;
$$;
revoke all on function public.arcade_redeem_player_pass(uuid,text,text) from public,anon,authenticated;
grant execute on function public.arcade_redeem_player_pass(uuid,text,text) to service_role;
-- IMPORTANT: SECURITY DEFINER can bypass RLS. Only service_role may execute.
-- No user-supplied auth ID should be trusted by the calling Edge Function.
