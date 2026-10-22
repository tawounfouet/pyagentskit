# PyAgentsKit 0.1.0a2 — Lot 02: Typed tool system

**Release date:** 2026-09-04  
**Baseline:** `0.1.0a1`  
**Milestone:** Lot 02 complete

## Outcome

This release turns the Phase 0 tool contracts into a provider-neutral execution subsystem. Python
functions can now be declared as governed tools, exposed through strict schemas, registered and
executed without a model, agent loop or network connection.

## Delivered

- typed `@tool` decorator;
- strict Pydantic input and output validation;
- automatic JSON Schema generation;
- hidden `RunContext` injection;
- synchronous execution outside the event-loop thread;
- native asynchronous execution;
- deterministic `ToolRegistry`;
- explicit duplicate replacement semantics;
- finite timeouts and cancellation propagation;
- per-tool concurrency limits;
- normalized validation, permission, timeout and execution errors;
- before/after policy hooks;
- structured tool lifecycle events;
- offline example and complete tool guide.

## Architectural boundaries preserved

- no model-provider dependency;
- no agent loop;
- no workflow engine;
- no arbitrary code execution tool;
- no implicit human-approval implementation;
- no SDK-specific type in the public API.

## Security behavior

- model arguments are validated before user code runs;
- unknown fields and coercion are rejected;
- destructive and code-execution definitions still require approval metadata;
- raw arguments and internal exception messages are not emitted in tool lifecycle events;
- policy errors fail closed as `ToolPermissionError`;
- every execution uses a finite positive timeout.

## Known limitation

Python cannot forcibly stop a synchronous callable already running in a worker thread. A timeout
cancels the awaiter and returns control, but blocking libraries must also receive their own native
timeouts. This behavior is documented and tested at the asynchronous boundary.

## Verification target

The release is accepted only when all of the following pass:

```bash
ruff check .
ruff format --check .
mypy src
pytest
python -m build
python -m twine check dist/*
```

The wheel must additionally install in a clean environment, import without optional dependencies
and execute `examples/typed_tools.py` successfully.

## Next milestone

`0.1.0b1` combines:

- Lot 03 — mono-agent runtime;
- Lot 04 — events, deterministic `FakeModel` and offline runtime test harness.
