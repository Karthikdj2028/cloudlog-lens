import io
import unittest
from pathlib import Path

from cloudlog_engine.ingestion import IngestionIssueCode, parse_stream
from cloudlog_engine.ingestion.models import SourceLine
from cloudlog_engine.parsers import ApacheCombinedParser, JSONLinesParser, NginxCombinedParser


FIXTURES = Path(__file__).resolve().parents[2] / "tests" / "fixtures"


class ParserTests(unittest.TestCase):
    def test_apache_combined_fixture_and_malformed_line(self):
        parser = ApacheCombinedParser(source_name="apache-edge")
        lines = (FIXTURES / "apache_combined.log").read_bytes()
        results = list(parse_stream(io.BytesIO(lines), parser))
        self.assertEqual(len(results), 3)
        event = results[0].event
        self.assertEqual(event.source.format, "apache.combined")
        self.assertEqual(event.source.name, "apache-edge")
        self.assertEqual(event.client_ip, "203.0.113.10")
        self.assertEqual(event.user, "alice")
        self.assertEqual(event.http.method, "GET")
        self.assertEqual(event.http.status_code, 200)
        self.assertEqual(results[1].event.severity.value, "warning")
        self.assertEqual(results[2].issue.code, IngestionIssueCode.MALFORMED_RECORD)

    def test_nginx_combined_fixture(self):
        parser = NginxCombinedParser(source_name="nginx-gateway")
        results = list(parse_stream(io.BytesIO((FIXTURES / "nginx_combined.log").read_bytes()), parser))
        self.assertEqual(results[0].event.source.format, "nginx.combined")
        self.assertEqual(results[0].event.http.target, "/api/items")
        self.assertEqual(results[0].event.http.response_bytes, 321)
        self.assertEqual(results[1].issue.code, IngestionIssueCode.MALFORMED_RECORD)

    def test_access_parser_classifies_invalid_timestamp_and_ip(self):
        parser = ApacheCombinedParser()
        invalid_timestamp = SourceLine(
            1, 0,
            '192.0.2.1 - - [not-a-date] "GET / HTTP/1.1" 200 1 "-" "test"',
        )
        invalid_ip = SourceLine(
            2, 80,
            'not-an-ip - - [24/Nov/2026:10:00:00 +0000] "GET / HTTP/1.1" 200 1 "-" "test"',
        )
        self.assertEqual(
            parser.parse_line(invalid_timestamp).issue.code,
            IngestionIssueCode.INVALID_TIMESTAMP,
        )
        self.assertEqual(
            parser.parse_line(invalid_ip).issue.code,
            IngestionIssueCode.INVALID_IP,
        )

    def test_jsonl_fixture_maps_fields_and_redacts_sensitive_attributes(self):
        parser = JSONLinesParser(source_name="app-json")
        results = list(parse_stream(io.BytesIO((FIXTURES / "events.jsonl").read_bytes()), parser))
        event = results[0].event
        self.assertEqual(event.source.name, "app-json")
        self.assertEqual(event.event_type, "auth.failure")
        self.assertEqual(event.auth.outcome.value, "failure")
        self.assertEqual(event.attributes["password"], "[REDACTED]")
        self.assertEqual(event.attributes["request_id"], "fixture-001")
        self.assertEqual(results[1].event.http.method, "GET")
        self.assertEqual(results[2].issue.code, IngestionIssueCode.INVALID_JSON)

    def test_jsonl_classifies_timestamp_ip_and_duplicate_key_errors(self):
        parser = JSONLinesParser()
        cases = [
            ('{"timestamp":"2026-11-24T10:00:00","event_type":"test"}', IngestionIssueCode.INVALID_TIMESTAMP),
            ('{"timestamp":"2026-11-24T10:00:00Z","client_ip":"999.1.1.1"}', IngestionIssueCode.INVALID_IP),
            ('{"timestamp":"2026-11-24T10:00:00Z","x":1,"x":2}', IngestionIssueCode.INVALID_JSON),
        ]
        for text, expected in cases:
            with self.subTest(expected=expected):
                result = parser.parse_line(SourceLine(1, 0, text))
                self.assertEqual(result.issue.code, expected)

    def test_blank_lines_are_skipped_not_reported_as_malformed(self):
        results = list(parse_stream(io.BytesIO(b"\n  \n"), JSONLinesParser()))
        self.assertTrue(all(result.is_skipped for result in results))


if __name__ == "__main__":
    unittest.main()
