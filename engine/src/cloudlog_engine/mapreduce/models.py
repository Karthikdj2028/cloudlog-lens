"""Configuration, metrics, and result contracts for MapReduce jobs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TypeVar

from .errors import ConfigurationError

TOut = TypeVar("TOut")


class ExecutionMode(StrEnum):
    SEQUENTIAL = "sequential"
    MULTIPROCESSING = "multiprocessing"


@dataclass(frozen=True, slots=True)
class JobConfiguration:
    num_partitions: int = 8
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    num_workers: int = 2
    batch_size: int = 128
    max_in_memory_records_per_partition: int = 10_000
    max_in_memory_bytes_per_partition: int = 8 * 1024 * 1024
    max_spill_bytes: int = 1024 * 1024 * 1024
    max_output_records: int = 1_000_000
    spill_directory: Path | None = None

    def __post_init__(self) -> None:
        for name in (
            "num_partitions",
            "num_workers",
            "batch_size",
            "max_in_memory_records_per_partition",
            "max_in_memory_bytes_per_partition",
            "max_output_records",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ConfigurationError(f"{name} must be a positive integer")
        if (
            isinstance(self.max_spill_bytes, bool)
            or not isinstance(self.max_spill_bytes, int)
            or self.max_spill_bytes < 1
        ):
            raise ConfigurationError("max_spill_bytes must be a positive integer")
        try:
            object.__setattr__(self, "mode", ExecutionMode(self.mode))
        except (TypeError, ValueError) as exc:
            raise ConfigurationError("unsupported execution mode") from exc
        if self.spill_directory is not None:
            object.__setattr__(self, "spill_directory", Path(self.spill_directory))


@dataclass(frozen=True, slots=True)
class JobMetrics:
    input_records: int = 0
    mapped_records: int = 0
    reduced_records: int = 0
    partitions: int = 0
    spill_bytes: int = 0
    spill_files: int = 0
    worker_count: int = 1
    mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    stage_seconds: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True, slots=True)
class JobResult[TOut]:
    outputs: tuple[TOut, ...]
    metrics: JobMetrics
