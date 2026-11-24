import io
import unittest

from cloudlog_engine.ingestion import IngestionIssue, IngestionIssueCode, SourceLine
from cloudlog_engine.ingestion.reader import iter_source_lines


class StreamingReaderTests(unittest.TestCase):
    def test_reads_lines_across_chunk_boundaries_with_offsets(self):
        records = list(iter_source_lines(io.BytesIO(b"one\r\ntwo\nthree"), chunk_size=2))
        self.assertEqual(
            records,
            [
                SourceLine(1, 0, "one"),
                SourceLine(2, 5, "two"),
                SourceLine(3, 9, "three"),
            ],
        )

    def test_empty_lines_are_preserved_for_parser_skip_accounting(self):
        records = list(iter_source_lines(io.BytesIO(b"\nvalue\n")))
        source_texts = [record.text for record in records if isinstance(record, SourceLine)]
        self.assertEqual(source_texts, ["", "value"])

    def test_oversized_line_is_discarded_and_reader_recovers(self):
        records = list(
            iter_source_lines(
                io.BytesIO(b"123456\nnext\n"),
                chunk_size=2,
                max_line_bytes=5,
            )
        )
        self.assertIsInstance(records[0], IngestionIssue)
        self.assertEqual(records[0].code, IngestionIssueCode.LINE_TOO_LARGE)
        self.assertEqual(records[0].line_number, 1)
        self.assertEqual(records[0].byte_offset, 0)
        self.assertEqual(records[1], SourceLine(2, 7, "next"))

    def test_invalid_utf8_is_classified_and_next_line_is_read(self):
        records = list(iter_source_lines(io.BytesIO(b"bad-\xff\nvalid\n")))
        self.assertEqual(records[0].code, IngestionIssueCode.INVALID_ENCODING)
        self.assertEqual(records[1], SourceLine(2, 6, "valid"))

    def test_utf8_bom_is_removed_from_first_record_only(self):
        records = list(iter_source_lines(io.BytesIO(b"\xef\xbb\xbffirst\n\xef\xbb\xbfsecond")))
        self.assertEqual(records[0].text, "first")
        self.assertEqual(records[1].text, "\ufeffsecond")

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "chunk_size"):
            list(iter_source_lines(io.BytesIO(b"x"), chunk_size=0))
        with self.assertRaisesRegex(ValueError, "max_line_bytes"):
            list(iter_source_lines(io.BytesIO(b"x"), max_line_bytes=0))


if __name__ == "__main__":
    unittest.main()
