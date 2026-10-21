# Contributing to PyAgentsKit

PyAgentsKit has reached its first stable pre-1.0 release. Contributions should preserve the
documented mono-agent scope and provider-neutral architecture.

## Development workflow

1. Create a focused branch from the current main branch.
2. Add or update tests with every behavioral change.
3. Run the complete local quality suite.
4. Document public API changes and architectural decisions.
5. Submit a small, reviewable pull request.

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy src
pytest
python scripts/release_check.py
```

## Architectural requirements

- Core contracts must not import provider SDKs.
- New provider-specific behavior belongs in an adapter.
- New tool capabilities must declare their security impact.
- Public types require documentation and tests.
- New dependencies require a written justification.
- Multi-agent orchestration is outside the V1 scope.

## Commit guidance

Use concise, imperative commit messages. Conventional Commit prefixes are recommended:
`feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci` and `chore`.

## Reporting security issues

Do not open a public issue for a vulnerability. Follow [SECURITY.md](SECURITY.md).
