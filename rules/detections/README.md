# Built-in detection rules

The initial M4 rule implementations are versioned in `engine/src/cloudlog_engine/detection/runner.py` and return the rule ID and version on every finding.

| Rule ID | Default threshold | Window | Severity |
|---|---:|---:|---|
| `auth.repeated_failures` | 5 failures | 300 seconds | High |
| `http.server_error_burst` | 10 HTTP 5xx responses | 60 seconds | Medium |
| `traffic.high_request_rate` | 120 HTTP requests per client IP | 60 seconds | Medium |
| `web.path-traversal` | 1 indicator | Per event | Medium |
| `web.environment-file-probe` | 1 indicator | Per event | Medium |
| `web.passwd-file-probe` | 1 indicator | Per event | Medium |
| `web.proc-environment-probe` | 1 indicator | Per event | Medium |
| `web.script-injection-probe` | 1 indicator | Per event | Medium |
| `web.sql-injection-probe` | 1 indicator | Per event | Medium |

Threshold windows are UTC tumbling windows, not sliding windows. These conservative pattern rules can produce false positives. Findings are investigative leads and must be validated with surrounding evidence; they are not proof of compromise and do not trigger automatic blocking. Group counts, evidence retained per finding, and total finding counts are bounded by `DetectionConfig`.
