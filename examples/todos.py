"""Lists open todos, adds one, and shows the same queries on the async client.

Run ``docker compose up -d`` first, then ``python examples/todos.py``.
"""

import asyncio
from typing import NotRequired, TypedDict

from pulsebeam import AsyncPulsebeamClient, PulsebeamClient, Table

URL = "http://localhost:3000"


class Todo(TypedDict):
    id: int
    title: str
    done: bool


class NewTodo(TypedDict):
    title: str
    done: NotRequired[bool]


todos = Table[Todo, NewTodo]("todos")
open_todos = todos.select().eq("done", False).order("id").with_count()


def main() -> None:
    with PulsebeamClient(URL) as client:
        page = client.execute(open_todos)
        print(f"{page.total} open:")
        for todo in page.rows:
            print(f"  #{todo['id']} {todo['title']}")

        [created] = client.execute(todos.insert([{"title": "Try pulsebeam"}]))
        print(f"created #{created['id']}")


async def main_async() -> None:
    async with AsyncPulsebeamClient(URL) as client:
        done, still_open = await asyncio.gather(
            client.execute(todos.select().eq("done", True).with_count()),
            client.execute(open_todos),
        )
        print(f"done: {done.total}, open: {still_open.total}")


if __name__ == "__main__":
    main()
    asyncio.run(main_async())
