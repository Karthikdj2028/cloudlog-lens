"""Bounded partition buffers, sorted spill runs, and streaming key groups."""
from __future__ import annotations
import heapq
import itertools
import json
from collections.abc import Iterator
from typing import Any
from .partitioner import canonical_key_bytes, partition_for
from .spill import SpillManager

class Shuffle:
    def __init__(self, partitions: int, max_records: int, max_bytes: int,
                 spill: SpillManager) -> None:
        self.partitions = partitions
        self.max_records = max_records
        self.max_bytes = max_bytes
        self.spill = spill
        self.buffers: list[list[tuple[bytes, int, Any, Any]]] = [
            [] for _ in range(partitions)
        ]
        self.buffer_bytes = [0] * partitions
        self.runs: list[list[object]] = [[] for _ in range(partitions)]

    def add(self, key: Any, value: Any, sequence: int) -> None:
        key_bytes = canonical_key_bytes(key)
        partition = partition_for(key, self.partitions)
        value_bytes = len(json.dumps(
            value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode("utf-8"))
        size = len(key_bytes) + value_bytes + 24
        self.buffers[partition].append((key_bytes, sequence, key, value))
        self.buffer_bytes[partition] += size
        if (len(self.buffers[partition]) >= self.max_records
                or self.buffer_bytes[partition] >= self.max_bytes):
            self._flush(partition)

    def _flush(self, partition: int) -> None:
        if not self.buffers[partition]:
            return
        path = self.spill.write_run(partition, self.buffers[partition])
        self.runs[partition].append(path)
        self.buffers[partition] = []
        self.buffer_bytes[partition] = 0

    def groups(self) -> Iterator[tuple[Any, Iterator[Any]]]:
        for partition in range(self.partitions):
            sources = [self.spill.read_run(path) for path in self.runs[partition]]
            if self.buffers[partition]:
                sources.append(iter(sorted(
                    self.buffers[partition], key=lambda item: (item[0], item[1])
                )))
            merged = heapq.merge(*sources, key=lambda item: (item[0], item[1]))
            for _, group in itertools.groupby(merged, key=lambda item: item[0]):
                first = next(group)
                values = itertools.chain((first[3],), (record[3] for record in group))
                yield first[2], values
