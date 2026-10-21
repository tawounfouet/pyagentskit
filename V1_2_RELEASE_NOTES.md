# PyAgentsKit 1.2.0 - explicit model retries and stream observability

Release date: 2026-09-09

PyAgentsKit 1.2.0 is a backward-compatible post-V1 feature release. It adds a disabled-by-default,
Runner-owned retry policy for transient model failures and enriches the existing model events with
attempt and stream summaries that never contain generated text or tool arguments.

## Added

- `pyagentskit.retry.ModelRetryPolicy`, a strict serializable configuration;
- deterministic exponential backoff with a bounded number of attempts;
- explicit retry categories for rate limits, timeouts, unavailability and adapter-declared errors;
- attempt, retry, backoff and stream-summary fields on the existing model event vocabulary;
- runtime metrics for attempts, retries, stream events, stream completions and stream failures;
- an offline retry example and a deterministic retry overhead benchmark.

## Safety rules

- retries are disabled unless `max_attempts > 1` is explicitly configured;
- every attempt consumes `RunLimits.max_model_calls`, including failed attempts;
- authentication and malformed-response errors are never retried;
- streamed calls may retry only before a text/tool/usage event becomes observable;
- provider HTTP retries and Runner retries cannot be enabled together;
- routed fallbacks require `allow_provider_fallbacks=True` on the retry policy;
- only model requests retry: tool execution and durable effects are never wrapped or replayed.

## Compatibility

- the root package still exports exactly the 155 names frozen in V1;
- `EventType` retains its exact 28-value V1 vocabulary;
- frozen serialized field orders and all provider constructors remain unchanged;
- `Runner.retry_policy` is keyword-only and defaults to `None`;
- applications upgrading from 1.1.0 require no migration.

## Explicit exclusions

- no retry of tools, guardrails, approvals, stores or workflow effects;
- no random jitter or hidden retry defaults;
- no transaction claim across repeated provider requests;
- no guarantee that a failed provider attempt incurred no cost;
- no multi-agent or workflow-engine behavior.

