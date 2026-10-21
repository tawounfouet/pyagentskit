# Observability

`RuntimeMetricsSink` consumes the existing safe `AgentEvent` stream and exposes counters for run,
model and tool outcomes plus the last cumulative token and cost totals. `snapshot()` returns an
immutable `RuntimeMetrics` value suitable for scraping or application logging.

Version 1.2 distinguishes successful model calls from actual attempts and retries. It also counts
stream events, completed streams and failed streams from additive fields on the existing V1 model
events. No new `EventType` value was introduced.

`model.request.started` is emitted once per actual attempt. A retry carries `is_retry=true`, the
typed retry category and the deterministic backoff already waited. `model.request.failed` records
whether another attempt will occur and whether stream payload was observed. A successful
`model.response.completed` contains event, character and tool-call counts. These payloads never
contain prompts, generated deltas, tool arguments or exception messages.

`OpenTelemetryEventSink` is optional. Install `pyagentskit[opentelemetry]` or inject a compatible
tracer. One span is opened per run, event names are copied as span events, and terminal run events
close the span. Only correlation identifiers and event types are exported by the bridge; event
payloads, prompts and tool arguments are excluded.

Applications remain responsible for configuring an OpenTelemetry SDK, sampler and exporter. A
sink should be attached to `EventBus`; it must not be allowed to turn telemetry failure into an
agent side effect. Provider routing metadata remains available in normalized model events.
