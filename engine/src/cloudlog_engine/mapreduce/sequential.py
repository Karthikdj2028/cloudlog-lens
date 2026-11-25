"""Reference single-process MapReduce execution."""

from __future__ import annotations

import time
from collections.abc import Iterable
from typing import Any

from .errors import JobCancelledError
from .models import JobConfiguration, JobMetrics, JobResult
from .protocols import Mapper, Reducer
from .shuffle import Shuffle
from .spill import SpillManager


def execute_sequential(
    records: Iterable[Any],
    mapper: Mapper[Any, Any, Any],
    reducer: Reducer[Any, Any, Any],
    config: JobConfiguration,
    *,
    cancel_check: Any = None,
) -> JobResult[Any]:
    started = time.perf_counter()
    input_count = mapped_count = sequence = 0
    outputs: list[Any] = []
    with SpillManager(config.max_spill_bytes, config.spill_directory) as spill:
        shuffle = Shuffle(
            config.num_partitions,
            config.max_in_memory_records_per_partition,
            config.max_in_memory_bytes_per_partition,
            spill,
        )
        for record in records:
            if cancel_check is not None and cancel_check():
                raise JobCancelledError("job cancelled")
            input_count += 1
            for key, value in mapper(record):
                if cancel_check is not None and cancel_check():
                    raise JobCancelledError("job cancelled")
                shuffle.add(key, value, sequence)
                sequence += 1
                mapped_count += 1
        for key, values in shuffle.groups():
            if cancel_check is not None and cancel_check():
                raise JobCancelledError("job cancelled")
            for output in reducer(key, values):
                if len(outputs) >= config.max_output_records:
                    raise ValueError("job output record limit exceeded")
                outputs.append(output)
        metrics = JobMetrics(
            input_records=input_count,
            mapped_records=mapped_count,
            reduced_records=len(outputs),
            partitions=config.num_partitions,
            spill_bytes=spill.bytes_written,
            spill_files=spill.files_written,
            worker_count=1,
            mode=config.mode,
            stage_seconds=(("total", time.perf_counter() - started),),
        )
    return JobResult(tuple(outputs), metrics)
