"""CloudLog Lens standalone log processing engine.

The package intentionally has no dependency on web frameworks, persistence
libraries, desktop runtimes, or frontend code.
"""

from cloudlog_engine.schema import (
    AuthOutcome, AuthenticationInfo, CanonicalEvent, EventSeverity, HTTPInfo,
    RedactionPolicy, SourceInfo, apply_redaction, prepare_event_for_persistence,
)

__all__ = [
    "AuthOutcome", "AuthenticationInfo", "CanonicalEvent", "EventSeverity",
    "HTTPInfo", "RedactionPolicy", "SourceInfo", "apply_redaction",
    "prepare_event_for_persistence",
]
