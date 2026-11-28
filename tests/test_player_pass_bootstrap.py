"""Offline tests for the DON bootstrap generator. Run: python3 -m unittest discover -s tests -p 'test_player_pass_bootstrap.py'"""
import importlib.util
import pathlib
import re
import unittest
from datetime import datetime, timedelta, timezone

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "prepare-don-bootstrap.py"
spec = importlib.util.spec_from_file_location("player_pass_bootstrap", SCRIPT)
bootstrap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bootstrap)

class BootstrapTests(unittest.TestCase):
    def test_code_and_digest(self):
        import hashlib
        import hmac
        pepper = "test-secret-only-" + "x" * 40
        code, digest, expires = bootstrap.generate(pepper)
        self.assertRegex(code, r"^PACMAN-[A-HJ-NP-Z2-9]{4}$")
        self.assertEqual(digest, hmac.new(pepper.encode(), code.encode(), hashlib.sha256).hexdigest())
        self.assertTrue(datetime.now(timezone.utc) + timedelta(days=6, hours=23) < expires)
        self.assertTrue(expires < datetime.now(timezone.utc) + timedelta(days=7, minutes=1))

    def test_reject_short_secret(self):
        with self.assertRaises(ValueError):
            bootstrap.generate("short")

    def test_independent_codes(self):
        pepper = "x" * 40
        codes = {bootstrap.generate(pepper)[0] for _ in range(30)}
        self.assertGreater(len(codes), 1)

if __name__ == "__main__":
    unittest.main()
