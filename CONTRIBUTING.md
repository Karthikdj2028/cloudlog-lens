# Contributing

Thanks for your interest in CloudLog Lens. The project is currently at the architecture/scaffold stage.

## Before contributing

1. Read the [system architecture](docs/architecture/README.md) and [repository structure](docs/architecture/repository-structure.md).
2. Check the roadmap and open issues to avoid duplicate work.
3. For cross-cutting changes, propose an architecture decision record before implementation.
4. Keep pull requests focused on one milestone or behavior.

## Engineering expectations

- Preserve dependency direction: the engine must remain independent of FastAPI, SQLAlchemy, and UI code.
- Add tests for behavior and security boundaries.
- Use synthetic or properly licensed fixtures only.
- Do not add telemetry, external log uploads, or third-party processing without an explicit product decision.
- Avoid adding infrastructure or dependencies without a clear need.
- Document commands that were actually run and their results.

## Pull request checklist

- [ ] Scope and motivation are clear.
- [ ] Relevant tests are added or updated.
- [ ] Format/lint/type checks pass, or failures are explained.
- [ ] Security and privacy implications are considered.
- [ ] Documentation and roadmap are updated where needed.
- [ ] No secrets, private logs, databases, or generated artifacts are included.

## License

The repository license is to be selected before the first distributable release. Contributions will be governed by the published license once added.
