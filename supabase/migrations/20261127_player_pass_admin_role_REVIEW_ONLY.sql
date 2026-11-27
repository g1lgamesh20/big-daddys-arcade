-- REVIEW ONLY: operator authorization tied to verified player/device, not initials.
-- DON must be enrolled through a trusted one-time server-side operator action.
create table if not exists arcade_private.player_pass_admins (
  player_id uuid primary key references arcade_private.player_pass_players(id),
  granted_at timestamptz not null default now(),
  granted_by text not null,
  revoked_at timestamptz
);
alter table arcade_private.player_pass_admins enable row level security;
revoke all on arcade_private.player_pass_admins from public,anon,authenticated;
grant select,insert,update,delete on arcade_private.player_pass_admins to service_role;

-- This check is safe to expose to signed-in clients: it only reveals whether
-- the caller's own verified, active device is associated with an admin player.
create or replace function public.arcade_my_player_pass_role()
returns table(iscored_handle text, is_admin boolean)
language sql stable security definer set search_path = ''
as $$
  select p.iscored_handle,
         exists(select 1 from arcade_private.player_pass_admins a
           where a.player_id=p.id and a.revoked_at is null) as is_admin
  from arcade_private.player_pass_devices d
  join arcade_private.player_pass_players p on p.id=d.player_id
  where d.auth_user_id=(select auth.uid()) and d.revoked_at is null
  limit 1;
$$;
revoke all on function public.arcade_my_player_pass_role() from public,anon;
grant execute on function public.arcade_my_player_pass_role() to authenticated;
-- NOTE: Every admin write endpoint must independently recheck the active
-- device AND player_pass_admins. The role RPC is a UI convenience, not proof
-- a client may submit for authorization.
-- Provision DON's role only after his verified Player Pass is activated.
