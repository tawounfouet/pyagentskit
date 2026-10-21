# Audit - PyAgentsKit 1.2.0

Audit date: 2026-09-09

## Conclusion

The retry implementation stays inside the provider-call boundary and does not wrap the agent step
or tool executor. Consequently, a retry can repeat a model request but cannot repeat an already
executed business effect. Defaults remain identical to 1.1.0.

## Controls reviewed

- maximum eight configured attempts and deterministic bounded backoff;
- run deadline covers both provider attempts and backoff waits;
- `max_model_calls` checked before every attempt;
- cancellation propagates immediately and is never classified as retryable;
- permanent authentication and response-shape failures fail closed;
- stream retry stops after any observable text, tool fragment, completed tool call or usage event;
- stream callback failures are wrapped separately and never classified as provider failures;
- event failures expose exception class and allowlisted route data, never exception messages;
- stream telemetry contains only counts, booleans, attempt numbers and sanitized route metadata;
- built-in provider HTTP retry stacking is rejected;
- routed fallback stacking requires explicit consent;
- no change to tool execution, approval claiming or durable-effect reconciliation.

## Residual risks

- repeated model requests can be billed even when no response was delivered;
- custom adapters may conceal retries the Runner cannot introspect;
- deterministic backoff has no jitter and can synchronize many workers; deployments may stagger
  initial calls externally until a future explicit jitter policy exists;
- a stream `STARTED` event can appear more than once when the first attempt fails before payload;
- provider-reported usage for failed attempts may be unavailable;
- `allow_provider_fallbacks=True` deliberately permits multiplicative routing attempts.

These risks are explicit and do not justify an unsafe automatic default.
