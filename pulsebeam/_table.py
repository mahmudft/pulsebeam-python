from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic

from pulsebeam._query import InsertQuery, SelectQuery
from pulsebeam._types import InsertT, RowT


@dataclass(frozen=True)
class Table(Generic[RowT, InsertT]):
    """A PostgREST table or view, typed by the rows it returns and the rows it accepts on insert.

    Declare one per table with explicit type arguments, e.g. ``Table[Todo, NewTodo]("todos")``.
    Every query and result derived from it then carries those types.
    """

    name: str

    def select(self) -> SelectQuery[RowT]:
        return SelectQuery(table=self.name)

    def insert(self, rows: Sequence[InsertT]) -> InsertQuery[RowT]:
        return InsertQuery(table=self.name, rows=tuple(dict(row) for row in rows))
