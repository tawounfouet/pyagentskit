"""Run a complete tool cycle without credentials or a network connection."""

from pyagentskit import (
    AgentDefinition,
    FinishReason,
    ModelRef,
    ModelResponse,
    TextContent,
    ToolCall,
    ToolRegistry,
    tool,
)
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


@tool(idempotent=True)
def add_one(value: int) -> int:
    """Add one to an integer."""
    return value + 1


def main() -> None:
    model = FakeModel(
        [
            ModelResponse(
                id="r1",
                model="demo",
                finish_reason=FinishReason.TOOL_CALLS,
                tool_calls=(ToolCall(id="c1", name="add_one", arguments={"value": 2}),),
            ),
            ModelResponse(
                id="r2",
                model="demo",
                finish_reason=FinishReason.STOP,
                content=(TextContent(text="The answer is 3."),),
            ),
        ]
    )
    definition = AgentDefinition(
        id="demo",
        version="1.0.0",
        instructions="Help the user.",
        model=ModelRef(provider="fake", name="demo"),
        tools=("add_one",),
    )
    result = Runner(model, tools=ToolRegistry([add_one])).run_sync(definition, "Add one to two")
    assert result.output == "The answer is 3."
    print(result.model_dump_json())


if __name__ == "__main__":
    main()
