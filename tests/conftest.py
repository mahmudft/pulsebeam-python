from typing import NotRequired, TypedDict

from pulsebeam import Table

BASE_URL = "http://postgrest.test"


class Todo(TypedDict):
    id: int
    title: str
    done: bool


class NewTodo(TypedDict):
    title: str
    done: NotRequired[bool]


todos = Table[Todo, NewTodo]("todos")

TODO_ROWS: list[Todo] = [
    {"id": 1, "title": "Write the query builder", "done": True},
    {"id": 2, "title": "Add the async client", "done": False},
]
