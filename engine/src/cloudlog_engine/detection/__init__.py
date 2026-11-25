"""Framework-independent explainable detection contracts and built-in rules."""

from .models import (
    DetectionConfig,
    DetectionEvidence,
    Finding,
    FindingSeverity,
)
from .runner import run_detections

__all__ = [
    "DetectionConfig",
    "DetectionEvidence",
    "Finding",
    "FindingSeverity",
    "run_detections",
]
