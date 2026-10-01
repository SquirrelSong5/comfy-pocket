"""Pure-function contract tests for the local session and client checks."""

from __future__ import annotations

import pathlib
import sys
import unittest


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.security import allowed_client, local_client, sign_session, valid_session


class SessionTokenTest(unittest.TestCase):
    SECRET = "test-secret"
    NOW = 1_800_000_000

    def test_signed_token_round_trips_with_fixed_time(self) -> None:
        token = sign_session(self.SECRET, self.NOW)
        self.assertTrue(valid_session(self.SECRET, token, self.NOW))

        expires, signature = token.split(".")
        self.assertEqual(int(expires), self.NOW + 30 * 86400)
        self.assertEqual(len(signature), 64)

    def test_token_is_invalid_after_expiry_and_for_wrong_key(self) -> None:
        token = sign_session(self.SECRET, self.NOW)
        self.assertFalse(valid_session(self.SECRET, token, self.NOW + 30 * 86400 + 1))
        self.assertFalse(valid_session("different-secret", token, self.NOW))

    def test_signature_or_expiry_tampering_is_rejected(self) -> None:
        token = sign_session(self.SECRET, self.NOW)
        expires, signature = token.split(".")
        changed_signature = signature[:-1] + ("0" if signature[-1] != "0" else "1")
        self.assertFalse(valid_session(self.SECRET, expires + "." + changed_signature, self.NOW))
        self.assertFalse(valid_session(self.SECRET, str(int(expires) + 1) + "." + signature, self.NOW))

    def test_malformed_tokens_are_rejected_without_raising(self) -> None:
        for token in (None, "", "not-a-token", "1", "1.2.3", "abc.signature"):
            with self.subTest(token=token):
                self.assertFalse(valid_session(self.SECRET, token, self.NOW))


class ClientAddressTest(unittest.TestCase):
    def test_loopback_detection_accepts_ipv4_and_ipv6_loopback(self) -> None:
        self.assertTrue(local_client("127.0.0.1"))
        self.assertTrue(local_client("127.0.0.2"))
        self.assertTrue(local_client("::1"))

    def test_loopback_detection_rejects_remote_and_invalid_addresses(self) -> None:
        self.assertFalse(local_client("192.0.2.10"))
        self.assertFalse(local_client("2001:db8::10"))
        self.assertFalse(local_client("not-an-ip"))

    def test_allowed_client_matches_ipv4_and_ipv6_networks(self) -> None:
        self.assertTrue(allowed_client("192.0.2.10", ["192.0.2.0/24"]))
        self.assertTrue(allowed_client("2001:db8::10", ["2001:db8::/64"]))
        self.assertTrue(allowed_client("127.0.0.1", ["10.0.0.0/8", "127.0.0.0/8"]))
        self.assertFalse(allowed_client("192.0.3.10", ["192.0.2.0/24"]))

    def test_invalid_remote_or_network_is_denied(self) -> None:
        self.assertFalse(allowed_client("not-an-ip", ["0.0.0.0/0"]))
        self.assertFalse(allowed_client("192.0.2.10", ["not-a-network"]))


if __name__ == "__main__":
    unittest.main()
