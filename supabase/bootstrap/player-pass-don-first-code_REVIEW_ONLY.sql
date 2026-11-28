-- REVIEW ONLY: trusted one-time DON code insertion, NOT a migration.
-- Run ONLY in a privileged SQL session after independent identity verification,
-- approved roster import, and isolated PostgreSQL integration testing.
-- Generate code/digest privately with scripts/prepare-don-bootstrap.py.
-- NEVER paste the plaintext code or PLAYER_PASS_PEPPER into SQL or GitHub.
-- Replace the digest placeholder in a private copy and use the generator's
-- actual expiry UTC (do not reset the seven-day clock during insertion).
begin;
do $bootstrap_code$
declare
  v_digest text := 'REPLACE_WITH_PRIVATE_64_CHAR_HMAC_DIGEST';
  v_expires_at timestamptz := null; -- replace privately with generated expiry
  v_player uuid;
begin
  if v_digest = 'REPLACE_WITH_PRIVATE_64_CHAR_HMAC_DIGEST'
     or v_digest !~ '^[a-f0-9]{64}$'
     or v_expires_at is null
     or v_expires_at <= now()
     or v_expires_at > now() + interval '7 days'
  then raise exception 'Private digest and valid original expiry required'; end if;

  -- The operator must independently verify the roster's DON entry.
  -- Do not create a player automatically from a self-claimed handle.
  select p.id into strict v_player
  from arcade_private.player_pass_players p
  where p.iscored_handle = 'DON'
  for update;

  -- Fail closed on a previously issued code or active device; do not silently
  -- reset first enrollment. A retry needs manual review of the audit trail.
  if exists (select 1 from arcade_private.player_pass_codes c
             where c.player_id = v_player)
     or exists (select 1 from arcade_private.player_pass_devices d
                where d.player_id = v_player)
  then raise exception 'DON bootstrap previously started; manual review required'; end if;

  insert into arcade_private.player_pass_codes
    (player_id, code_digest, expires_at, created_by)
  values (v_player, v_digest, v_expires_at, 'trusted_one_time_bootstrap');
  insert into arcade_private.player_pass_audit
    (player_id, event_type, details)
  values (v_player, 'bootstrap_code_issued',
          pg_catalog.jsonb_build_object('method','trusted_one_time_bootstrap'));
end;
$bootstrap_code$;
commit;
-- Redemption must occur under DON's allowlisted GitHub Auth session.
-- Only AFTER successful redemption use player-pass-don-admin-grant_REVIEW_ONLY.sql.
