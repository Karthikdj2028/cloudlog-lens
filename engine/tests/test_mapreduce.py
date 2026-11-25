from __future__ import annotations
from datetime import UTC, datetime
from pathlib import Path
import pytest
from cloudlog_engine.mapreduce import (
    CorruptSpillError, ExecutionMode, JobCancelledError, JobConfiguration,
    SpillBudgetExceededError, execute_job, partition_for,
)
from cloudlog_engine.mapreduce.spill import SpillManager
from cloudlog_engine.schema.events import CanonicalEvent, SourceInfo

def count_mapper(record):
    yield record["kind"], record["value"]

def sum_reducer(key, values):
    yield {"key": key, "total": sum(values)}

def event_mapper(event):
    yield event.event_type, 1

def event_reducer(key, values):
    yield {"event_type": key, "count": sum(values)}

def test_partition_is_stable_and_in_range():
    assert partition_for("client", 17) == partition_for("client", 17)
    assert 0 <= partition_for(("a", 2), 3) < 3

def test_sequential_groups_and_spills_and_cleans_up(tmp_path: Path):
    config = JobConfiguration(
        num_partitions=2, max_in_memory_records_per_partition=1,
        spill_directory=tmp_path,
    )
    result = execute_job(
        [{"kind": "a", "value": 1}, {"kind": "b", "value": 4},
         {"kind": "a", "value": 3}],
        count_mapper, sum_reducer, config,
    )
    assert {item["key"]: item["total"] for item in result.outputs} == {"a": 4, "b": 4}
    assert result.metrics.spill_files >= 1
    assert list(tmp_path.iterdir()) == []

def test_spill_budget_is_enforced(tmp_path: Path):
    with SpillManager(1024, tmp_path) as spill:
        records = [(b'"x"', i, "x", "v" * 2000) for i in range(2)]
        with pytest.raises(SpillBudgetExceededError):
            spill.write_run(0, records)

def test_rejects_non_json_values():
    with pytest.raises((TypeError, ValueError)):
        execute_job([1], lambda _: [("x", object())], sum_reducer)

def test_output_limit():
    config = JobConfiguration(max_output_records=1)
    with pytest.raises(ValueError, match="output record limit"):
        execute_job([1], lambda _: [("x", 1)], lambda key, values: iter([1, 2]), config)

def test_mapper_failure_cleans_spill_workspace(tmp_path: Path):
    def fail(_record):
        raise RuntimeError("expected failure")
    with pytest.raises(RuntimeError, match="expected failure"):
        execute_job([1], fail, sum_reducer, JobConfiguration(spill_directory=tmp_path))
    assert list(tmp_path.iterdir()) == []

def test_cancellation_cleans_spill_workspace(tmp_path: Path):
    with pytest.raises(JobCancelledError):
        execute_job(
            [1], lambda record: [("x", record)], sum_reducer,
            JobConfiguration(spill_directory=tmp_path), cancel_check=lambda: True,
        )
    assert list(tmp_path.iterdir()) == []

def test_corrupt_spill_is_rejected(tmp_path: Path):
    with SpillManager(4096, tmp_path) as spill:
        path = spill.path / "corrupt.jsonl"
        path.write_text(
            '{"version":1,"key":"x","key":"y","value":1,"sequence":0}\n',
            encoding="utf-8",
        )
        with pytest.raises(CorruptSpillError):
            list(spill.read_run(path))

def test_spawn_multiprocessing_matches_sequential():
    records = [
        {"kind": "a", "value": 1}, {"kind": "b", "value": 4},
        {"kind": "a", "value": 3},
    ]
    sequential = execute_job(records, count_mapper, sum_reducer)
    parallel = execute_job(
        records, count_mapper, sum_reducer,
        JobConfiguration(mode=ExecutionMode.MULTIPROCESSING, num_workers=2, batch_size=1),
    )
    assert parallel.outputs == sequential.outputs

def test_spawn_round_trips_canonical_event():
    event = CanonicalEvent(
        timestamp=datetime(2026, 11, 25, tzinfo=UTC),
        source=SourceInfo(name="test", format="test"),
        event_type="auth.failure",
    )
    result = execute_job(
        [event], event_mapper, event_reducer,
        JobConfiguration(mode=ExecutionMode.MULTIPROCESSING, num_workers=1, batch_size=1),
    )
    assert result.outputs == ({"event_type": "auth.failure", "count": 1},)
