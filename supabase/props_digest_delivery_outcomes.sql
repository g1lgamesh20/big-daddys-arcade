-- Stage 3: guarded outcome transitions; install manually after review.
-- This SQL NEVER sends a push or creates a reservation.
-- Reserved -> sent requires a real provider notification ID.
-- Reserved -> unknown blocks automated retries after an ambiguous outcome.
-- Sent/unknown are terminal for automated delivery; operator reconciliation is separate.
create or replace function public.arcade_record_props_digest_outcome(
  p_eastern_day date,
  p_outcome text,
  p_notification_id text default null
)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare v_updated date;
begin
  if p_eastern_day is null then raise exception 'Eastern day required'; end if;
  if p_outcome not in ('sent', 'unknown') or p_outcome is null then
    raise exception 'Only sent or unknown outcome permitted';
  end if;
  if p_outcome = 'sent' and
     (p_notification_id is null or length(btrim(p_notification_id)) = 0) then
    raise exception 'Confirmed sent outcome requires OneSignal notification ID';
  end if;
  if p_outcome = 'unknown' and p_notification_id is not null then
    raise exception 'Unknown outcome cannot claim a notification ID';
  end if;
  update public.arcade_props_digest_deliveries
     set status = p_outcome,
         sent_at = case when p_outcome = 'sent' then now() else null end,
         onesignal_notification_id =
           case when p_outcome = 'sent' then btrim(p_notification_id) else null end
   where eastern_day = p_eastern_day and status = 'reserved'
   returning eastern_day into v_updated;
  return v_updated is not null;
end;
$$;
revoke all on function public.arcade_record_props_digest_outcome(date,text,text)
  from public, anon, authenticated;
grant execute on function public.arcade_record_props_digest_outcome(date,text,text)
  to service_role;
-- IMPORTANT: service_role can still update the ledger directly; the future
-- delivery worker must use this RPC and must never reset terminal states.
