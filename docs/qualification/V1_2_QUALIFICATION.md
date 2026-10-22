# PyAgentsKit 1.2.0 qualification

The release is qualified locally and without network access. Live provider tests remain opt-in.

## Required evidence

| Area | Qualified behavior |
|---|---|
| Policy validation | finite bounds, unique categories and deterministic capped backoff |
| Default behavior | no automatic retry without an explicit enabled policy |
| Transient errors | rate limit, timeout and unavailability may retry |
| Permanent errors | authentication and response normalization never retry |
| Run limits | every attempt consumes `max_model_calls` |
| Stream safety | retry allowed before observable payload, refused after delta/tool/usage |
| Tool effects | an already executed write is not replayed when the next model call retries |
| Retry ownership | provider HTTP retries cannot stack with Runner retries |
| Router coordination | server fallback requires an explicit policy override |
| Telemetry privacy | event payloads expose counts and categories, not text or tool arguments |
| V1 compatibility | 155 root exports, 28 event types and frozen contracts remain intact |
| Packaging | reproducible wheel/sdist and installed-wheel examples pass |

## Provider boundary

All built-in adapters normalize transient failures into the existing model exception hierarchy.
The Runner uses exception types and the explicit `retryable` flag, never provider error messages.
Custom providers must disclose any internal retry behavior; automatic detection is guaranteed only
for the built-in transport contract.

OpenRouter can already perform upstream and model fallback. Runner retries are rejected when those
fallbacks are enabled unless the application deliberately sets `allow_provider_fallbacks=True`.
This override accepts the resulting multiplication of upstream attempts and possible charges.

