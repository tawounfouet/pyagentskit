# PyAgentsKit 0.1.0b1 — Offline mono-agent runtime

Date: 2026-09-05. Baseline: 0.1.0a2. Lots 03–04, first beta delivery.

## Delivered

- `runtime.Runner`: async loop plus safe synchronous facade using existing AgentDefinition.
- Explicit tool allowlist, unique call IDs, strict output validation using `output_type`.
- Finite steps, model/tool calls, deadline and reported token/cost budgets.
- Ordered multi-tool turns (sequential execution); optional sanitized tool-error recovery.
- Terminal RunResult for success, failure and limits; task cancellation propagates normally.
- `testing.FakeModel`: scripted responses/errors, request capture, deterministic stream events.
- `observability.EventBus`: ordered sync/async consumers, explicit fail-fast/best-effort modes.
- Memory, JSON Lines and console sinks, application-supplied secret redaction.
- Fixed preservation of typed nested Pydantic tool arguments from alpha2.

## Usage

```bash
python -m pip install -e '.[dev]'
python examples/offline_agent.py
ruff check src tests examples
ruff format --check src tests examples
mypy src
pytest
python -m build
python -m twine check dist/*
```

Import Runner from `pyagentskit.runtime`, FakeModel from `pyagentskit.testing`, and sinks
from `pyagentskit.observability`. Use `Runner.run(agent, input, output_type=MyPydanticModel)`
for structured JSON validation. Existing AgentDefinition remains the configuration object.

## Beta boundaries and known limitations

- No live provider yet; OpenAI remains the next planned lot.
- No sessions, durable checkpoints, approval workflow or arbitrary-code sandbox.
- Approval-required tools are rejected by Runner, not automatically approved.
- Tools execute sequentially; max_parallel_tools is therefore respected but not saturated.
- Runner consumes complete responses; FakeModel exposes streaming separately for adapter tests.
- Budgets use reported usage after each response; they cannot guarantee a hard billing ceiling.
  Unknown costs cannot be checked. Providers must add request-level output constraints later.
- Model selection is injected, not automatically resolved from ModelRef.
- Assistant tool calls are retained in message metadata under `tool_calls`; future adapters
  must translate this field. No SDK-specific objects cross the boundary.
- JSON Schema alone is not locally validated: supply output_type or receive CapabilityError.
- Refusals produce FAILED with sanitized error, not a dedicated refusal status in this beta.
- Synchronous tool threads cannot be forcibly stopped; external clients need native timeouts.
- Event sinks own their streams, retention and access controls. Do not register an executor sink
  and Runner sink to the same destination if duplicate lifecycle events are undesirable.
- EventBus redacts supplied secret values, not arbitrary unknown sensitive information.
- RunContext supplies IDs; Runner accepts a clock for deterministic event-envelope tests.
- Runtime returns collected artifact references; artifact stores remain lot 08.

## Local verification results

73 tests passed; total branch-aware coverage 94.97%. Ruff and strict Mypy pass.
The full offline example completes two model calls and one tool call.

The tests run offline on Python 3.12 in this delivery environment. Other supported Python
versions require the CI matrix; no claim of local multi-version testing is made.
