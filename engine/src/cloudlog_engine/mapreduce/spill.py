"""Validated JSONL spill runs with per-job isolation and a hard byte budget."""
from __future__ import annotations
import json
import os
import tempfile
import uuid
from pathlib import Path
from typing import Any, Iterator
from .errors import CorruptSpillError, SpillBudgetExceededError, SpillError
from .partitioner import canonical_key_bytes

def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result

def _decode_key(value: Any) -> Any:
    if isinstance(value, dict) and set(value) == {"$tuple"}:
        return tuple(_decode_key(item) for item in value["$tuple"])
    if isinstance(value, list):
        return [_decode_key(item) for item in value]
    return value

class SpillManager:
    def __init__(self, max_bytes: int, directory: Path | None = None) -> None:
        self.max_bytes = max_bytes
        self.bytes_written = 0
        self.files_written = 0
        self._closed = False
        parent = str(directory) if directory is not None else None
        try:
            self.path = Path(tempfile.mkdtemp(prefix=f"cloudlog_mr_{uuid.uuid4().hex}_", dir=parent))
            try:
                os.chmod(self.path, 0o700)
            except OSError:
                pass
        except OSError as exc:
            raise SpillError("could not create isolated spill workspace") from exc

    @staticmethod
    def _encode(key: Any, value: Any, sequence: int) -> bytes:
        canonical_key_bytes(key)
        try:
            encoded_key = json.loads(canonical_key_bytes(key))
            payload = json.dumps(
                {"version": 1, "key": encoded_key, "value": value, "sequence": sequence},
                ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False,
            ).encode("utf-8") + b"\n"
        except (TypeError, ValueError) as exc:
            raise SpillError("intermediate values must be finite JSON-compatible data") from exc
        return payload

    def write_run(self, partition: int, records: list[tuple[bytes, int, Any, Any]]) -> Path:
        if self._closed:
            raise SpillError("spill workspace is closed")
        ordered = sorted(records, key=lambda item: (item[0], item[1]))
        path = self.path / f"p{partition}_{uuid.uuid4().hex}.jsonl"
        total = 0
        try:
            with path.open("xb") as stream:
                for _, sequence, key, value in ordered:
                    line = self._encode(key, value, sequence)
                    if self.bytes_written + total + len(line) > self.max_bytes:
                        raise SpillBudgetExceededError(
                            "configured spill byte budget would be exceeded"
                        )
                    stream.write(line)
                    total += len(line)
            self.bytes_written += total
            self.files_written += 1
            return path
        except SpillBudgetExceededError:
            path.unlink(missing_ok=True)
            raise
        except (OSError, SpillError) as exc:
            path.unlink(missing_ok=True)
            if isinstance(exc, SpillError):
                raise
            raise SpillError("could not write spill run") from exc

    def read_run(self, path: Path) -> Iterator[tuple[bytes, int, Any, Any]]:
        try:
            with path.open("rb") as stream:
                for line in stream:
                    try:
                        item = json.loads(
                            line,
                            parse_constant=lambda value: (_ for _ in ()).throw(
                                ValueError(f"invalid JSON constant: {value}")
                            ),
                            object_pairs_hook=_unique_object,
                        )
                        if (
                            not isinstance(item, dict)
                            or set(item) != {"version", "key", "value", "sequence"}
                            or item["version"] != 1
                            or not isinstance(item["sequence"], int)
                            or isinstance(item["sequence"], bool)
                            or item["sequence"] < 0
                        ):
                            raise ValueError
                        key = _decode_key(item["key"])
                        key_bytes = canonical_key_bytes(key)
                        yield key_bytes, item["sequence"], key, item["value"]
                    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError, KeyError) as exc:
                        raise CorruptSpillError("spill run contains an invalid record") from exc
        except OSError as exc:
            raise SpillError("could not read spill run") from exc

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            for child in self.path.iterdir():
                child.unlink()
            self.path.rmdir()
        except OSError as exc:
            raise SpillError("could not completely remove spill workspace") from exc

    def __enter__(self) -> "SpillManager":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        try:
            self.close()
        except SpillError:
            if exc is None:
                raise
