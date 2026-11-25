"""Typed failures raised by the MapReduce engine."""


class MapReduceError(Exception):
    """Base class for MapReduce failures."""


class ConfigurationError(MapReduceError, ValueError):
    """Invalid job configuration or unsupported data."""


class SpillError(MapReduceError):
    """A spill run could not be safely written or read."""


class SpillBudgetExceededError(SpillError):
    """The configured on-disk intermediate-data budget was exceeded."""


class CorruptSpillError(SpillError):
    """A spill record failed validation."""


class JobCancelledError(MapReduceError):
    """The caller cancelled a running job."""


class WorkerExecutionError(MapReduceError):
    """A multiprocessing worker failed."""
