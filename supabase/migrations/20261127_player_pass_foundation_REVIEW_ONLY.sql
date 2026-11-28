-- PLAYER PASS STAGE 1: REVIEW-ONLY migration; DO NOT apply until redemption API is ready.
-- Private schema: no direct browser/Data API access.
create schema if not exists arcade_private;
revoke all on schema arcade_private from public, anon, authenticated;
grant usage on schema arcade_private to service_role;

create table if not exists arcade_private.player_pass_players (
  id uuid primary key default gen_random_uuid(),
  iscored_handle text not null unique,
  display_name text,
  created_at timestamptz not null default now(),
  constraint handle_format check (iscored_handle = upper(iscored_handle) and length(iscored_handle) between 1 and 24)
);
create table if not exists arcade_private.player_pass_devices (
  id uuid primary key default gen_random_uuid(),
  player_id uuid not null references arcade_private.player_pass_players(id),
  auth_user_id uuid not null unique references auth.users(id) on delete cascade,
  activated_at timestamptz not null default now(),
  revoked_at timestamptz,
  last_seen_at timestamptz
);
create index if not exists player_pass_devices_player_idx on arcade_private.player_pass_devices(player_id);

create table if not exists arcade_private.player_pass_codes (
  id uuid primary key default gen_random_uuid(),
  player_id uuid not null references arcade_private.player_pass_players(id),
  -- HMAC-SHA256(code, server-only pepper), encoded as 64 lowercase hex chars.
  code_digest text not null unique,
  issued_at timestamptz not null default now(),
  expires_at timestamptz not null,
  redeemed_at timestamptz,
  redeemed_by uuid references auth.users(id),
  revoked_at timestamptz,
  created_by text not null default 'operator',
  constraint digest_format check (code_digest ~ '^[a-f0-9]{64}$'),
  constraint code_expiry check (expires_at > issued_at),
  constraint code_redeem_consistency check ((redeemed_at is null) = (redeemed_by is null))
);
create index if not exists player_pass_codes_player_idx on arcade_private.player_pass_codes(player_id);
create index if not exists player_pass_codes_expiry_idx on arcade_private.player_pass_codes(expires_at);

create table if not exists arcade_private.player_pass_audit (
  id bigint generated always as identity primary key,
  player_id uuid references arcade_private.player_pass_players(id),
  device_id uuid references arcade_private.player_pass_devices(id),
  event_type text not null,
  event_at timestamptz not null default now(),
  details jsonb not null default '{}'::jsonb
);

alter table arcade_private.player_pass_players enable row level security;
alter table arcade_private.player_pass_devices enable row level security;
alter table arcade_private.player_pass_codes enable row level security;
alter table arcade_private.player_pass_audit enable row level security;

-- No policies for anon/authenticated; only trusted backend service role may access.
revoke all on all tables in schema arcade_private from public, anon, authenticated;
grant select, insert, update, delete on all tables in schema arcade_private to service_role;
grant usage, select on all sequences in schema arcade_private to service_role;

comment on schema arcade_private is 'Player Pass secrets and identity bindings; never expose through Supabase Data API';
comment on table arcade_private.player_pass_codes is 'Only HMAC digests, never plaintext activation codes; server-side redemption must lock rows atomically';
