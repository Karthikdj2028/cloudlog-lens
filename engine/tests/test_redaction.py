import unittest

from datetime import datetime, timezone 
from cloudlog_engine.schema import (
    CanonicalEvent, RedactionPolicy, SourceInfo, apply_redaction,
    prepare_event_for_persistence,
)


class RedactionTests(unittest.TestCase):
    def make_event(self):
        return CanonicalEvent(
            timestamp=datetime(2026, 2, 1, tzinfo=timezone.utc),
            event_type="http.request",
            source=SourceInfo(name="proxy", format="jsonl"),
            client_ip="192.0.2.44",
            attributes={
                "headers": {
                    "Authorization": "Bearer top-secret",
                    "Cookie": "session=abc",
                    "Accept": "application/json",
                },
                "attempt": 2,
                "nested": [{"api_key": "key-value"}],
            },
        )

    def test_sensitive_fields_are_redacted_recursively_without_mutation(self):
        original = self.make_event()
        redacted = apply_redaction(original)
        self.assertEqual(redacted.attributes["headers"]["Authorization"], "[REDACTED]")
        self.assertEqual(redacted.attributes["headers"]["Cookie"], "[REDACTED]")
        self.assertEqual(redacted.attributes["headers"]["Accept"], "application/json")
        self.assertEqual(redacted.attributes["nested"][0]["api_key"], "[REDACTED]")
        self.assertEqual(original.attributes["headers"]["Authorization"], "Bearer top-secret")

    def test_client_ip_masking_is_opt_in_and_cidr_based(self):
        original = self.make_event()
        self.assertEqual(apply_redaction(original).client_ip, "192.0.2.44")
        policy = RedactionPolicy(mask_client_ips=True)
        masked = apply_redaction(original, policy)
        self.assertEqual(masked.client_ip, "192.0.2.0/24")
        remasked = apply_redaction(masked, RedactionPolicy(mask_client_ips=True, ipv4_prefix=16))
        self.assertEqual(remasked.client_ip, "192.0.2.0/24")
        ipv6 = CanonicalEvent(
            timestamp=datetime(2026, 2, 1, tzinfo=timezone.utc),
            event_type="auth.failure",
            source=SourceInfo(name="auth", format="syslog"),
            client_ip="2001:db8::1234",
        )
        self.assertEqual(apply_redaction(ipv6, policy).client_ip, "2001:db8::/48")

    def test_custom_sensitive_fields_and_replacement(self):
        policy = RedactionPolicy(sensitive_fields=frozenset({"accept", "attempt"}), replacement="<hidden>")
        redacted = apply_redaction(self.make_event(), policy)
        self.assertEqual(redacted.attributes["headers"]["Accept"], "<hidden>")
        self.assertEqual(redacted.attributes["attempt"], "<hidden>")

    def test_persistence_helper_is_an_explicit_redaction_boundary(self):
        result = prepare_event_for_persistence(self.make_event(), RedactionPolicy(mask_client_ips=True))
        self.assertEqual(result.client_ip, "192.0.2.0/24")
        self.assertEqual(result.attributes["headers"]["Authorization"], "[REDACTED]")


if __name__ == "__main__":
    unittest.main()
