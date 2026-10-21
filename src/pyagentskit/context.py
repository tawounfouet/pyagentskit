"""Explainable context selection and conservative token budgeting."""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field, field_validator

from ._base import ContractModel
from .exceptions import ContextBudgetError
from .messages import Message, MessageRole
from .runs import RunContext

__all__ = [
    "ContextAction",
    "ContextBudget",
    "ContextDecision",
    "ContextPolicy",
    "ContextSelection",
    "ContextSource",
    "FullContextPolicy",
    "SummarizingContextPolicy",
    "WindowContextPolicy",
    "estimate_message_tokens",
]


class ContextAction(StrEnum):
    """Reason recorded for each context transformation."""

    KEEP = "keep"
    DROP = "drop"
    SUMMARIZE = "summarize"


class ContextBudget(ContractModel):
    """Approximate input budget used before a provider call."""

    max_tokens: int | None = Field(default=None, gt=0)
    reserve_output_tokens: int = Field(default=0, ge=0)
    chars_per_token: float = Field(default=4.0, gt=0)

    @field_validator("chars_per_token")
    @classmethod
    def validate_finite_ratio(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("chars_per_token must be finite")
        return value

    @property
    def available_tokens(self) -> int | None:
        if self.max_tokens is None:
            return None
        available = self.max_tokens - self.reserve_output_tokens
        if available <= 0:
            raise ContextBudgetError("Output reserve exhausts the model context window")
        return available


class ContextDecision(ContractModel):
    """Auditable decision for one source message or synthetic summary."""

    action: ContextAction
    source_indexes: tuple[int, ...]
    reason: str
    estimated_tokens: int = Field(ge=0)


class ContextSelection(ContractModel):
    """Messages selected for a model call plus an explanation."""

    messages: tuple[Message, ...]
    estimated_tokens: int = Field(ge=0)
    source_message_count: int = Field(ge=0)
    removed_message_count: int = Field(ge=0)
    summarized_message_count: int = Field(default=0, ge=0)
    decisions: tuple[ContextDecision, ...] = ()


@runtime_checkable
class ContextPolicy(Protocol):
    """Select an explainable bounded model context."""

    async def select(
        self, messages: tuple[Message, ...], *, budget: ContextBudget
    ) -> ContextSelection: ...


@runtime_checkable
class ContextSource(Protocol):
    """Optional external memory/RAG hook; retrieval implementation is application-owned."""

    async def retrieve(self, query: str, *, context: RunContext[Any]) -> tuple[Message, ...]: ...


def estimate_message_tokens(message: Message, *, chars_per_token: float = 4.0) -> int:
    """Return a conservative deterministic approximation, including structure/metadata."""

    return max(1, math.ceil(len(message.model_dump_json()) / chars_per_token))


def _message_groups(messages: tuple[Message, ...]) -> list[tuple[int, ...]]:
    """Keep assistant tool calls and their immediately following results atomic."""

    groups: list[tuple[int, ...]] = []
    index = 0
    while index < len(messages):
        message = messages[index]
        if message.role is MessageRole.ASSISTANT and message.tool_calls:
            call_ids = {call.id for call in message.tool_calls}
            group = [index]
            cursor = index + 1
            while (
                cursor < len(messages)
                and messages[cursor].role is MessageRole.TOOL
                and messages[cursor].tool_call_id in call_ids
            ):
                group.append(cursor)
                cursor += 1
            groups.append(tuple(group))
            index = cursor
        else:
            groups.append((index,))
            index += 1
    return groups


class FullContextPolicy:
    """Keep every message, failing before networking when a known budget is exceeded."""

    async def select(
        self, messages: tuple[Message, ...], *, budget: ContextBudget
    ) -> ContextSelection:
        costs = [
            estimate_message_tokens(item, chars_per_token=budget.chars_per_token)
            for item in messages
        ]
        total = sum(costs)
        available = budget.available_tokens
        if available is not None and total > available:
            raise ContextBudgetError("Full conversation exceeds the context budget")
        return ContextSelection(
            messages=messages,
            estimated_tokens=total,
            source_message_count=len(messages),
            removed_message_count=0,
            decisions=tuple(
                ContextDecision(
                    action=ContextAction.KEEP,
                    source_indexes=(index,),
                    reason="full_context",
                    estimated_tokens=cost,
                )
                for index, cost in enumerate(costs)
            ),
        )


class WindowContextPolicy:
    """Keep system messages and the newest complete message/tool groups."""

    def __init__(self, *, max_messages: int | None = None) -> None:
        if max_messages is not None and max_messages <= 0:
            raise ValueError("max_messages must be positive")
        self.max_messages = max_messages

    async def select(
        self, messages: tuple[Message, ...], *, budget: ContextBudget
    ) -> ContextSelection:
        if not messages:
            raise ContextBudgetError("Context cannot be empty")
        costs = [
            estimate_message_tokens(item, chars_per_token=budget.chars_per_token)
            for item in messages
        ]
        available = budget.available_tokens
        groups = _message_groups(messages)
        required = {index for index, item in enumerate(messages) if item.role is MessageRole.SYSTEM}
        required.update(next(group for group in groups if len(messages) - 1 in group))
        selected = set(required)
        used = sum(costs[index] for index in selected)
        if available is not None and used > available:
            raise ContextBudgetError("Required system/current messages exceed the context budget")
        for group in reversed(groups):
            candidates = set(group) - selected
            if not candidates:
                continue
            if (
                self.max_messages is not None
                and len(selected) + len(candidates) > self.max_messages
            ):
                continue
            group_cost = sum(costs[index] for index in candidates)
            if available is not None and used + group_cost > available:
                continue
            selected.update(candidates)
            used += group_cost
        ordered = tuple(messages[index] for index in sorted(selected))
        decisions = tuple(
            ContextDecision(
                action=ContextAction.KEEP if index in selected else ContextAction.DROP,
                source_indexes=(index,),
                reason="required_or_recent" if index in selected else "window_or_budget",
                estimated_tokens=cost,
            )
            for index, cost in enumerate(costs)
        )
        return ContextSelection(
            messages=ordered,
            estimated_tokens=used,
            source_message_count=len(messages),
            removed_message_count=len(messages) - len(ordered),
            decisions=decisions,
        )


SummaryFunction = Callable[[tuple[Message, ...]], Awaitable[str]]


class SummarizingContextPolicy:
    """Summarize messages removed by a window policy through an injected function."""

    def __init__(
        self,
        summarizer: SummaryFunction,
        *,
        max_messages: int | None = None,
        max_summary_tokens: int = 512,
    ) -> None:
        if max_summary_tokens <= 0:
            raise ValueError("max_summary_tokens must be positive")
        self.summarizer = summarizer
        self.window = WindowContextPolicy(max_messages=max_messages)
        self.max_summary_tokens = max_summary_tokens

    async def select(
        self, messages: tuple[Message, ...], *, budget: ContextBudget
    ) -> ContextSelection:
        selected = await self.window.select(messages, budget=budget)
        removed_indexes = tuple(
            index
            for decision in selected.decisions
            if decision.action is ContextAction.DROP
            for index in decision.source_indexes
        )
        if not removed_indexes:
            return selected
        summary_text = await self.summarizer(tuple(messages[index] for index in removed_indexes))
        if not isinstance(summary_text, str) or not summary_text.strip():
            raise ContextBudgetError("Summarizer returned an invalid summary")
        summary = Message.from_text(
            MessageRole.SYSTEM,
            "Conversation summary:\n" + summary_text.strip(),
            metadata={"context_summary": True},
        )
        summary_cost = estimate_message_tokens(summary, chars_per_token=budget.chars_per_token)
        if summary_cost > self.max_summary_tokens:
            raise ContextBudgetError("Summary exceeds max_summary_tokens")
        available = budget.available_tokens
        if available is not None and selected.estimated_tokens + summary_cost > available:
            raise ContextBudgetError("Summary does not fit the context budget")
        insertion = 0
        while (
            insertion < len(selected.messages)
            and selected.messages[insertion].role is MessageRole.SYSTEM
        ):
            insertion += 1
        result = (*selected.messages[:insertion], summary, *selected.messages[insertion:])
        decisions = (
            *selected.decisions,
            ContextDecision(
                action=ContextAction.SUMMARIZE,
                source_indexes=removed_indexes,
                reason="summarizer",
                estimated_tokens=summary_cost,
            ),
        )
        return selected.model_copy(
            update={
                "messages": result,
                "estimated_tokens": selected.estimated_tokens + summary_cost,
                "summarized_message_count": len(removed_indexes),
                "decisions": decisions,
            }
        )
