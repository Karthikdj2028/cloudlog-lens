# Security Policy

CloudLog Lens is currently at the architecture/scaffold stage and is not yet ready for production use.

## Reporting a vulnerability

Please do not publish exploit details or sensitive log samples in a public issue. Use GitHub's private vulnerability reporting feature for this repository if enabled. If private reporting is unavailable, contact the repository maintainer privately through a verified GitHub contact method.

Include the affected commit/version, impact, reproduction steps, and a minimal proof of concept. Remove secrets and personal data from reports.

## Scope and expectations

The project is designed to process untrusted infrastructure logs. Security issues involving arbitrary file access, unsafe parsing, code execution, workspace isolation, secret exposure, or denial of service are especially important.

Do not test against systems or data you do not own or have permission to assess.

## Current status

No production security guarantees are made at this stage. The security baseline and required pre-release regression tests are documented in [the security architecture](docs/security/README.md).
