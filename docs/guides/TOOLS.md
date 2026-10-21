# Tool system guide

PyAgentsKit tools are explicit capabilities. A model may request a call, but validation,
policy and execution remain owned by the application runtime.

## Declare a function tool

```python
from pyagentskit import RunContext, tool


@tool(
    name="customer.get",
    risk="read",
    idempotent=True,
    tags=("customer", "read"),
)
async def get_customer(
    customer_id: str,
    context: RunContext[dict[str, str]],
) -> dict[str, str]:
    """Retrieve one customer without modifying it."""
    tenant = context.deps["tenant"]
    return {"id": customer_id, "tenant": tenant}
```

The decorator derives a strict JSON input schema from the callable signature. It also derives an
output schema when a return annotation exists. A description is mandatory and may come from the
docstring or the `description` option.

`RunContext` is injected by the executor and omitted from the schema shown to the model. It is the
correct channel for database clients, service ports, tenant information and other non-prompt
dependencies.

## Supported signatures

- standard named and keyword-only parameters;
- Pydantic-compatible annotations, including models, enums, literals, unions and collections;
- optional defaults;
- synchronous and asynchronous callables;
- zero or one exact `RunContext` parameter.

The following are rejected during declaration:

- untyped parameters;
- positional-only parameters;
- `*args` and `**kwargs`;
- unresolved annotations;
- absent description;
- governance metadata that violates `ToolDefinition` invariants.

Input validation is strict. For example, the string `"2"` is not silently converted to the
integer `2`.

## Register and execute

```python
from pyagentskit import RunContext, ToolRegistry

registry = ToolRegistry([get_customer])
context = RunContext(agent_id="support", deps={"tenant": "demo"})

result = await registry.execute(
    "customer.get",
    {"customer_id": "cus-42"},
    context=context,
    call_id="call-001",
)
```

Names are unique. Registering a duplicate raises `ToolAlreadyRegisteredError`; replacement must be
explicit with `register(tool, replace=True)`. `names()` and `definitions()` use deterministic
lexical order.

## Execution boundary

`ToolExecutor` applies these stages:

1. verify that the selected tool matches the requested name;
2. run every `before_execute` policy;
3. validate arguments;
4. inject `RunContext`;
5. acquire the tool concurrency slot;
6. run with a finite timeout;
7. validate and normalize the result;
8. run every `after_execute` policy;
9. emit correlated structured events.

Synchronous functions run through a worker thread so they do not block the event loop. Cancelling
their awaiter cannot forcibly terminate Python code already running in that thread; applications
must design blocking operations with their own cancellation or timeout controls.

## Errors

| Exception | Meaning |
|---|---|
| `ToolNotFoundError` | Requested name is absent from the registry |
| `ToolAlreadyRegisteredError` | Duplicate registration without explicit replacement |
| `ToolValidationError` | Arguments or returned value violate the type-derived schema |
| `ToolPermissionError` | A policy denied the call or failed closed |
| `ToolTimeoutError` | The configured execution timeout elapsed |
| `ToolExecutionError` | Tool code or post-execution policy failed |

Internal exception text is retained through Python exception chaining for local diagnosis but is
not copied into the normalized public message.

## Policies and approvals

Policies implement `ToolExecutionPolicy` with asynchronous `before_execute` and `after_execute`
methods. A policy can reject a call by raising `ToolPermissionError` or return a transformed
`ToolResult` after execution.

Lot 02 provides interception points only. Persistent human approval, suspension and safe resumption
belong to lot 09. A `requires_approval=True` definition is governance metadata and must be enforced
by a policy in applications that execute such tools before lot 09.

## Events

When sinks are configured, the executor emits:

- `tool.call.started`;
- `tool.call.completed`;
- `tool.call.failed` for timeout, cancellation or execution failure.

Events include the full run and trace identifiers, tool name, call identifier, status and duration.
Arguments and raw exception messages are intentionally excluded.

## Security recommendations

- Treat all model-provided arguments as untrusted.
- Use the narrowest `ToolRisk` matching the real effect.
- Mark idempotence only when repeating the same call is safe.
- Require approval for destructive and code-execution definitions.
- Keep credentials inside `RunContext` dependencies or a `SecretProvider`.
- Never place secrets in definitions, metadata, arguments intended for logging or display text.
- Set realistic timeouts and concurrency limits around external systems.
