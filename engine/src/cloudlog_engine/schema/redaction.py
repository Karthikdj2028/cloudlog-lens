"""Privacy transformations to apply before an event crosses a persistence boundary."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, replace
from typing import Any, Mapping

from cloudlog_engine.schema.events import CanonicalEvent

DEFAULT_SENSITIVE_FIELDS = frozenset({
    "authorization", "cookie", "set-cookie", "password", "passwd", "token",
    "access_token", "refresh_token", "api_key", "secret", "session_id",
})


@dataclass(frozen=True, slots=True)
class RedactionPolicy:
    """Controls recursive field redaction and optional client-network masking."""

    sensitive_fields: frozenset[str] = DEFAULT_SENSITIVE_FIELDS
    replacement: str = "[REDACTED]"
    mask_client_ips: bool = False
    ipv4_prefix: int = 24
    ipv6_prefix: int = 48

    def __post_init__(self) -> None:
        if not isinstance(self.replacement, str) or not self.replacement:
            raise ValueError("replacement must be a non-empty string")
        if not 0 <= self.ipv4_prefix <= 32:
            raise ValueError("ipv4_prefix must be between 0 and 32")
        if not 0 <= self.ipv6_prefix <= 128:
            raise ValueError("ipv6_prefix must be between 0 and 128")
        normalized = frozenset(_normalize_key(name) for name in self.sensitive_fields)
        if any(not name for name in normalized):
            raise ValueError("sensitive field names must be non-empty")
        object.__setattr__(self, "sensitive_fields", normalized)


def apply_redaction(
    event: CanonicalEvent,
    policy: RedactionPolicy | None = None,
) -> CanonicalEvent:
    """Return a redacted copy; never mutate the original event.

    Invoke during normalization, before writing to a database, index, queue,
    or durable intermediate file.
    """
    if not isinstance(event, CanonicalEvent):
        raise TypeError("event must be a CanonicalEvent instance")
    policy = policy or RedactionPolicy()
    attributes = _redact_value(event.attributes, policy)
    client_ip = event.client_ip
    if policy.mask_client_ips and client_ip is not None:
        existing = ipaddress.ip_network(client_ip, strict=False) if "/" in client_ip else None
        address = existing.network_address if existing else ipaddress.ip_address(client_ip)
        requested = policy.ipv4_prefix if address.version == 4 else policy.ipv6_prefix
        prefix = max(existing.prefixlen, requested) if existing else requested
        client_ip = str(ipaddress.ip_network(f"{address}/{prefix}", strict=False))
    return replace(event, client_ip=client_ip, attributes=attributes)


def prepare_event_for_persistence(
    event: CanonicalEvent,
    policy: RedactionPolicy | None = None,
) -> CanonicalEvent:
    """Named persistence-boundary helper; persistence adapters must call this first."""
    return apply_redaction(event, policy)


def _redact_value(value: Any, policy: RedactionPolicy, key: str | None = None) -> Any:
    if key is not None and _normalize_key(key) in policy.sensitive_fields:
        return policy.replacement
    if isinstance(value, Mapping):
        return {str(child_key): _redact_value(child, policy, str(child_key)) for child_key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_redact_value(child, policy) for child in value]
    return value


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.casefold())
