-- REVIEW ONLY: service-role-only issuance RPC; private schema is NOT exposed in PostgREST.
-- Operator authorization is verified in the Edge Function before invoking this RPC.
create or replace function public.arcade_issue_player_pass(
  p_handle text, p_digest text, p_expires_at timestamptz, p_operator_id uuid
) returns boolean
language plpgsql security definer set search_path = ''
as $$
declare v_player uuid;
begin
  if p_handle is null or p_digest is null or p_expires_at is null or p_digest !~ '^[a-f0-9]{64}$'
     or p_operator_id is null or p_expires_at <= now()
     or p_expires_at > now() + interval '8 days' then
    return false;
  end if;
  select id into v_player from arcade_private.player_pass_players
    where iscored_handle = upper(trim(p_handle));
  if v_player is null then return false; end if;
  insert into arcade_private.player_pass_codes
    (player_id,code_digest,expires_at,created_by)
    values(v_player,p_digest,p_expires_at,p_operator_id::text);
  insert into arcade_private.player_pass_audit(player_id,event_type,details)
    values(v_player,'code_issued',pg_catalog.jsonb_build_object('operator_id',p_operator_id));
  return true;
end;
$$;
revoke all on function public.arcade_issue_player_pass(text,text,timestamptz,uuid)
  from public,anon,authenticated;
grant execute on function public.arcade_issue_player_pass(text,text,timestamptz,uuid)
  to service_role;
