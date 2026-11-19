import unittest
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

from cloudlog_engine.schema import (
    AuthenticationInfo,
    AuthOutcome,
    CanonicalEvent,
    EventSeverity,
    HTTPInfo,
    SourceInfo,
)


class CanonicalEventTests(unittest.TestCase):
    def make_event(self, **overrides):
        data = {
            "timestamp": datetime(2026, 1, 2, 3, 4, tzinfo=UTC),
            "event_type": "http.request",
            "source": SourceInfo(name="edge-proxy", format="nginx"),
        }
        data.update(overrides)
        return CanonicalEvent(**data)

    def test_timestamp_is_normalized_to_utc(self):
        value = datetime(2026, 1, 2, 8, 34, tzinfo=timezone(timedelta(hours=5, minutes=30)))
        self.assertEqual(self.make_event(timestamp=value).timestamp, datetime(2026, 1, 2, 3, 4, tzinfo=timezone.utc))

    def test_naive_timestamp_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            self.make_event(timestamp=datetime(2026, 1, 2, 3, 4))

    def test_event_id_is_validated_as_uuid(self):
        event = self.make_event()
        self.assertEqual(str(UUID(event.event_id)), event.event_id)
        with self.assertRaisesRegex(ValueError, "valid UUID"):
            self.make_event(event_id="not-a-uuid")

    def test_ip_address_and_cidr_are_normalized(self):
        event = self.make_event(client_ip="2001:0db8:0000:0000:0000:0000:0000:0001")
        self.assertEqual(event.client_ip, "2001:db8::1")
        self.assertEqual(self.make_event(client_ip="192.0.2.0/24").client_ip, "192.0.2.0/24")
        with self.assertRaisesRegex(ValueError, "valid IP address or CIDR"):
            self.make_event(client_ip="not-an-ip")

    def test_http_fields_are_validated_and_normalized(self):
        http = HTTPInfo(
            method="get",
            target="/health",
            status_code=200,
            response_bytes=12,
            duration_ms=1.5,
        )
        self.assertEqual(self.make_event(http=http).http.method, "GET")
        with self.assertRaisesRegex(ValueError, "status_code"):
            HTTPInfo(status_code=700)
        with self.assertRaisesRegex(ValueError, "response_bytes"):
            HTTPInfo(response_bytes=-1)
        with self.assertRaisesRegex(ValueError, "duration_ms"):
            HTTPInfo(duration_ms=float("inf"))

    def test_auth_outcome_and_severity_are_normalized(self):
        info = AuthenticationInfo(outcome="failure", action="login", account="alice")
        event = self.make_event(auth=info, severity=EventSeverity.WARNING)
        self.assertEqual(event.auth.outcome, AuthOutcome.FAILURE)
        self.assertEqual(event.severity, EventSeverity.WARNING)

    def test_attributes_are_json_compatible_and_immutable(self):
        event = self.make_event(attributes={"http": {"tags": ["api", "edge"]}, "count": 3})
        with self.assertRaises(TypeError):
            event.attributes["new"] = "value"
        exported = event.to_dict()
        exported["attributes"]["http"]["tags"].append("mutable-copy")
        self.assertEqual(event.to_dict()["attributes"]["http"]["tags"], ["api", "edge"])

    def test_invalid_json_values_and_non_finite_numbers_are_rejected(self):
        with self.assertRaisesRegex(TypeError, "not JSON-compatible"):
            self.make_event(attributes={"bad": object()})
        with self.assertRaisesRegex(ValueError, "finite"):
            self.make_event(attributes={"bad": float("nan")})

    def test_attribute_depth_and_top_level_size_are_bounded(self):
        nested = {"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": 1}}}}}}}}}
        with self.assertRaisesRegex(ValueError, "nesting"):
            self.make_event(attributes=nested)
        with self.assertRaisesRegex(ValueError, "128 top-level"):
            self.make_event(attributes={str(i): i for i in range(129)})

    def test_to_dict_is_json_friendly(self):
        event = self.make_event(
            severity="info", auth=AuthenticationInfo(outcome="success"),
            http=HTTPInfo(method="post", status_code=201),
        )
        payload = event.to_dict()
        self.assertEqual(payload["schema_version"], "1.0")
        self.assertTrue(payload["timestamp"].endswith("Z"))
        self.assertEqual(payload["severity"], "info")
        self.assertEqual(payload["auth"]["outcome"], "success")
        self.assertEqual(payload["http"]["method"], "POST")


if __name__ == "__main__":
    unittest.main()
