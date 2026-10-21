from __future__ import annotations

import json
import unittest
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

from pyagentskit import (
    AgentDefinition,
    ConfigurationError,
    EventType,
    FinishReason,
    ModelAuthenticationError,
    ModelCapabilities,
    ModelRateLimitError,
    ModelRef,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
    ModelUnavailableError,
    RunContext,
    RunLimits,
    Runner,
    RunStatus,
    TextContent,
    ToolCall,
    ToolRegistry,
    ToolRisk,
    tool,
)
from pyagentskit.observability import EventBus, MemoryEventSink
from pyagentskit.retry import ModelRetryPolicy, ModelRetryReason


def definition(*tools: str) -> AgentDefinition:
    return AgentDefinition(
        id="retry.agent",
        version="1.0.0",
        instructions="Use the scripted model.",
        model=ModelRef(provider="fake", name="retry-model"),
        tools=tools,
    )


def final(text: str = "done") -> ModelResponse:
    return ModelResponse(
        id="final",
        model="retry-model",
        content=(TextContent(text=text),),
        finish_reason=FinishReason.STOP,
    )


class GenerateScriptModel:
    capabilities = ModelCapabilities(tool_calling=True, streaming=True)

    def __init__(self, script: tuple[ModelResponse | Exception, ...]) -> None:
        self.script = script
        self.calls = 0

    async def generate(self, request: ModelRequest, *, context: RunContext[Any]) -> ModelResponse:
        item = self.script[self.calls]
        self.calls += 1
        if isinstance(item, Exception):
            raise item
        return item

    async def stream(
        self, request: ModelRequest, *, context: RunContext[Any]
    ) -> AsyncIterator[ModelStreamEvent]:
        raise AssertionError("generate path expected")
        yield  # pragma: no cover


def immediate_policy(max_attempts: int = 3) -> ModelRetryPolicy:
    return ModelRetryPolicy(
        max_attempts=max_attempts,
        initial_delay_seconds=0,
        max_delay_seconds=0,
    )


class RetryPolicyTests(unittest.TestCase):
    def test_exponential_backoff_is_bounded_and_deterministic(self) -> None:
        policy = ModelRetryPolicy(
            max_attempts=4,
            initial_delay_seconds=0.5,
            backoff_multiplier=3,
            max_delay_seconds=2,
        )
        self.assertEqual([policy.delay_after(i) for i in (1, 2, 3)], [0.5, 1.5, 2])
        self.assertTrue(policy.enabled)
        with self.assertRaises(ValueError):
            policy.delay_after(0)
        with self.assertRaises(ValueError):
            ModelRetryPolicy(initial_delay_seconds=2, max_delay_seconds=1)
        with self.assertRaises(ValueError):
            ModelRetryPolicy(retry_on=(ModelRetryReason.TIMEOUT, ModelRetryReason.TIMEOUT))

    def test_nested_provider_retries_and_unapproved_fallbacks_are_rejected(self) -> None:
        model = GenerateScriptModel((final(),))
        model._http = SimpleNamespace(retries=1)  # type: ignore[attr-defined]
        with self.assertRaises(ConfigurationError):
            Runner(model, retry_policy=immediate_policy())

        model._http.retries = 0  # type: ignore[attr-defined]
        model.routing = SimpleNamespace(  # type: ignore[attr-defined]
            allow_fallbacks=True, model_fallbacks=()
        )
        with self.assertRaises(ConfigurationError):
            Runner(model, retry_policy=immediate_policy())
        allowed = immediate_policy().model_copy(update={"allow_provider_fallbacks": True})
        Runner(model, retry_policy=allowed)


class ModelRetryRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_retryable_generate_failure_recovers_with_auditable_attempts(self) -> None:
        model = GenerateScriptModel(
            (ModelRateLimitError("private provider text", retryable=True), final())
        )
        sink = MemoryEventSink()
        result = await Runner(
            model,
            events=EventBus((sink,)),
            retry_policy=immediate_policy(),
        ).run(definition(), "hello")
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(result.usage.model_calls, 2)
        self.assertEqual(model.calls, 2)
        attempts = [
            event for event in sink.events if event.event_type is EventType.MODEL_REQUEST_STARTED
        ]
        failures = [
            event for event in sink.events if event.event_type is EventType.MODEL_REQUEST_FAILED
        ]
        self.assertEqual([event.payload["attempt"] for event in attempts], [1, 2])
        self.assertFalse(attempts[0].payload["is_retry"])
        self.assertTrue(attempts[1].payload["is_retry"])
        self.assertEqual(attempts[1].payload["retry_reason"], "rate_limit")
        self.assertTrue(failures[0].payload["will_retry"])
        self.assertNotIn("private provider text", json.dumps(failures[0].payload))

    async def test_authentication_failure_is_never_retried(self) -> None:
        model = GenerateScriptModel((ModelAuthenticationError("secret"), final()))
        result = await Runner(model, retry_policy=immediate_policy()).run(definition(), "hello")
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(result.usage.model_calls, 1)
        self.assertEqual(model.calls, 1)

    async def test_model_call_budget_prevents_retry(self) -> None:
        model = GenerateScriptModel((ModelUnavailableError("temporary"), final()))
        sink = MemoryEventSink()
        result = await Runner(
            model,
            events=EventBus((sink,)),
            retry_policy=immediate_policy(),
        ).run(definition(), "hello", limits=RunLimits(max_model_calls=1))
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(result.usage.model_calls, 1)
        failure = next(
            event for event in sink.events if event.event_type is EventType.MODEL_REQUEST_FAILED
        )
        self.assertFalse(failure.payload["will_retry"])

    async def test_retry_after_tool_result_never_replays_tool_effect(self) -> None:
        effects: list[int] = []

        @tool(risk=ToolRisk.LOCAL_WRITE, idempotent=False)
        async def record(value: int) -> int:
            """Record one local effect."""
            effects.append(value)
            return value

        tool_response = ModelResponse(
            id="tool",
            model="retry-model",
            tool_calls=(ToolCall(id="call-1", name="record", arguments={"value": 7}),),
            finish_reason=FinishReason.TOOL_CALLS,
        )
        model = GenerateScriptModel((tool_response, ModelUnavailableError("temporary"), final()))
        result = await Runner(
            model,
            tools=ToolRegistry((record,)),
            retry_policy=immediate_policy(),
        ).run(definition("record"), "hello")
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(result.usage.model_calls, 3)
        self.assertEqual(result.usage.tool_calls, 1)
        self.assertEqual(effects, [7])


class StreamRetryRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_can_retry_before_observable_payload(self) -> None:
        class StreamModel:
            capabilities = ModelCapabilities(streaming=True)

            def __init__(self) -> None:
                self.calls = 0

            async def generate(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> ModelResponse:
                raise AssertionError("stream path expected")

            async def stream(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> AsyncIterator[ModelStreamEvent]:
                self.calls += 1
                yield ModelStreamEvent(type=ModelStreamEventType.STARTED)
                if self.calls == 1:
                    raise ModelUnavailableError("private interruption")
                yield ModelStreamEvent(type=ModelStreamEventType.TEXT_DELTA, delta="done")
                yield ModelStreamEvent(type=ModelStreamEventType.COMPLETED)

        model = StreamModel()
        received: list[ModelStreamEventType] = []

        async def handle(event: ModelStreamEvent) -> None:
            received.append(event.type)

        sink = MemoryEventSink()
        result = await Runner(
            model,
            events=EventBus((sink,)),
            retry_policy=immediate_policy(),
        ).run(definition(), "hello", stream_handler=handle)
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(result.output, "done")
        self.assertEqual(result.usage.model_calls, 2)
        self.assertEqual(received.count(ModelStreamEventType.STARTED), 2)
        completed = next(
            event for event in sink.events if event.event_type is EventType.MODEL_RESPONSE_COMPLETED
        )
        self.assertTrue(completed.payload["streaming"])
        self.assertEqual(completed.payload["stream_event_count"], 3)
        self.assertEqual(completed.payload["stream_text_chars"], 4)

    async def test_stream_is_not_retried_after_a_delta(self) -> None:
        class InterruptedModel:
            capabilities = ModelCapabilities(streaming=True)

            def __init__(self) -> None:
                self.calls = 0

            async def generate(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> ModelResponse:
                raise AssertionError("stream path expected")

            async def stream(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> AsyncIterator[ModelStreamEvent]:
                self.calls += 1
                yield ModelStreamEvent(
                    type=ModelStreamEventType.TEXT_DELTA, delta="private partial text"
                )
                raise ModelUnavailableError("private interruption")

        model = InterruptedModel()
        sink = MemoryEventSink()

        async def handle(event: ModelStreamEvent) -> None:
            return None

        result = await Runner(
            model,
            events=EventBus((sink,)),
            retry_policy=immediate_policy(),
        ).run(definition(), "hello", stream_handler=handle)
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(model.calls, 1)
        stream_failures = [
            event.payload
            for event in sink.events
            if event.event_type is EventType.MODEL_REQUEST_FAILED
        ]
        self.assertEqual(len(stream_failures), 1)
        self.assertFalse(stream_failures[0]["will_retry"])
        serialized = json.dumps(stream_failures)
        self.assertNotIn("private partial text", serialized)
        self.assertNotIn("private interruption", serialized)
        self.assertEqual(stream_failures[0]["stream_event_count"], 1)
        self.assertTrue(stream_failures[0]["stream_observed"])

    async def test_stream_handler_failure_is_not_misclassified_as_provider_failure(self) -> None:
        class StreamModel:
            capabilities = ModelCapabilities(streaming=True)

            def __init__(self) -> None:
                self.calls = 0

            async def generate(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> ModelResponse:
                raise AssertionError("stream path expected")

            async def stream(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> AsyncIterator[ModelStreamEvent]:
                self.calls += 1
                yield ModelStreamEvent(type=ModelStreamEventType.STARTED)
                yield ModelStreamEvent(type=ModelStreamEventType.TEXT_DELTA, delta="unused")
                yield ModelStreamEvent(type=ModelStreamEventType.COMPLETED)

        model = StreamModel()

        async def failing_handler(event: ModelStreamEvent) -> None:
            raise ModelUnavailableError("downstream observer unavailable")

        result = await Runner(model, retry_policy=immediate_policy()).run(
            definition(), "hello", stream_handler=failing_handler
        )
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(model.calls, 1)


if __name__ == "__main__":
    unittest.main()
