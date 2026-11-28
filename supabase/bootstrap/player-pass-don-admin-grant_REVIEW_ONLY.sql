-- REVIEW ONLY. One-time privileged DON admin grant AFTER successful redemption.
-- Run manually in a trusted SQL session after independently verifying identity.
-- Never expose this operation through the browser or an Edge Function.
-- Replace the UUID placeholder in a PRIVATE copy; never commit a real secret.
begin;
do $bootstrap$
declare
  v_operator uuid := '00000000-0000-0000-0000-000000000000'::uuid;
  v_player uuid;
  v_device uuid;
begin
  if v_operator = '00000000-0000-0000-0000-000000000000'::uuid then
    raise exception 'Set the independently verified operator UUID in a private copy';
  end if;
  if not exists (
    select 1 from auth.users u
    where u.id = v_operator
      and u.is_anonymous is false
      and u.raw_app_meta_data->'providers' ? 'github'
  ) then raise exception 'Operator GitHub identity not verified'; end if;
  select p.id, d.id into strict v_player, v_device
  from arcade_private.player_pass_players p
  join arcade_private.player_pass_devices d on d.player_id = p.id
  where p.iscored_handle = 'DON'
    and d.auth_user_id = v_operator
    and d.revoked_at is null;
  if exists (
    select 1 from arcade_private.player_pass_admins a
    where a.player_id = v_player
  ) then raise exception 'Admin grant already exists; manual review required'; end if;
  insert into arcade_private.player_pass_admins(player_id,granted_by)
  values(v_player,'trusted_one_time_bootstrap');
  insert into arcade_private.player_pass_audit(player_id,device_id,event_type,details)
  values(v_player,v_device,'admin_granted',
    pg_catalog.jsonb_build_object('method','trusted_one_time_bootstrap'));
end;
$bootstrap$;
commit;
-- Operator must verify role and revocation using separate tests.
-- This script cannot be used to issue a first code; that is a separate
-- trusted operation described in docs/player-pass-bootstrap.md.
