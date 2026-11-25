"""Stable key encoding and partition assignment."""
from __future__ import annotations
import hashlib
import json
import math
from typing import Any
from .errors import ConfigurationError

def canonical_key_bytes(key: Any) -> bytes:
    """Encode supported JSON keys deterministically, preserving tuple identity."""
    def validate(value: Any, depth: int = 0) -> Any:
        if depth > 16:
            raise ConfigurationError("key nesting exceeds 16 levels")
        if value is None or isinstance(value, (str, bool, int)):
            return value
        if isinstance(value, float):
            if not math.isfinite(value):
                raise ConfigurationError("non-finite float keys are unsupported")
            return value
        if isinstance(value, tuple):
            return {"$tuple": [validate(item, depth + 1) for item in value]}
        if isinstance(value, list):
            return [validate(item, depth + 1) for item in value]
        raise ConfigurationError(f"unsupported key type: {type(value).__name__}")
    try:
        text = json.dumps(validate(key), ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError("key cannot be canonically encoded") from exc
    return text.encode("utf-8")

def partition_for(key: Any, num_partitions: int) -> int:
    if (isinstance(num_partitions, bool) or not isinstance(num_partitions, int)
            or num_partitions < 1):
        raise ConfigurationError("num_partitions must be a positive integer")
    digest = hashlib.sha256(canonical_key_bytes(key)).digest()
    return int.from_bytes(digest[:8], "big") % num_partitions
