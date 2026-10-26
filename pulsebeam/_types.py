from collections.abc import Mapping
from typing import Literal, TypeVar

RowT = TypeVar("RowT", bound=Mapping[str, object])
InsertT = TypeVar("InsertT", bound=Mapping[str, object])

Scalar = str | int | float | bool
CountMode = Literal["exact", "planned", "estimated"]
