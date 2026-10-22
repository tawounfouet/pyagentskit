# PyAgentsKit 0.1.0a1 — Phase 0 release notes

## Delivered scope

This pre-alpha archive completes **Phase 0 — Foundation, lots 00–01**.

### Lot 00 — Project foundation

- Python `src/` package layout;
- Apache-2.0 license and project governance;
- dependency policy;
- CI for lint, format, typing, tests and package build;
- nine accepted architecture decisions;
- version roadmap and explicit V1 non-goals;
- founding vision included and amended by normative ADRs.

### Lot 01 — Public contracts

- agent definition and model reference;
- multimodal messages;
- model request, response, stream and capability types;
- tool definition, calls, results and risk classification;
- run context, limits, status, result and usage;
- artifact references;
- versioned event envelope;
- model, tool, event, secret and sink protocols;
- normalized exception hierarchy.

## Verification evidence

| Check | Result |
|---|---|
| Ruff lint | Passed |
| Ruff format | Passed |
| mypy strict | Passed, 14 source files |
| Tests | 33 passed |
| Coverage | 93.16%, required minimum 90% |
| Wheel build | Passed |
| Source distribution build | Passed |
| Twine metadata check | Passed |
| Wheel ZIP integrity | Passed |
| Wheel import smoke test | Passed |
| Dependency consistency | Passed |

Validation was executed with Python 3.12.13. CI is configured for Python 3.11, 3.12 and 3.13.

## Distribution hashes

```text
7c64b5948b3c7a0e5fd4009821d9c642e1c77c21cb7c79fb096020f2dc4fefda  pyagentskit-0.1.0a1-py3-none-any.whl
6807b2f8138c3af034a3fc33c3cc629eda530c27e6d0188e8700528267b07dab  pyagentskit-0.1.0a1.tar.gz
```

## Explicit exclusions

This release does not yet contain a tool decorator/executor, agent loop, live provider, session
store, approvals, durable runtime or multi-agent orchestration.

## Next milestone

`0.1.0a2` — typed `@tool` decorator, schema generation, registry and governed executor.
