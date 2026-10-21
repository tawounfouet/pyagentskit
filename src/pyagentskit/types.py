"""Reusable constrained scalar types."""

from typing import Annotated

from pydantic import StringConstraints

Identifier = Annotated[
    str,
    StringConstraints(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z][a-z0-9]*(?:[._-][a-z0-9]+)*$",
    ),
]
"""Stable lower-case identifier, optionally qualified with dots, dashes or underscores."""

SemanticVersion = Annotated[
    str,
    StringConstraints(
        min_length=5,
        max_length=64,
        pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
        r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
        r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$",
    ),
]
"""Semantic Versioning 2.0 compatible version string."""

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
