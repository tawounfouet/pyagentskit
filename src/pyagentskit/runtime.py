"""Bounded provider-neutral mono-agent execution."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from pydantic import TypeAdapter

from .agents import AgentDefinition
from .approvals import ApprovalRequest, ApprovalStatus, ApprovalStore
from .artifact_store import ArtifactRetentionPolicy, ArtifactStore
from .context import (
    ContextBudget,
    ContextPolicy,
    ContextSelection,
    ContextSource,
    FullContextPolicy,
)
from .events import AgentEvent, EventType
from .exceptions import (
    ApprovalError,
    CapabilityError,
    ConfigurationError,
    ContextBudgetError,
    GuardrailError,
    ModelError,
    ModelResponseError,
    PyAgentsKitError,
    RunLimitExceededError,
    SessionError,
    ToolError,
)
from .guardrails import GuardrailAction, GuardrailPipeline, GuardrailStage
from .messages import Message, MessageRole, TextContent
from .models import (
    FinishReason,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
)
from .observability import EventBus
from .ports import Model
from .privacy import DataClassification, DataPolicy
from .retry import ModelRetryPolicy
from .runs import RunContext, RunError, RunLimits, RunResult, RunStatus, utc_now
from .sessions import SessionStore
from .tools import ToolRegistry, ToolResult, ToolResultStatus, ToolRisk
from .usage import Usage


class Runner:
    """Per-call state isolation. Cancellation propagates as CancelledError.

    Model instances must themselves support concurrent calls when shared.
    Explicit output types provide local structured validation; no provider SDK required.
    """

    def __init__(
        self,
        model: Model,
        *,
        tools: ToolRegistry | None = None,
        events: EventBus | None = None,
        clock: Callable[[], datetime] = utc_now,
        session_store: SessionStore | None = None,
        context_policy: ContextPolicy | None = None,
        artifact_store: ArtifactStore | None = None,
        artifact_policy: ArtifactRetentionPolicy | None = None,
        context_sources: tuple[ContextSource, ...] = (),
        guardrails: GuardrailPipeline | None = None,
        data_policy: DataPolicy | None = None,
        approval_store: ApprovalStore | None = None,
        approval_ttl_seconds: float | None = 3600,
        parallel_tool_calls: bool = False,
        retry_policy: ModelRetryPolicy | None = None,
    ) -> None:
        self.model = model
        self.tools = tools if tools is not None else ToolRegistry()
        self.events = events or EventBus()
        self.clock = clock
        self.session_store = session_store
        self.context_policy = context_policy or FullContextPolicy()
        self.artifact_store = artifact_store
        self.artifact_policy = artifact_policy or ArtifactRetentionPolicy()
        self.context_sources = context_sources
        self.guardrails = guardrails or GuardrailPipeline()
        self.data_policy = data_policy
        self.approval_store = approval_store
        self.approval_ttl_seconds = approval_ttl_seconds
        self.parallel_tool_calls = parallel_tool_calls
        self.retry_policy = retry_policy
        if retry_policy is not None and retry_policy.enabled:
            transport = getattr(model, "_http", None)
            if getattr(transport, "retries", 0):
                raise ConfigurationError(
                    "Runner retries cannot be combined with provider HTTP retries"
                )
            routing = getattr(model, "routing", None)
            routed_fallbacks = bool(
                getattr(routing, "allow_fallbacks", False)
                or getattr(routing, "model_fallbacks", ())
            )
            if routed_fallbacks and not retry_policy.allow_provider_fallbacks:
                raise ConfigurationError(
                    "Runner retries require allow_provider_fallbacks=True when routing fallbacks "
                    "are enabled"
                )

    def run_sync(self, agent: AgentDefinition, input: str, **kwargs: Any) -> RunResult[Any]:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.run(agent, input, **kwargs))
        raise RuntimeError("Use await Runner.run() inside an active event loop")

    async def resume_approval(
        self,
        agent: AgentDefinition,
        approval_id: str,
        *,
        context: RunContext[Any] | None = None,
        limits: RunLimits | None = None,
        output_type: Any = None,
        recover_tool_errors: bool = False,
        context_budget: ContextBudget | None = None,
    ) -> RunResult[Any]:
        """Resume one approved or rejected tool call from durable session state."""

        if self.approval_store is None or self.session_store is None:
            raise ApprovalError("Approval resume requires approval_store and session_store")
        tenant_id = None if context is None else context.metadata.get("tenant_id")
        if tenant_id is not None and not isinstance(tenant_id, str):
            raise ValueError("RunContext metadata tenant_id must be a string")
        approval = await self.approval_store.get(approval_id, tenant_id=tenant_id)
        if approval.agent_id != agent.id:
            raise ApprovalError("Approval agent does not match agent definition")
        if approval.status not in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
        }:
            raise ApprovalError("Approval is not ready to resume")
        resumed_context = RunContext(
            agent_id=agent.id,
            deps=None if context is None else context.deps,
            run_id=approval.run_id,
            trace_id=approval.trace_id,
            session_id=approval.session_id,
            started_at=approval.requested_at,
            metadata={} if context is None else context.metadata,
        )
        return await self.run(
            agent,
            "approval-resume",
            context=resumed_context,
            limits=limits,
            output_type=output_type,
            recover_tool_errors=recover_tool_errors,
            context_budget=context_budget,
            _resume_approval=approval,
        )

    async def run(
        self,
        agent: AgentDefinition,
        input: str,
        *,
        context: RunContext[Any] | None = None,
        limits: RunLimits | None = None,
        output_type: Any = None,
        recover_tool_errors: bool = False,
        context_budget: ContextBudget | None = None,
        stream_handler: Callable[[ModelStreamEvent], Awaitable[None]] | None = None,
        _resume_approval: ApprovalRequest | None = None,
        _resume_session: bool = False,
    ) -> RunResult[Any]:
        ctx = context or RunContext(agent_id=agent.id, deps=None)
        if ctx.agent_id != agent.id:
            raise ValueError("Context agent_id does not match agent definition")
        configured_provider = getattr(self.model, "provider", None)
        configured_model = getattr(self.model, "model", None)
        if configured_provider is not None and configured_provider != agent.model.provider:
            raise CapabilityError("Agent provider does not match the configured model adapter")
        if configured_model is not None and configured_model != agent.model.name:
            raise CapabilityError("Agent model does not match the configured model adapter")
        bound = limits or agent.limits
        adapter: TypeAdapter[Any] | None = TypeAdapter(output_type) if output_type else None
        schema = adapter.json_schema() if adapter else agent.output_schema
        if schema is not None and adapter is None:
            raise CapabilityError("Supply output_type for local structured output validation")
        if agent.tools and not self.model.capabilities.tool_calling:
            raise CapabilityError("Model does not support tools")
        if schema and not self.model.capabilities.structured_output:
            raise CapabilityError("Model does not support structured output")
        if stream_handler is not None and not self.model.capabilities.streaming:
            raise CapabilityError("Model does not support streaming")
        definitions = tuple(self.tools.get(name).definition for name in agent.tools)
        system_message = Message.from_text(MessageRole.SYSTEM, agent.instructions)
        user_message = (
            None
            if _resume_approval is not None or _resume_session
            else Message.from_text(MessageRole.USER, input)
        )
        messages = [system_message, *(() if user_message is None else (user_message,))]
        started = self.clock()
        usage = Usage()
        artifacts: list[Any] = []
        output: Any = None
        error: RunError | None = None
        status = RunStatus.RUNNING
        used_ids: set[str] = set()
        tenant_id_raw = ctx.metadata.get("tenant_id")
        if tenant_id_raw is not None and not isinstance(tenant_id_raw, str):
            raise ValueError("RunContext metadata tenant_id must be a string")
        tenant_id = tenant_id_raw
        classification_raw = ctx.metadata.get("data_classification", DataClassification.INTERNAL)
        try:
            classification = (
                classification_raw
                if isinstance(classification_raw, DataClassification)
                else DataClassification[classification_raw.upper()]
                if isinstance(classification_raw, str)
                else DataClassification(classification_raw)
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid RunContext data_classification") from exc
        last_selection: ContextSelection | None = None
        guardrail_audit: list[dict[str, Any]] = []
        approval_id: str | None = None
        guardrail_retries = 0

        async def emit(kind: EventType, **payload: Any) -> None:
            event_step = payload.pop("step", None)
            await self.events.emit(
                AgentEvent(
                    event_type=kind,
                    occurred_at=self.clock(),
                    run_id=ctx.run_id,
                    trace_id=ctx.trace_id,
                    agent_id=agent.id,
                    session_id=ctx.session_id,
                    step=event_step,
                    payload=payload,
                )
            )

        async def govern(value: Any, stage: GuardrailStage) -> tuple[Any, GuardrailAction]:
            transformed, decisions = await self.guardrails.evaluate(value, stage=stage, context=ctx)
            action = GuardrailAction.ALLOW
            for decision in decisions:
                action = decision.action
                safe = {
                    "stage": stage.value,
                    "action": decision.action.value,
                    "policy_id": decision.policy_id,
                    "metadata": decision.metadata,
                }
                guardrail_audit.append(safe)
                await emit(EventType.GUARDRAIL_EVALUATED, **safe)
                if decision.action in {GuardrailAction.REJECT, GuardrailAction.ABORT}:
                    await emit(EventType.GUARDRAIL_REJECTED, **safe)
                    raise GuardrailError(f"Guardrail {decision.action.value} at {stage.value}")
                if decision.action is not GuardrailAction.TRANSFORM:
                    action = decision.action
            return transformed, action

        def check_usage() -> None:
            for limit, value in (
                (bound.max_input_tokens, usage.input_tokens),
                (bound.max_output_tokens, usage.output_tokens),
                (bound.max_total_tokens, usage.total_tokens),
                (bound.max_cost_usd, usage.estimated_cost_usd),
            ):
                if limit is not None and value is not None and value > limit:
                    raise RunLimitExceededError("Reported usage budget exceeded")

        def safe_failure_metadata(error: BaseException) -> dict[str, Any]:
            original = getattr(error, "metadata", {})
            original = original if isinstance(original, dict) else {}
            return {
                ("provider_error_type" if key == "error_type" else key): value
                for key, value in original.items()
                if key
                in {
                    "http_status",
                    "error_type",
                    "provider_code",
                    "route_strategy",
                    "route_region",
                    "route_attempt",
                    "fallback_used",
                    "upstream_provider",
                }
                and (value is None or isinstance(value, str | bool | int | float))
            }

        async def generate_response(
            request: ModelRequest, step: int
        ) -> tuple[ModelResponse, int, dict[str, int | bool]]:
            nonlocal usage
            policy = self.retry_policy or ModelRetryPolicy()
            retry_reason: str | None = None
            retry_delay = 0.0
            for attempt in range(1, policy.max_attempts + 1):
                if usage.model_calls >= bound.max_model_calls:
                    raise RunLimitExceededError("Model call limit reached during retry")
                usage = usage + Usage(model_calls=1)
                await emit(
                    EventType.MODEL_REQUEST_STARTED,
                    step=step,
                    attempt=attempt,
                    streaming=stream_handler is not None,
                    is_retry=attempt > 1,
                    retry_reason=retry_reason,
                    backoff_seconds=retry_delay,
                    requested_provider=agent.model.provider,
                    requested_model=agent.model.name,
                )
                stream_observed = False
                stream_event_count = 0
                text_parts: list[str] = []
                streamed_calls: list[Any] = []
                try:
                    if stream_handler is None:
                        response = await self.model.generate(request, context=ctx)
                    else:
                        streamed_usage = Usage()
                        metadata: dict[str, Any] = {}
                        completed = False
                        async for stream_event in self.model.stream(request, context=ctx):
                            stream_event_count += 1
                            if stream_event.type in {
                                ModelStreamEventType.TEXT_DELTA,
                                ModelStreamEventType.TOOL_CALL_DELTA,
                                ModelStreamEventType.TOOL_CALL_COMPLETED,
                                ModelStreamEventType.USAGE,
                            }:
                                stream_observed = True
                            try:
                                await stream_handler(stream_event.model_copy(deep=True))
                            except asyncio.CancelledError:
                                raise
                            except Exception:
                                raise PyAgentsKitError("Stream handler failed") from None
                            if stream_event.type is ModelStreamEventType.TEXT_DELTA:
                                if stream_event.delta is None:
                                    raise ModelResponseError("Text stream event requires a delta")
                                text_parts.append(stream_event.delta)
                            elif stream_event.type is ModelStreamEventType.TOOL_CALL_COMPLETED:
                                if stream_event.tool_call is None:
                                    raise ModelResponseError(
                                        "Tool stream event requires a completed call"
                                    )
                                streamed_calls.append(stream_event.tool_call)
                            elif stream_event.type is ModelStreamEventType.USAGE:
                                if stream_event.usage is not None:
                                    streamed_usage = stream_event.usage
                            elif stream_event.type is ModelStreamEventType.ERROR:
                                raise ModelResponseError("Model stream reported an error")
                            elif stream_event.type is ModelStreamEventType.COMPLETED:
                                if completed:
                                    raise ModelResponseError(
                                        "Model stream completed more than once"
                                    )
                                completed = True
                                metadata.update(stream_event.metadata)
                        if not completed:
                            raise ModelResponseError("Model stream ended without completion")
                        native_response = metadata.pop("response", None)
                        if isinstance(native_response, dict):
                            response = ModelResponse.model_validate(native_response)
                        else:
                            resolved_model = metadata.get("resolved_model", agent.model.name)
                            response_id = metadata.get(
                                "generation_id", f"stream-{ctx.run_id}-{step}"
                            )
                            response = ModelResponse(
                                id=str(response_id),
                                model=str(resolved_model),
                                content=(
                                    (TextContent(text="".join(text_parts)),) if text_parts else ()
                                ),
                                tool_calls=tuple(streamed_calls),
                                finish_reason=(
                                    FinishReason.TOOL_CALLS if streamed_calls else FinishReason.STOP
                                ),
                                usage=streamed_usage,
                                metadata={
                                    "provider": agent.model.provider,
                                    "requested_model": agent.model.name,
                                    "resolved_model": str(resolved_model),
                                    **metadata,
                                },
                            )
                    return (
                        response,
                        attempt,
                        {
                            "streaming": stream_handler is not None,
                            "stream_event_count": stream_event_count,
                            "stream_text_chars": sum(len(part) for part in text_parts),
                            "stream_tool_call_count": len(streamed_calls),
                        },
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    reason = policy.reason_for(exc)
                    retryable = (
                        reason is not None
                        and not stream_observed
                        and attempt < policy.max_attempts
                        and usage.model_calls < bound.max_model_calls
                    )
                    delay = policy.delay_after(attempt) if retryable else 0.0
                    await emit(
                        EventType.MODEL_REQUEST_FAILED,
                        step=step,
                        attempt=attempt,
                        error_type=type(exc).__name__,
                        will_retry=retryable,
                        retry_delay_seconds=delay,
                        retry_reason=reason.value if reason is not None else None,
                        streaming=stream_handler is not None,
                        stream_event_count=stream_event_count,
                        stream_observed=stream_observed,
                        requested_provider=agent.model.provider,
                        requested_model=agent.model.name,
                        **safe_failure_metadata(exc),
                    )
                    if not retryable or reason is None:
                        raise
                    await asyncio.sleep(delay)
                    retry_reason = reason.value
                    retry_delay = delay
            raise ModelError("Model retry attempts exhausted")  # pragma: no cover

        async def persist(batch: tuple[Message, ...], *, phase: str, step: int) -> None:
            if self.session_store is None or ctx.session_id is None:
                return
            await self.session_store.append(
                ctx.session_id,
                batch,
                turn_id=str(ctx.run_id),
                tenant_id=tenant_id,
                run_id=ctx.run_id,
                idempotency_key=f"{ctx.run_id}:{step}:{phase}",
            )
            await emit(EventType.SESSION_UPDATED, phase=phase, message_count=len(batch))

        await emit(EventType.RUN_STARTED)
        try:
            async with asyncio.timeout(bound.timeout_seconds):
                if user_message is not None:
                    governed_input, input_action = await govern(input, GuardrailStage.INPUT)
                    if input_action in {
                        GuardrailAction.REQUIRE_APPROVAL,
                        GuardrailAction.RETRY_WITH_FEEDBACK,
                    }:
                        raise GuardrailError("Input guardrail returned an unsupported action")
                    if not isinstance(governed_input, str) or not governed_input.strip():
                        raise GuardrailError("Input guardrail must produce non-empty text")
                    input = governed_input
                    user_message = Message.from_text(MessageRole.USER, input)
                    messages = [system_message, user_message]
                if self.session_store is not None and ctx.session_id is not None:
                    session = await self.session_store.get(ctx.session_id, tenant_id=tenant_id)
                    if session.agent_id != agent.id:
                        raise SessionError("Session agent does not match agent definition")
                    if user_message is not None:
                        await self.session_store.append(
                            ctx.session_id,
                            (user_message,),
                            turn_id=str(ctx.run_id),
                            tenant_id=tenant_id,
                            run_id=ctx.run_id,
                            idempotency_key=f"{ctx.run_id}:input",
                            expected_revision=session.revision,
                        )
                    entries = await self.session_store.list_entries(
                        ctx.session_id, tenant_id=tenant_id
                    )
                    messages = [system_message, *(entry.message for entry in entries)]
                    await emit(
                        EventType.SESSION_LOADED,
                        revision=(
                            await self.session_store.get(ctx.session_id, tenant_id=tenant_id)
                        ).revision,
                        message_count=len(entries),
                    )
                retrieved_messages: list[Message] = []
                if _resume_approval is None and not _resume_session:
                    for source in self.context_sources:
                        retrieved_messages.extend(await source.retrieve(input, context=ctx))
                retrieved = tuple(retrieved_messages)
                if retrieved:
                    messages[-1:-1] = retrieved
                if _resume_approval is not None:
                    if self.approval_store is None:
                        raise ApprovalError("Approval store is unavailable")
                    call = _resume_approval.tool_call
                    if call.name not in agent.tools:
                        raise ApprovalError("Approved tool is no longer allowed by the agent")
                    governed_call, resume_action = await govern(call, GuardrailStage.TOOL_CALL)
                    if not isinstance(governed_call, type(call)):
                        raise GuardrailError("Tool-call guardrail must produce ToolCall")
                    if governed_call != call:
                        raise ApprovalError("A transformed call requires a new approval")
                    if resume_action in {
                        GuardrailAction.REJECT,
                        GuardrailAction.ABORT,
                        GuardrailAction.RETRY_WITH_FEEDBACK,
                    }:
                        raise GuardrailError("Approved tool no longer passes current policy")
                    claimed = await self.approval_store.claim(
                        _resume_approval.approval_id,
                        tenant_id=tenant_id,
                        expected_revision=_resume_approval.revision,
                    )
                    await emit(
                        EventType.APPROVAL_CLAIMED,
                        approval_id=claimed.approval_id,
                        tool_name=call.name,
                    )
                    if _resume_approval.status is ApprovalStatus.APPROVED:
                        result = await self.tools.execute_call(call, context=ctx, approved=True)
                        governed_result, result_action = await govern(
                            result, GuardrailStage.TOOL_RESULT
                        )
                        if result_action in {
                            GuardrailAction.REQUIRE_APPROVAL,
                            GuardrailAction.RETRY_WITH_FEEDBACK,
                        } or not isinstance(governed_result, ToolResult):
                            raise GuardrailError("Invalid approved tool-result decision")
                        result = governed_result
                    else:
                        result = ToolResult(
                            call_id=call.id,
                            tool_name=call.name,
                            status=ToolResultStatus.DENIED,
                            content={
                                "decision": _resume_approval.status.value,
                                "reason": _resume_approval.reason,
                            },
                        )
                    completed = await self.approval_store.complete(
                        claimed.approval_id,
                        tenant_id=tenant_id,
                        expected_revision=claimed.revision,
                    )
                    await emit(
                        EventType.APPROVAL_EXECUTED,
                        approval_id=completed.approval_id,
                        tool_name=call.name,
                        tool_executed=_resume_approval.status is ApprovalStatus.APPROVED,
                    )
                    usage = usage + Usage(tool_calls=1)
                    content = result.model_dump_json()
                    tool_message = Message.from_text(
                        MessageRole.TOOL,
                        content,
                        name=call.name,
                        tool_call_id=call.id,
                    )
                    messages.append(tool_message)
                    await persist((tool_message,), phase="approval_resolution", step=0)
                    await emit(
                        EventType.APPROVAL_RESOLVED,
                        approval_id=_resume_approval.approval_id,
                        decision=(
                            _resume_approval.decision.value
                            if _resume_approval.decision is not None
                            else "unknown"
                        ),
                        actor_id=_resume_approval.actor_id,
                    )
                for step in range(bound.max_steps):
                    if usage.model_calls >= bound.max_model_calls:
                        raise RunLimitExceededError("Model call limit reached")
                    await emit(EventType.STEP_STARTED, step=step)
                    settings: dict[str, Any] = {}
                    if bound.max_output_tokens is not None:
                        remaining_output = bound.max_output_tokens - usage.output_tokens
                        if remaining_output <= 0:
                            raise RunLimitExceededError("Output token budget exhausted")
                        settings["max_output_tokens"] = remaining_output
                    reserve = settings.get("max_output_tokens", 0)
                    if not isinstance(reserve, int):
                        reserve = 0
                    budget = context_budget or ContextBudget(
                        max_tokens=self.model.capabilities.max_context_tokens,
                        reserve_output_tokens=reserve,
                    )
                    last_selection = await self.context_policy.select(
                        tuple(messages), budget=budget
                    )
                    await emit(
                        EventType.CONTEXT_SELECTED,
                        source_message_count=last_selection.source_message_count,
                        selected_message_count=len(last_selection.messages),
                        removed_message_count=last_selection.removed_message_count,
                        summarized_message_count=last_selection.summarized_message_count,
                        estimated_tokens=last_selection.estimated_tokens,
                    )
                    request = ModelRequest(
                        messages=last_selection.messages,
                        tools=definitions,
                        output_schema=schema,
                        settings=settings,
                    )
                    governed_request, request_action = await govern(
                        request, GuardrailStage.MODEL_REQUEST
                    )
                    if request_action in {
                        GuardrailAction.REQUIRE_APPROVAL,
                        GuardrailAction.RETRY_WITH_FEEDBACK,
                    }:
                        raise GuardrailError(
                            "Model request guardrail returned an unsupported action"
                        )
                    if not isinstance(governed_request, ModelRequest):
                        raise GuardrailError("Model request guardrail must produce ModelRequest")
                    if self.data_policy is not None:
                        raw_provider_policy = getattr(self.model, "data_policy_metadata", {})
                        provider_policy = (
                            dict(raw_provider_policy)
                            if isinstance(raw_provider_policy, dict)
                            else {}
                        )
                        routing = getattr(self.model, "routing", None)
                        routing_data = getattr(routing, "data", None)
                        if routing_data is not None:
                            provider_policy = {
                                "zdr": getattr(routing_data, "require_zdr", False),
                                "allow_training": getattr(routing_data, "allow_training", None),
                            }
                        self.data_policy.authorize(
                            provider=agent.model.provider,
                            model=agent.model.name,
                            classification=classification,
                            provider_policy=provider_policy,
                        )
                        await emit(
                            EventType.PRIVACY_POLICY_EVALUATED,
                            classification=classification.name.lower(),
                            provider=agent.model.provider,
                            model=agent.model.name,
                        )
                    response, response_attempts, stream_summary = await generate_response(
                        governed_request, step
                    )
                    usage = usage + response.usage.model_copy(
                        update={"model_calls": 0, "tool_calls": 0}
                    )
                    await emit(
                        EventType.MODEL_RESPONSE_COMPLETED,
                        provider=response.metadata.get("provider", agent.model.provider),
                        requested_model=response.metadata.get("requested_model", agent.model.name),
                        resolved_model=response.metadata.get("resolved_model", response.model),
                        upstream_provider=response.metadata.get("upstream_provider"),
                        fallback_used=response.metadata.get("fallback_used", False),
                        route_attempt=response.metadata.get("route_attempt"),
                        response_id=response.id,
                        finish_reason=response.finish_reason.value,
                        attempts=response_attempts,
                        **stream_summary,
                    )
                    await emit(EventType.USAGE_UPDATED, usage=usage.model_dump(mode="json"))
                    check_usage()
                    if response.finish_reason in {
                        FinishReason.ERROR,
                        FinishReason.CONTENT_FILTER,
                        FinishReason.CANCELLED,
                        FinishReason.UNKNOWN,
                    }:
                        raise ModelResponseError("Model did not produce an accepted completion")
                    if response.finish_reason is FinishReason.LENGTH:
                        raise RunLimitExceededError("Model output length limit reached")
                    if response.tool_calls:
                        governed_calls: list[Any] = []
                        approval_required = False
                        for original_call in response.tool_calls:
                            governed_call, call_action = await govern(
                                original_call, GuardrailStage.TOOL_CALL
                            )
                            if call_action is GuardrailAction.RETRY_WITH_FEEDBACK:
                                raise GuardrailError(
                                    "Tool-call guardrails cannot request a model retry"
                                )
                            if not isinstance(governed_call, type(original_call)):
                                raise GuardrailError("Tool-call guardrail must produce ToolCall")
                            governed_calls.append(governed_call)
                            definition = self.tools.get(governed_call.name).definition
                            approval_required = approval_required or (
                                definition.requires_approval
                                or call_action is GuardrailAction.REQUIRE_APPROVAL
                            )
                        calls = tuple(governed_calls)
                        if usage.tool_calls + len(calls) > bound.max_tool_calls:
                            raise RunLimitExceededError("Tool call limit reached")
                        for call in calls:
                            if call.name not in agent.tools or call.id in used_ids:
                                raise ModelResponseError("Unauthorized tool or duplicate call ID")
                            used_ids.add(call.id)
                        assistant_message = Message(
                            role=MessageRole.ASSISTANT,
                            content=response.content,
                            tool_calls=calls,
                            metadata=response.metadata,
                        )
                        messages.append(assistant_message)
                        persisted_batch = [assistant_message]
                        if approval_required:
                            if len(calls) != 1:
                                raise ApprovalError(
                                    "An approval-gated response must contain exactly one tool call"
                                )
                            if (
                                self.approval_store is None
                                or self.session_store is None
                                or ctx.session_id is None
                            ):
                                raise ApprovalError(
                                    "Approval requires approval_store, session_store and session_id"
                                )
                            await persist((assistant_message,), phase="approval_request", step=step)
                            approval = ApprovalRequest.for_tool_call(
                                calls[0],
                                run_id=ctx.run_id,
                                trace_id=ctx.trace_id,
                                agent_id=agent.id,
                                session_id=ctx.session_id,
                                tenant_id=tenant_id,
                                ttl_seconds=self.approval_ttl_seconds,
                                metadata={
                                    "tool_risk": self.tools.get(calls[0].name).definition.risk.value
                                },
                                clock=self.clock,
                            )
                            approval = await self.approval_store.create(approval)
                            approval_id = approval.approval_id
                            status = RunStatus.WAITING_APPROVAL
                            await emit(
                                EventType.APPROVAL_REQUESTED,
                                approval_id=approval.approval_id,
                                tool_name=calls[0].name,
                                expires_at=(
                                    approval.expires_at.isoformat()
                                    if approval.expires_at is not None
                                    else None
                                ),
                            )
                            await emit(EventType.STEP_COMPLETED, step=step)
                            break
                        parallel_allowed = (
                            self.parallel_tool_calls
                            and self.model.capabilities.parallel_tool_calls
                            and len(calls) > 1
                            and all(
                                self.tools.get(call.name).definition.idempotent
                                and self.tools.get(call.name).definition.risk
                                in {ToolRisk.PURE, ToolRisk.READ}
                                for call in calls
                            )
                        )
                        semaphore = (
                            asyncio.Semaphore(bound.max_parallel_tools)
                            if parallel_allowed
                            else None
                        )

                        async def invoke_tool(
                            call: Any,
                            *,
                            _semaphore: asyncio.Semaphore | None = semaphore,
                        ) -> ToolResult | Exception:
                            await emit(
                                EventType.TOOL_CALL_REQUESTED, call_id=call.id, tool_name=call.name
                            )
                            try:
                                if _semaphore is None:
                                    await emit(
                                        EventType.TOOL_CALL_STARTED,
                                        call_id=call.id,
                                        tool_name=call.name,
                                    )
                                    return await self.tools.execute_call(call, context=ctx)
                                async with _semaphore:
                                    await emit(
                                        EventType.TOOL_CALL_STARTED,
                                        call_id=call.id,
                                        tool_name=call.name,
                                    )
                                    return await self.tools.execute_call(call, context=ctx)
                            except Exception as exc:
                                await emit(
                                    EventType.TOOL_CALL_FAILED,
                                    call_id=call.id,
                                    tool_name=call.name,
                                )
                                return exc

                        if parallel_allowed:
                            tool_outcomes = await asyncio.gather(
                                *(invoke_tool(call) for call in calls)
                            )
                        else:
                            tool_outcomes = []
                            for call in calls:
                                outcome = await invoke_tool(call)
                                tool_outcomes.append(outcome)
                                if isinstance(outcome, Exception) and (
                                    not recover_tool_errors or not isinstance(outcome, ToolError)
                                ):
                                    break

                        for call, outcome in zip(calls, tool_outcomes, strict=False):
                            usage = usage + Usage(tool_calls=1)
                            if isinstance(outcome, Exception):
                                if not recover_tool_errors or not isinstance(outcome, ToolError):
                                    raise outcome
                                content = json.dumps({"status": "failed", "call_id": call.id})
                            else:
                                result = outcome
                                governed_result, result_action = await govern(
                                    result, GuardrailStage.TOOL_RESULT
                                )
                                if result_action in {
                                    GuardrailAction.REQUIRE_APPROVAL,
                                    GuardrailAction.RETRY_WITH_FEEDBACK,
                                }:
                                    raise GuardrailError(
                                        "Tool-result guardrail returned an unsupported action"
                                    )
                                if not isinstance(governed_result, type(result)):
                                    raise GuardrailError(
                                        "Tool-result guardrail must produce ToolResult"
                                    )
                                result = governed_result
                                artifacts.extend(result.artifacts)
                                content = result.model_dump_json()
                                encoded = content.encode()
                                if (
                                    self.artifact_store is not None
                                    and len(encoded) > self.artifact_policy.inline_threshold_bytes
                                ):
                                    record = await self.artifact_store.put(
                                        encoded,
                                        name=f"tool-{call.name}-{call.id}.json",
                                        media_type="application/json",
                                        tenant_id=tenant_id,
                                        session_id=ctx.session_id,
                                        provenance={
                                            "agent_id": agent.id,
                                            "run_id": str(ctx.run_id),
                                            "tool_name": call.name,
                                            "tool_call_id": call.id,
                                        },
                                        ttl_seconds=self.artifact_policy.default_ttl_seconds,
                                    )
                                    artifacts.append(record.ref)
                                    content = json.dumps(
                                        {
                                            "status": "externalized",
                                            "artifact": record.ref.model_dump(mode="json"),
                                        },
                                        separators=(",", ":"),
                                    )
                                    await emit(
                                        EventType.ARTIFACT_CREATED,
                                        artifact_id=record.ref.artifact_id,
                                        media_type=record.ref.media_type,
                                        size_bytes=record.ref.size_bytes,
                                    )
                                await emit(
                                    EventType.TOOL_CALL_COMPLETED,
                                    call_id=call.id,
                                    tool_name=call.name,
                                )
                            tool_message = Message.from_text(
                                MessageRole.TOOL, content, name=call.name, tool_call_id=call.id
                            )
                            messages.append(tool_message)
                            persisted_batch.append(tool_message)
                        await persist(tuple(persisted_batch), phase="tool_cycle", step=step)
                    else:
                        text = "".join(p.text for p in response.content if p.type == "text")
                        governed_output, output_action = await govern(text, GuardrailStage.OUTPUT)
                        if output_action is GuardrailAction.REQUIRE_APPROVAL:
                            raise GuardrailError("Output approval is not supported in 0.5.0")
                        if output_action is GuardrailAction.RETRY_WITH_FEEDBACK:
                            if guardrail_retries >= 1:
                                raise GuardrailError("Output guardrail retry limit reached")
                            guardrail_retries += 1
                            messages.append(
                                Message.from_text(
                                    MessageRole.SYSTEM,
                                    "The previous output was rejected by policy. "
                                    "Produce a compliant answer.",
                                )
                            )
                            await emit(EventType.STEP_COMPLETED, step=step)
                            continue
                        if not isinstance(governed_output, str):
                            raise GuardrailError("Output guardrail must produce text")
                        output = (
                            adapter.validate_json(governed_output, strict=True)
                            if adapter
                            else governed_output
                        )
                        final_message = Message(
                            role=MessageRole.ASSISTANT,
                            content=(
                                response.content
                                if governed_output == text
                                else (TextContent(text=governed_output),)
                            ),
                            metadata=response.metadata,
                        )
                        messages.append(final_message)
                        await persist((final_message,), phase="final", step=step)
                        status = RunStatus.COMPLETED
                        await emit(EventType.STEP_COMPLETED, step=step)
                        break
                    await emit(EventType.STEP_COMPLETED, step=step)
                else:
                    raise RunLimitExceededError("Step limit reached")
        except asyncio.CancelledError:
            await emit(EventType.RUN_CANCELLED)
            raise
        except (RunLimitExceededError, ContextBudgetError, TimeoutError) as exc:
            status = RunStatus.LIMIT_EXCEEDED
            error = RunError(type="run.limit", message=str(exc) or "Run deadline reached")
        except Exception as exc:
            status = RunStatus.FAILED
            error = RunError(
                type="run.failed",
                message="Run failed; inspect sanitized events",
                details={"exception_type": type(exc).__name__},
            )
        terminal = {
            RunStatus.COMPLETED: EventType.RUN_COMPLETED,
            RunStatus.FAILED: EventType.RUN_FAILED,
            RunStatus.LIMIT_EXCEEDED: EventType.RUN_LIMIT_EXCEEDED,
            RunStatus.WAITING_APPROVAL: EventType.RUN_WAITING_APPROVAL,
        }[status]
        await emit(terminal)
        result_metadata: dict[str, Any] = {}
        if guardrail_audit:
            result_metadata["guardrails"] = guardrail_audit
        if approval_id is not None:
            result_metadata["approval_id"] = approval_id
        if ctx.session_id is not None:
            result_metadata["session_id"] = ctx.session_id
        if last_selection is not None and ctx.session_id is not None:
            result_metadata["context"] = {
                "source_message_count": last_selection.source_message_count,
                "selected_message_count": len(last_selection.messages),
                "removed_message_count": last_selection.removed_message_count,
                "summarized_message_count": last_selection.summarized_message_count,
                "estimated_tokens": last_selection.estimated_tokens,
                "decisions": [
                    decision.model_dump(mode="json") for decision in last_selection.decisions
                ],
            }
        return RunResult(
            run_id=ctx.run_id,
            trace_id=ctx.trace_id,
            agent_id=agent.id,
            status=status,
            output=output,
            error=error,
            usage=usage,
            started_at=started,
            completed_at=self.clock(),
            artifacts=tuple(artifacts),
            metadata=result_metadata,
        )
