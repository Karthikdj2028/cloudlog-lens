# Canonical Event Schema v1.0

This document describes the first shared event contract. The Python implementation is in `engine/src/cloudlog_engine/schema/`.

## Design constraints

- Events are immutable value objects.
- Event timestamps must include a timezone and are normalized to UTC.
- Source identity is a logical label; absolute local paths are not part of the event contract.
- Raw source lines are deliberately excluded from the canonical event.
- Client network identity may be represented as a host IP or a masked CIDR network.
- Extension attributes are JSON-compatible, bounded, and recursively immutable.
- Sensitive attribute names are redacted recursively before durable storage.
- Client IP masking is configurable; when enabled, default networks are IPv4 /24 and IPv6 /48.

## Fields

| Field | Type | Required | Notes |
|---|---|---:|---|
| `schema_version` | string | yes | Currently `1.0` |
| `event_id` | UUID string | yes | Generated if omitted |
| `timestamp` | timezone-aware datetime | yes | Normalized to UTC |
| `observed_at` | timezone-aware datetime | yes | Defaults to current UTC time |
| `event_type` | string | yes | Examples: `http.request`, `auth.failure` |
| `severity` | enum | yes | unknown, debug, info, warning, error, critical |
| `source` | SourceInfo | yes | Logical name, format, parser version |
| `host` | string | no | Source host label |
| `client_ip` | IP or CIDR | no | Validated IPv4/IPv6 or masked network |
| `user` | string | no | Normalized account/user label |
| `http` | HTTPInfo | no | Method, target, protocol, status, bytes, duration |
| `auth` | AuthenticationInfo | no | Outcome, action, account |
| `message` | string | no | Bounded event message |
| `attributes` | JSON object | no | Max 128 top-level keys, depth 8, bounded arrays/strings |

## Privacy boundary

Parser adapters should create canonical events, then apply configured redaction before an event is written to a database, index, queue, or durable intermediate file. Use `prepare_event_for_persistence(event, policy)` at persistence boundaries as a second explicit safeguard. The current engine schema does not itself write data to disk.

## Compatibility

Changes to field meaning or serialization require a schema version decision and regression tests. Additive optional fields may remain within the same major schema version only when they do not change existing field semantics.
