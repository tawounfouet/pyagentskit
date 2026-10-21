# Retries and stream observability

Retries are disabled by default and apply only to model requests.

## Configure a policy

```python
from pyagentskit import Runner
from pyagentskit.retry import ModelRetryPolicy

policy = ModelRetryPolicy(
    max_attempts=3,
    initial_delay_seconds=0.25,
    backoff_multiplier=2,
    max_delay_seconds=2,
)

runner = Runner(model, tools=registry, retry_policy=policy)
result = await runner.run(agent, "Question")
```

`max_attempts` includes the first request. Delays before attempts 2 and 3 are 0.25 and 0.5 seconds.
The run timeout includes those waits, and each provider attempt consumes `max_model_calls`.

## Eligible failures

The default policy accepts normalized rate-limit, timeout and unavailable errors. Authentication,
invalid request and malformed response failures are not retried. To admit a custom adapter error,
the adapter must raise `ModelError(retryable=True)` and the policy must include
`ModelRetryReason.ADAPTER_RETRYABLE` explicitly.

## Stream rule

A stream may retry after transport failure only before text, tool or usage payload becomes
observable. A provider `STARTED` event alone does not block retry, so a handler may see more than
one `STARTED`. After a delta is shown, the run fails instead of duplicating partial output.

## Safe telemetry

The existing model events carry:

- one-based attempt number and whether it is a retry;
- retry category and deterministic delay;
- whether the call streamed;
- event, character and completed-tool counts;
- whether stream payload had already become observable;
- allowlisted provider route identifiers already supported by the framework.

Prompts, generated deltas, tool arguments, exception messages and terminal response documents are
never copied into these event payloads. `RuntimeMetrics` distinguishes completed model calls,
attempts, retries, stream completions, stream failures and total stream events.

## Retry ownership

Configure either provider HTTP retries or `ModelRetryPolicy`, never both. The Runner rejects this
combination for built-in adapters. OpenRouter fallback is a separate routing mechanism and must be
acknowledged with `allow_provider_fallbacks=True` before combining it with Runner retries.

Tools are outside the retry boundary. Use the existing durable-effect and reconciliation contracts
for uncertain writes; never treat model retry as a workflow recovery mechanism.

