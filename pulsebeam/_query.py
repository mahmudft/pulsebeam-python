import re
from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Generic, Self

from pulsebeam._types import CountMode, RowT, Scalar

# PostgREST splits `in.(...)` lists on commas and parentheses, so items containing them, quotes,
# backslashes or whitespace must be double-quoted.
_NEEDS_QUOTING = re.compile(r'[,()"\\\s]')


def _encode(value: Scalar) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _encode_list_item(value: Scalar) -> str:
    text = _encode(value)
    if text and not _NEEDS_QUOTING.search(text):
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


@dataclass(frozen=True)
class SelectQuery(Generic[RowT]):
    """An immutable description of a read. Every builder method returns a new query.

    It performs no I/O: the same query runs on either client, which is what keeps the sync and
    async paths identical.
    """

    table: str
    filters: tuple[tuple[str, str], ...] = ()
    orders: tuple[str, ...] = ()
    row_limit: int | None = None
    row_offset: int | None = None
    count_mode: CountMode | None = None

    def eq(self, column: str, value: Scalar) -> Self:
        return self._filter(column, f"eq.{_encode(value)}")

    def neq(self, column: str, value: Scalar) -> Self:
        return self._filter(column, f"neq.{_encode(value)}")

    def gt(self, column: str, value: int | float | str) -> Self:
        return self._filter(column, f"gt.{_encode(value)}")

    def gte(self, column: str, value: int | float | str) -> Self:
        return self._filter(column, f"gte.{_encode(value)}")

    def lt(self, column: str, value: int | float | str) -> Self:
        return self._filter(column, f"lt.{_encode(value)}")

    def lte(self, column: str, value: int | float | str) -> Self:
        return self._filter(column, f"lte.{_encode(value)}")

    def like(self, column: str, pattern: str) -> Self:
        """``pattern`` uses ``*`` as the wildcard, as PostgREST expects in a URL."""
        return self._filter(column, f"like.{pattern}")

    def ilike(self, column: str, pattern: str) -> Self:
        return self._filter(column, f"ilike.{pattern}")

    def in_(self, column: str, values: Sequence[Scalar]) -> Self:
        if isinstance(values, str):
            raise TypeError("in_() takes a sequence of values, not a single string")
        items = ",".join(_encode_list_item(value) for value in values)
        return self._filter(column, f"in.({items})")

    def is_(self, column: str, value: bool | None) -> Self:
        return self._filter(column, f"is.{'null' if value is None else _encode(value)}")

    def order(self, column: str, *, descending: bool = False, nulls_first: bool | None = None) -> Self:
        term = f"{column}.{'desc' if descending else 'asc'}"
        if nulls_first is not None:
            term += ".nullsfirst" if nulls_first else ".nullslast"
        return replace(self, orders=(*self.orders, term))

    def limit(self, count: int) -> Self:
        if count < 0:
            raise ValueError("limit must not be negative")
        return replace(self, row_limit=count)

    def offset(self, count: int) -> Self:
        if count < 0:
            raise ValueError("offset must not be negative")
        return replace(self, row_offset=count)

    def with_count(self, mode: CountMode = "exact") -> Self:
        """Ask PostgREST for the total row count, returned as ``Page.total``."""
        return replace(self, count_mode=mode)

    def to_params(self) -> list[tuple[str, str]]:
        params: list[tuple[str, str]] = [("select", "*"), *self.filters]
        if self.orders:
            params.append(("order", ",".join(self.orders)))
        if self.row_limit is not None:
            params.append(("limit", str(self.row_limit)))
        if self.row_offset is not None:
            params.append(("offset", str(self.row_offset)))
        return params

    def _filter(self, column: str, expression: str) -> Self:
        return replace(self, filters=(*self.filters, (column, expression)))


@dataclass(frozen=True)
class InsertQuery(Generic[RowT]):
    """Rows to insert, typed by the row PostgREST sends back. Build it with ``Table.insert()``."""

    table: str
    rows: tuple[dict[str, object], ...]
