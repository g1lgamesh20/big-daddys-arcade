-- Staged only: review and deploy explicitly in Supabase SQL Editor.
-- No client access to registrations, codes or audit. All functions run only
-- through a protected, service-role Edge Function after Turnstile verification.
create table if not exists public.arcade_registration_codes (
  code_digest text primary key check (code_digest ~ '^[a-f0-9]{64}$'),
  player_initials text not null check (player_initials ~ '^[A-Z0-9 ]{1,3}$' and btrim(player_initials) <> ''),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  redeemed_at timestamptz,
  redeemed_device_digest text,
  constraint code_expiry_after_creation check (expires_at > created_at)
);
create table if not exists public.arcade_verified_devices (
  device_digest text primary key check (device_digest ~ '^[a-f0-9]{64}$'),
  player_initials text not null check (player_initials ~ '^[A-Z0-9 ]{1,3}$' and btrim(player_initials) <> ''),
  linked_at timestamptz not null default now(),
  revoked_at timestamptz
);
create table if not exists public.arcade_registration_attempts (
  id bigint generated always as identity primary key,
  device_digest text not null,
  attempted_at timestamptz not null default now()
);
create index if not exists arcade_registration_attempts_lookup
  on public.arcade_registration_attempts(device_digest, attempted_at);

alter table public.arcade_registration_codes enable row level security;
alter table public.arcade_verified_devices enable row level security;
alter table public.arcade_registration_attempts enable row level security;
revoke all on public.arcade_registration_codes from public, anon, authenticated;
revoke all on public.arcade_verified_devices from public, anon, authenticated;
revoke all on public.arcade_registration_attempts from public, anon, authenticated;

-- Atomic single-use redemption, rate limiting and binding. This is NEVER
-- exposed as an anonymous/public RPC; only Edge Function service role can call.
create or replace function public.arcade_redeem_registration(
  p_code_digest text, p_device_digest text
) returns table (linked_player text, redeemed boolean, outcome text)
language plpgsql security definer
set search_path = pg_catalog, public
as $$
declare
  v_code public.arcade_registration_codes%rowtype;
  v_existing public.arcade_verified_devices%rowtype;
begin
  if p_code_digest !~ '^[a-f0-9]{64}$'
     or p_device_digest !~ '^[a-f0-9]{64}$' then
    return query select ''::text, false, 'invalid'::text; return;
  end if;
  -- Existing device may not switch players via a second code.
  select * into v_existing from public.arcade_verified_devices
   where device_digest=p_device_digest for update;
  if found and v_existing.revoked_at is null then
    return query select v_existing.player_initials, false, 'already_linked'::text;
    return;
  end if;
  -- An attempt counts even if the code is wrong; enforce fixed window.
  insert into public.arcade_registration_attempts(device_digest) values(p_device_digest);
  if (select count(*) from public.arcade_registration_attempts
      where device_digest=p_device_digest
      and attempted_at > now()-interval '1 hour') > 5 then
    return query select ''::text,false,'rate_limited'::text; return;
  end if;
  select * into v_code from public.arcade_registration_codes
   where code_digest=p_code_digest for update;
  if not found or v_code.redeemed_at is not null or v_code.expires_at<=now() then
    return query select ''::text,false,'invalid_or_expired'::text; return;
  end if;
  insert into public.arcade_verified_devices(device_digest,player_initials)
    values(p_device_digest,v_code.player_initials)
    on conflict(device_digest) do update set
      player_initials=excluded.player_initials,linked_at=now(),revoked_at=null;
  update public.arcade_registration_codes
    set redeemed_at=now(),redeemed_device_digest=p_device_digest
    where code_digest=p_code_digest;
  return query select v_code.player_initials,true,'linked'::text;
end;
$$;
revoke all on function public.arcade_redeem_registration(text,text)
  from public, anon, authenticated;
grant execute on function public.arcade_redeem_registration(text,text)
  to service_role;
