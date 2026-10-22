# OpenRouter RC1 qualification — PyAgentsKit 0.2.0rc1

Qualification date: 2026-09-05

| Qualification area | Status |
|---|---:|
| Routing and privacy policy fixtures | Pass |
| Primary + fallback capability preflight | Pass |
| Capability intersection | Pass |
| Non-streaming route trace | Pass |
| Streaming terminal route trace | Pass |
| Failure-event route trace | Pass |
| Typed errors including guardrail HTTP 403 | Pass |
| Catalog TTL/concurrency/invalidation | Pass |
| Snapshot v1 compatibility | Pass |
| Snapshot v2 integrity | Pass |
| Secret-free offline snapshot mode | Pass |
| Evaluation live profile | Not run — opt-in |
| Compliance/ZDR live profile | Not run — opt-in |
| Expected model fallback live path | Not run — opt-in |

## Live gates

All live gates may incur charges and require an already configured `OPENROUTER_API_KEY`.

Evaluation/catalog:

```bash
PYAGENTSKIT_OPENROUTER_LIVE=1 \
PYAGENTSKIT_OPENROUTER_MODEL=provider/model \
pytest -q tests/test_openrouter_live_qualification.py
```

Compliance/ZDR additionally requires:

```text
PYAGENTSKIT_OPENROUTER_COMPLIANCE_LIVE=1
PYAGENTSKIT_OPENROUTER_ALLOWED_PROVIDERS=provider-slug[,provider-slug]
```

Expected fallback additionally requires:

```text
PYAGENTSKIT_OPENROUTER_FALLBACK_LIVE=1
PYAGENTSKIT_OPENROUTER_PRIMARY_MODEL=provider/model
PYAGENTSKIT_OPENROUTER_FALLBACK_MODEL=provider/model
PYAGENTSKIT_OPENROUTER_EXPECTED_RESOLVED_MODEL=provider/model
```

The test request caps output at 16 tokens. This bounds completion size but is not a guaranteed
billing ceiling because routing, prompt tokens and provider accounting remain remote concerns.

## Privacy boundary

Per-request ZDR only filters inference endpoints. It does not govern third-party plugins or tools.
This adapter does not enable server-side plugins/tools. Deployment owners remain responsible for
account privacy settings, provider allowlists, logs and external tool policies.

## Official references

- [Router metadata](https://openrouter.ai/docs/guides/features/router-metadata)
- [Zero Data Retention](https://openrouter.ai/docs/guides/features/zdr)
- [Provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks)
- [Errors and debugging](https://openrouter.ai/docs/api_reference/errors-and-debugging)
