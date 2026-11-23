-- Stage 3: Review and run once in Supabase SQL Editor.
-- Atomic, fail-closed reservation. This function DOES NOT send notifications.
-- It returns true only for the first successful reservation for a date.
-- A reservation is permanent until explicitly investigated by the operator.
create or replace function public.arcade_reserve_props_digest(p_eastern_day date)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_key text;
  v_inserted date;
begin
  if p_eastern_day is null then
    raise exception 'Eastern day required';
  end if;
  -- Prevent future/old accidental claims. The caller must target yesterday ET.
  if p_eastern_day <> ((now() at time zone 'America/New_York')::date - 1) then
    raise exception 'Only previous Eastern day may be reserved';
  end if;
  v_key := 'big-daddys-arcade:give-props:' || p_eastern_day::text;
  insert into public.arcade_props_digest_deliveries
    (eastern_day, status, idempotency_key)
  values (p_eastern_day, 'reserved', v_key)
  on conflict do nothing
  returning eastern_day into v_inserted;
  return v_inserted is not null;
end;
$$;
revoke all on function public.arcade_reserve_props_digest(date) from public;
revoke all on function public.arcade_reserve_props_digest(date) from anon, authenticated;
grant execute on function public.arcade_reserve_props_digest(date) to service_role;
-- Security note: service_role has elevated database access; keep its key in
-- GitHub Actions secrets only. Do not invoke this function from the PWA.
