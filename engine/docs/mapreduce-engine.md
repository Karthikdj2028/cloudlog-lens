# MapReduce Engine (M3)

## Scope and execution model

The engine is a framework-independent Python package. `execute_job` accepts an iterable, a mapper that yields `(key, value)` pairs, a reducer that consumes a key and an iterator of values, and an optional `JobConfiguration`. Sequential mode is the reference execution path. Multiprocessing mode uses Python's `spawn` context to map bounded batches in worker processes; shuffle and reduction remain in the parent process so workers never own persistence resources.

Mapper and reducer callables should be deterministic. Multiprocessing mappers must be trusted, module-level, pickleable callables. Inputs and mapped key/value pairs use a JSON-compatible wire representation for process transport; canonical events are reconstructed from their schema representation. Spill files never use pickle.

## Determinism

Keys are encoded as canonical UTF-8 JSON and assigned with SHA-256, never Python's randomized `hash()`. Supported keys are `None`, booleans, integers, finite floats, strings, and nested lists/tuples. Tuple keys retain tuple identity in the spill envelope. Each mapped pair receives a sequence number; spill runs are sorted by canonical key bytes and sequence, and the merge preserves this order within each key. Cross-mode output ordering is deterministic when mapper behavior and source iteration order are deterministic.

## Memory and disk limits

Each partition buffer is flushed when either its record-count or estimated serialized-payload threshold is reached. The byte threshold measures canonical key/value payload plus fixed per-record allowance; it is not a hard process-RSS limit and does not account for all Python allocator/object overhead. Multiprocessing bounds submitted batches to twice the worker count. Each worker currently returns a complete mapped batch, so an individual batch's intermediate expansion is bounded by the mapper's output for that batch, not by a separate output-byte limit.

Spill files are versioned JSON Lines with strict JSON encoding and are bounded by `max_spill_bytes`, including newline framing. The current result API collects at most `max_output_records` outputs in memory. Spill workspaces are unique per job and are created with owner-only permissions where supported. Cleanup runs on normal exit and exceptions. Spill records are validated when read. A failed cleanup is raised if there is no earlier exception; an existing job exception remains primary.

## Cancellation and failures

Pass a zero-argument `cancel_check` callback to `execute_job`; it is polled between records, batches, and reduce groups. A cancellation raises `JobCancelledError`. Worker failures are wrapped as `WorkerExecutionError` with the original exception chained. The process executor context shuts down workers on exit.

## Example

```python
def mapper(event):
    yield event["event_type"], 1

def reducer(key, values):
    yield {"event_type": key, "count": sum(values)}

result = execute_job(events, mapper, reducer, JobConfiguration(num_partitions=4))
```

No database, FastAPI, SQLAlchemy, Tauri, network service, or telemetry dependency is introduced.
