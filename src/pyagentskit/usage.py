"""Provider-neutral usage accounting."""

from decimal import Decimal

from pydantic import Field

from ._base import ContractModel


class Usage(ContractModel):
    """Cumulative usage reported or estimated for model and tool operations."""

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    estimated_cost_usd: Decimal | None = Field(default=None, ge=0)

    @property
    def total_tokens(self) -> int:
        """Return billable input and output tokens without double-counting subcategories."""

        return self.input_tokens + self.output_tokens

    def __add__(self, other: "Usage") -> "Usage":
        if not isinstance(other, Usage):
            return NotImplemented
        if self.estimated_cost_usd is None and other.estimated_cost_usd is None:
            cost = None
        else:
            cost = (self.estimated_cost_usd or Decimal(0)) + (
                other.estimated_cost_usd or Decimal(0)
            )
        return Usage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cached_input_tokens=self.cached_input_tokens + other.cached_input_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
            model_calls=self.model_calls + other.model_calls,
            tool_calls=self.tool_calls + other.tool_calls,
            estimated_cost_usd=cost,
        )
