#!/usr/bin/env python3
"""Concurrent redemption regression against disposable CI PostgreSQL only."""
import concurrent.futures
import subprocess

if __name__ == '__main__':
    def sql(statement):
        return subprocess.run(
            ["psql", "-X", "-A", "-t", "-v", "ON_ERROR_STOP=1", "-c", statement],
            check=True, capture_output=True, text=True,
        ).stdout.strip()

    sql("""INSERT INTO auth.users(id,is_anonymous,raw_app_meta_data) VALUES
    ('66666666-6666-4666-8666-666666666666',true,'{"providers":["anonymous"]}'),
    ('77777777-7777-4777-8777-777777777777',true,'{"providers":["anonymous"]}');
    INSERT INTO arcade_private.player_pass_players(iscored_handle) VALUES('RACE');
    INSERT INTO arcade_private.player_pass_codes(player_id,code_digest,expires_at)
    SELECT id,repeat('8',64),now()+interval '7 days'
    FROM arcade_private.player_pass_players WHERE iscored_handle='RACE';""")

    def redeem(user):
        return sql(f"""SELECT count(*) FROM public.arcade_redeem_player_pass_limited(
    '{user}','RACE',repeat('8',64),repeat('9',64))""")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(redeem, u) for u in (
            "66666666-6666-4666-8666-666666666666",
            "77777777-7777-4777-8777-777777777777",
        )]
        results = [future.result() for future in futures]

    if sorted(results) != ["0", "1"]:
        raise AssertionError(f"Expected one winner and one rejected redemption: {results}")
    devices = sql("""SELECT count(*) FROM arcade_private.player_pass_devices d
    JOIN arcade_private.player_pass_players p ON p.id=d.player_id
    WHERE p.iscored_handle='RACE'""")
    consumed = sql("""SELECT count(*) FROM arcade_private.player_pass_codes
    WHERE code_digest=repeat('8',64) AND redeemed_at IS NOT NULL""")
    if devices != "1" or consumed != "1":
        raise AssertionError(f"Expected one device and one consumed code: {devices}, {consumed}")
    print("Concurrent redemption: exactly one activation, one rejection; code consumed once.")
