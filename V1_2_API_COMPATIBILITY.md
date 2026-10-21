# PyAgentsKit 1.2.0 API compatibility

## V1 freeze retained

| Contract | Stable requirement | 1.2.0 result |
|---|---|---|
| Root exports | 155 names and frozen SHA-256 | Unchanged |
| `EventType` | 28 exact values | Unchanged |
| Central Pydantic layouts | Frozen field order | Unchanged |
| `RunContext` | Frozen dataclass fields | Unchanged |
| Provider constructors | Frozen parameters | Unchanged |
| OpenRouter public surface | Frozen routing/provider signatures | Unchanged |

The new policy is intentionally imported from `pyagentskit.retry`, avoiding a root namespace
change. `Runner.__init__` adds only the keyword-only `retry_policy=None` parameter.

## Event compatibility

No event type was added. Existing events gain additive payload keys:

| Event | Additive safe fields |
|---|---|
| `model.request.started` | `attempt`, `is_retry`, retry category, backoff, streaming flag |
| `model.request.failed` | `will_retry`, delay, category, attempt and stream counters |
| `model.response.completed` | attempts and stream event/text/tool counts |

With retries disabled, one `model.request.started` event is emitted for each logical model call,
as before. With retries enabled, it is emitted for every actual provider attempt. Consumers must
continue treating event payloads as forward-compatible dictionaries.

## Usage compatibility

`Usage.model_calls` now explicitly counts actual Runner-level model attempts. This equals the old
successful-call count when retries are disabled. Failed provider attempts may lack token or cost
data; the runtime never fabricates those values.

