# OpenRouter API stability contract — PyAgentsKit 0.2.x

Effective version: `0.2.0`. Scope: the optional OpenRouter adapter only.

## Frozen public import paths

The following paths are public for the complete `0.2.x` line:

```python
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.providers.openrouter_catalog import (
    ModelCapabilityRequirements,
    OpenRouterCatalog,
    OpenRouterModelDescriptor,
    common_capabilities,
    require_capabilities,
)
from pyagentskit.providers.openrouter_routing import (
    OpenRouterDataPolicy,
    OpenRouterProfile,
    OpenRouterRoutingPolicy,
)
```

Each module declares an explicit `__all__`. Names beginning with `_`, transport internals and raw
mapping helpers are private.

## Compatibility promise

For `0.2.x` patch releases, PyAgentsKit will not:

- remove or rename a frozen public symbol;
- remove a constructor or method parameter;
- change an existing parameter from optional to required;
- change a documented default in a behaviorally incompatible way;
- remove or rename a serialized Pydantic field;
- change an existing `OpenRouterProfile` value;
- stop reading schema-v1 or schema-v2 catalog snapshots.

Patch releases may add optional parameters, fields, metadata keys or enum values when old callers
continue to work. Security fixes may reject inputs that were previously accepted when accepting
them would violate the documented safety boundary.

## Frozen behavior

- Default endpoint fallback is disabled and parameter support is required.
- Explicit model fallbacks are serialized as an ordered `models` list.
- Local HTTP retries cannot be combined with OpenRouter fallbacks.
- `from_catalog(...)` owns capability resolution and rejects a manual capability override.
- A fallback chain exposes only capabilities common to every routed model.
- Router metadata is opt-in at the wire level and reduced to a safe normalized subset.
- Streaming route metadata is emitted on the terminal completed event when supplied upstream.
- Cache-hit metadata may be absent and is never invented.
- Snapshot v2 checks integrity; it does not authenticate provenance.
- Offline catalogs never create a client or refresh implicitly.

## Dynamic boundaries excluded from the freeze

OpenRouter's model catalog, endpoint availability, prices, provider names, model capabilities,
account policy and upstream latency are external dynamic data. A model listed today is not a
permanent framework guarantee. Applications must pin explicit model IDs and provider policies when
reproducibility matters.

The `metadata` mappings on responses and capabilities are additive. Consumers must ignore unknown
keys. Arbitrary upstream router payloads are intentionally not part of the public contract.

## Deprecation policy

A future replacement API must be introduced additively and documented before a frozen `0.2.x`
symbol can be removed. Removal or incompatible serialization changes require at least a minor
version boundary. The test suite `tests/test_openrouter_stable_api.py` is the executable contract.
