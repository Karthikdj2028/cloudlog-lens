"""Public MapReduce job dispatcher."""
from __future__ import annotations
from collections.abc import Iterable
from typing import Any
from .models import ExecutionMode, JobConfiguration, JobResult
from .multiprocessing_runner import execute_multiprocessing
from .protocols import Mapper, Reducer
from .sequential import execute_sequential

def execute_job(
    records: Iterable[Any], mapper: Mapper[Any, Any, Any],
    reducer: Reducer[Any, Any, Any], config: JobConfiguration | None = None, *,
    cancel_check: Any = None,
) -> JobResult[Any]:
    config = config or JobConfiguration()
    if config.mode == ExecutionMode.MULTIPROCESSING:
        return execute_multiprocessing(
            records, mapper, reducer, config, cancel_check=cancel_check
        )
    return execute_sequential(records, mapper, reducer, config, cancel_check=cancel_check)
