-- Dedicated, isolated table for live uniqueness/concurrency tests.
-- NEVER uses the real delivery ledger or reserves a real notification day.
create table if not exists public.arcade_props_concurrency_probe (
  probe_key text primary key,
  created_at timestamptz not null default now()
);
alter table public.arcade_props_concurrency_probe enable row level security;
revoke all on public.arcade_props_concurrency_probe from public, anon, authenticated;
grant select, insert, delete on public.arcade_props_concurrency_probe to service_role;
-- Optional cleanup after tests are complete:
-- drop table public.arcade_props_concurrency_probe;
