"""Spawn-based bounded parallel mapper with parent-owned shuffle and reduce."""
from __future__ import annotations
import concurrent.futures
import json
import multiprocessing
import time
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from cloudlog_engine.schema.events import (
    AuthenticationInfo, CanonicalEvent, EventSeverity, HTTPInfo, SourceInfo,
)
from .errors import JobCancelledError, WorkerExecutionError
from .models import ExecutionMode, JobConfiguration, JobMetrics, JobResult
from .partitioner import canonical_key_bytes
from .protocols import Mapper, Reducer
from .shuffle import Shuffle
from .spill import SpillManager

def _encode_input(record: Any) -> tuple[str, Any]:
    if isinstance(record, CanonicalEvent):
        return ("canonical_event_v1", record.to_dict())
    try:
        json.dumps(record, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"multiprocessing input type {type(record).__name__} is not supported"
        ) from exc
    return ("json", record)

def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))

def _decode_input(encoded: tuple[str, Any]) -> Any:
    kind, payload = encoded
    if kind == "json":
        return payload
    if kind != "canonical_event_v1":
        raise ValueError("unsupported multiprocessing input envelope")
    source = SourceInfo(**payload["source"])
    http = HTTPInfo(**payload["http"]) if payload["http"] is not None else None
    auth_data = payload["auth"]
    auth = AuthenticationInfo(**auth_data) if auth_data is not None else None
    return CanonicalEvent(
        timestamp=_parse_datetime(payload["timestamp"]),
        observed_at=_parse_datetime(payload["observed_at"]),
        event_type=payload["event_type"], event_id=payload["event_id"],
        schema_version=payload["schema_version"], severity=EventSeverity(payload["severity"]),
        source=source, host=payload["host"], client_ip=payload["client_ip"],
        user=payload["user"], http=http, auth=auth, message=payload["message"],
        attributes=payload["attributes"],
    )

def _map_batch(mapper: Any, batch: list[tuple[str, Any]]) -> list[tuple[Any, Any]]:
    mapped: list[tuple[Any, Any]] = []
    for encoded in batch:
        record = _decode_input(encoded)
        for key, value in mapper(record):
            canonical_key_bytes(key)
            try:
                json.dumps(value, ensure_ascii=False, allow_nan=False)
            except (TypeError, ValueError) as exc:
                raise TypeError(
                    "multiprocessing mapper values must be JSON-compatible"
                ) from exc
            mapped.append((key, value))
    return mapped

def _batches(records: Iterable[Any], size: int):
    batch: list[Any] = []
    for record in records:
        batch.append(record)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch

def execute_multiprocessing(
    records: Iterable[Any], mapper: Mapper[Any, Any, Any],
    reducer: Reducer[Any, Any, Any], config: JobConfiguration, *,
    cancel_check: Any = None,
) -> JobResult[Any]:
    """Map bounded batches in spawned workers; shuffle/reduce in the parent.

    Mappers must be trusted, module-level pickleable callables. Inputs and
    intermediate key/value records use a versioned JSON wire representation;
    canonical events use their public schema representation. Spill files never
    use pickle. Reducers run in the parent process.
    """
    started = time.perf_counter()
    input_count = mapped_count = sequence = 0
    outputs: list[Any] = []
    context = multiprocessing.get_context("spawn")
    with SpillManager(config.max_spill_bytes, config.spill_directory) as spill:
        shuffle = Shuffle(
            config.num_partitions, config.max_in_memory_records_per_partition,
            config.max_in_memory_bytes_per_partition, spill,
        )
        iterator = iter(_batches(records, config.batch_size))
        try:
            with concurrent.futures.ProcessPoolExecutor(
                max_workers=config.num_workers, mp_context=context
            ) as pool:
                pending: dict[
                    concurrent.futures.Future[list[tuple[Any, Any]]], int
                ] = {}
                ready: dict[int, list[tuple[Any, Any]]] = {}
                next_batch = next_to_apply = 0
                exhausted = False
                while pending or ready or not exhausted:
                    if cancel_check is not None and cancel_check():
                        raise JobCancelledError("job cancelled")
                    while not exhausted and len(pending) < config.num_workers * 2:
                        try:
                            batch = next(iterator)
                        except StopIteration:
                            exhausted = True
                            break
                        input_count += len(batch)
                        encoded_batch = [_encode_input(record) for record in batch]
                        pending[pool.submit(_map_batch, mapper, encoded_batch)] = next_batch
                        next_batch += 1
                    if pending:
                        done, _ = concurrent.futures.wait(
                            tuple(pending),
                            return_when=concurrent.futures.FIRST_COMPLETED,
                        )
                        for future in done:
                            batch_index = pending.pop(future)
                            try:
                                ready[batch_index] = future.result()
                            except Exception as exc:
                                raise WorkerExecutionError("mapper worker failed") from exc
                    while next_to_apply in ready:
                        for key, value in ready.pop(next_to_apply):
                            shuffle.add(key, value, sequence)
                            sequence += 1
                            mapped_count += 1
                        next_to_apply += 1
                for key, values in shuffle.groups():
                    if cancel_check is not None and cancel_check():
                        raise JobCancelledError("job cancelled")
                    for output in reducer(key, values):
                        if len(outputs) >= config.max_output_records:
                            raise ValueError("job output record limit exceeded")
                        outputs.append(output)
        except (JobCancelledError, WorkerExecutionError):
            raise
        except Exception as exc:
            if isinstance(exc, (ValueError, TypeError)):
                raise
            raise WorkerExecutionError("multiprocessing execution failed") from exc
        metrics = JobMetrics(
            input_records=input_count, mapped_records=mapped_count,
            reduced_records=len(outputs), partitions=config.num_partitions,
            spill_bytes=spill.bytes_written, spill_files=spill.files_written,
            worker_count=config.num_workers, mode=ExecutionMode.MULTIPROCESSING,
            stage_seconds=(("total", time.perf_counter() - started),),
        )
    return JobResult(tuple(outputs), metrics)
