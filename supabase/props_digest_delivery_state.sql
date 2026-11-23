-- Stage 3: run ONCE in Supabase SQL editor after review.
-- Private server-side delivery ledger. Do not grant anon/authenticated access.
create table if not exists public.arcade_props_digest_deliveries (
  eastern_day date primary key,
  status text not null default 'reserved'
    check (status in ('reserved', 'sent', 'unknown')),
  idempotency_key text not null unique,
  reserved_at timestamptz not null default now(),
  sent_at timestamptz,
  onesignal_notification_id text,
  check (status <> 'sent' or sent_at is not null)
);
alter table public.arcade_props_digest_deliveries enable row level security;
revoke all on table public.arcade_props_digest_deliveries from public, anon, authenticated;
grant select, insert, update on table public.arcade_props_digest_deliveries to service_role;
-- Do NOT create an automatic expiry or reset: uncertain sends must not retry blindly.
