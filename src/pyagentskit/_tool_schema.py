"""Callable inspection and Pydantic validation for function tools."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, get_origin, get_type_hints

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError, create_model

from .exceptions import ToolValidationError
from .runs import RunContext


def _is_context_annotation(annotation: Any) -> bool:
    return annotation is RunContext or get_origin(annotation) is RunContext


@dataclass(frozen=True, slots=True)
class CallableSchema:
    """Compiled validators and JSON schemas for one callable."""

    arguments_model: type[BaseModel]
    result_adapter: TypeAdapter[Any] | None
    context_parameter: str | None
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None

    def validate_arguments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Validate untrusted model arguments without coercion."""

        try:
            validated = self.arguments_model.model_validate(arguments)
        except ValidationError as error:
            raise ToolValidationError("Tool arguments failed schema validation") from error
        return {name: getattr(validated, name) for name in type(validated).model_fields}

    def validate_result(self, value: Any) -> Any:
        """Validate a callable result against its return annotation."""

        if self.result_adapter is None:
            return value
        try:
            return self.result_adapter.validate_python(value, strict=True)
        except ValidationError as error:
            raise ToolValidationError("Tool result failed schema validation") from error


def compile_callable_schema(function: Any) -> CallableSchema:
    """Compile a function signature into strict validators and JSON schemas."""

    signature = inspect.signature(function)
    try:
        hints = get_type_hints(function, include_extras=True)
    except (NameError, TypeError) as error:
        raise ToolValidationError("Tool annotations could not be resolved") from error

    fields: dict[str, Any] = {}
    context_parameter: str | None = None
    for parameter in signature.parameters.values():
        if parameter.kind in {parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD}:
            raise ToolValidationError("Tool functions cannot declare *args or **kwargs")
        if parameter.kind is parameter.POSITIONAL_ONLY:
            raise ToolValidationError("Tool functions cannot declare positional-only parameters")

        annotation = hints.get(parameter.name, parameter.annotation)
        if annotation is inspect.Parameter.empty:
            raise ToolValidationError(
                f"Tool parameter '{parameter.name}' requires a type annotation"
            )
        if _is_context_annotation(annotation):
            if context_parameter is not None:
                raise ToolValidationError(
                    "Tool functions may declare only one RunContext parameter"
                )
            context_parameter = parameter.name
            continue

        default = ... if parameter.default is inspect.Parameter.empty else parameter.default
        fields[parameter.name] = (annotation, default)

    model_name = f"_{function.__name__.title().replace('_', '')}Arguments"
    arguments_model = create_model(
        model_name,
        __config__=ConfigDict(extra="forbid", strict=True),
        **fields,
    )

    return_annotation = hints.get("return", signature.return_annotation)
    if return_annotation in {inspect.Signature.empty, Any}:
        result_adapter = None
        output_schema = None
    else:
        try:
            result_adapter = TypeAdapter(return_annotation)
            output_schema = result_adapter.json_schema()
        except (TypeError, ValueError) as error:
            raise ToolValidationError("Tool return annotation is not supported") from error

    return CallableSchema(
        arguments_model=arguments_model,
        result_adapter=result_adapter,
        context_parameter=context_parameter,
        input_schema=arguments_model.model_json_schema(),
        output_schema=output_schema,
    )
