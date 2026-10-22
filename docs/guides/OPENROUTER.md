# OpenRouter adapter — 0.2.0 stable

`OpenRouterModel` is an optional adapter, not the framework's multi-provider abstraction.
PyAgentsKit core continues to depend only on its own `Model` protocol.

## Installation

```bash
pip install "pyagentskit[openrouter]"
export OPENROUTER_API_KEY="..."
```

## Minimal usage

```python
from pyagentskit import AgentDefinition, ModelRef
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.runtime import Runner

agent = AgentDefinition(
    id="support",
    version="1.0.0",
    instructions="Answer precisely.",
    model=ModelRef(provider="openrouter", name="anthropic/YOUR_MODEL_ID"),
)

async with OpenRouterModel(
    model="anthropic/YOUR_MODEL_ID",
    app_url="https://example.org",
    app_title="My application",
) as model:
    result = await Runner(model).run(agent, "Hello")
```

`app_url` and `app_title` are optional attribution headers. The API key is never placed in the
request body, events, model metadata or serialized agent definition.

## Routing policies

Every request includes:

```json
{
  "provider": {
    "allow_fallbacks": false,
    "require_parameters": true
  }
}
```

`allow_fallbacks=false` prevents OpenRouter from switching between provider endpoints after a
failure. `require_parameters=true` restricts routing to endpoints supporting the parameters sent
by PyAgentsKit. Both flags can be changed explicitly at construction, but reproducible tests and
benchmarks should retain the defaults.

Advanced routing is explicit and serializable:

```python
from pyagentskit.providers.openrouter_routing import (
    OpenRouterDataPolicy,
    OpenRouterRoutingPolicy,
)

routing = OpenRouterRoutingPolicy(
    provider_order=("anthropic", "amazon-bedrock"),
    allow_fallbacks=True,
    model_fallbacks=("openai/YOUR_FALLBACK_MODEL",),
    require_parameters=True,
    data=OpenRouterDataPolicy(
        require_zdr=True,
        allow_training=False,
        allowed_providers=("anthropic", "amazon-bedrock"),
    ),
)
model = OpenRouterModel("anthropic/YOUR_MODEL_ID", routing=routing)
```

Model fallbacks are sent through the ordered `models` list. When any OpenRouter fallback is active,
local HTTP retries must remain zero so failure amplification stays bounded.

Named profiles are available through `OpenRouterRoutingPolicy.for_profile(...)`. Evaluation keeps
fallback disabled. Compliance requires an explicit provider allowlist and enforces ZDR plus denied
provider data collection.

An evaluation may pin one or more upstream providers through `allowed_providers`. Profiles do not
enable server-side plugins or tools.

## Catalog and capability preflight

```python
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.providers.openrouter_catalog import (
    ModelCapabilityRequirements,
    OpenRouterCatalog,
)

async with OpenRouterCatalog(api_key="...") as catalog:
    model = await OpenRouterModel.from_catalog(
        "anthropic/YOUR_MODEL_ID",
        catalog=catalog,
        requirements=ModelCapabilityRequirements(
            tool_calling=True,
            structured_output=True,
            min_context_tokens=100_000,
        ),
        api_key="...",
    )
```

The catalog caches `/models` for one hour by default and coalesces concurrent refreshes. Call
`invalidate()` or `list_models(force=True)` to refresh. After a successful fetch,
`save_snapshot(path)` creates an atomic JSON snapshot with a canonical SHA-256 integrity check.
For a network-free process, load it without credentials:

```python
catalog = OpenRouterCatalog.from_snapshot("openrouter-models.json")
models = await catalog.list_models()
```

Schema-v1 beta snapshots remain readable. The v2 checksum detects modification but does not prove
who produced the snapshot.

Catalog capabilities are conservative and include `catalog_reported=true` plus
`model_verified=false`. They are not a permanent guarantee of endpoint availability or account
policy.

When a routing policy contains explicit model fallbacks, `from_catalog(...)` validates every model
and exposes only their shared capabilities. A fallback can therefore never silently weaken a
preflight contract.

## Trace and usage metadata

Normalized responses retain:

```text
router
requested_model
resolved_model
upstream_provider
fallback_used
route_strategy
route_region
route_attempt
generation_id
usage_reported
is_byok
openrouter_cost
```

`Usage.estimated_cost_usd` receives the reported request cost when supplied. No local pricing table
is used. Router metadata is enabled with `X-OpenRouter-Metadata: enabled`; only stable scalar route
fields and the selected endpoint provider are retained. Summaries, attempt arrays, pipeline data
and arbitrary endpoint fields are discarded.

For SSE, the same safe route subset is attached to the terminal `completed` stream event. Cache
hits may omit OpenRouter's router metadata; missing values remain absent instead of being guessed.

## Errors

OpenRouter's `error.metadata.error_type` is mapped to normalized PyAgentsKit exceptions:

| OpenRouter error type | PyAgentsKit exception | Retryable |
|---|---|---:|
| `authentication` | `ModelAuthenticationError` | No |
| `rate_limit_exceeded` | `ModelRateLimitError` | Yes |
| `timeout` | `ModelTimeoutError` | Yes |
| `provider_overloaded` | `ModelUnavailableError` | Yes |
| `provider_unavailable` | `ModelUnavailableError` | Yes |
| `server` | `ModelUnavailableError` | Yes |
| Other validation/policy types | `ModelResponseError` | No |

An HTTP 403 carrying a typed guardrail or invalid-prompt error maps to `ModelResponseError`, not
authentication. A 401—or an untyped 403 at the authentication boundary—maps to
`ModelAuthenticationError`.

Exceptions retain only safe router metadata: `error_type`, numeric error/HTTP code and
`provider_code`. Provider messages, prompts and opaque metadata are not copied.

Errors embedded in HTTP 200 non-streaming bodies, choice objects or SSE events are handled as
failures. Streaming never retries after partial output.

## Live qualification

Live calls are disabled by default and may incur charges:

```bash
PYAGENTSKIT_OPENROUTER_LIVE=1 \
PYAGENTSKIT_OPENROUTER_MODEL=anthropic/YOUR_MODEL_ID \
pytest tests/test_openrouter_provider.py
```

Additional independently gated compliance and expected-fallback tests are documented in
`../qualification/OPENROUTER_RC1_QUALIFICATION.md`. They cap completion output at 16 tokens but can still incur
charges. The release contract tests use HTTPX mock transports and require no credentials.

## Stable API

The public imports, constructors, methods, serialized policy/descriptor fields and profile values
are frozen for the `0.2.x` line. See `../compatibility/OPENROUTER_API_STABILITY.md`. Dynamic model catalog entries,
provider availability, prices and additive response metadata remain upstream-controlled.

## Official references

- [API overview](https://openrouter.ai/docs/api_reference/overview)
- [Client tool calling](https://openrouter.ai/docs/guides/features/tool-calling)
- [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Streaming](https://openrouter.ai/docs/api_reference/streaming)
- [Errors and typed codes](https://openrouter.ai/docs/api_reference/errors-and-debugging)
- [Provider selection](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks)
- [Model catalog](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties)
- [Router metadata](https://openrouter.ai/docs/guides/features/router-metadata)
- [Zero Data Retention](https://openrouter.ai/docs/guides/features/zdr)
