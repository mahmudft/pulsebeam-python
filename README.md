# pulsebeam-python

A strictly typed query builder for [PostgREST](https://postgrest.org), with matching synchronous
and asynchronous clients.

```python
from typing import NotRequired, TypedDict

from pulsebeam import PulsebeamClient, Table


class Todo(TypedDict):
    id: int
    title: str
    done: bool


class NewTodo(TypedDict):
    title: str
    done: NotRequired[bool]


todos = Table[Todo, NewTodo]("todos")

with PulsebeamClient("http://localhost:3000") as client:
    page = client.execute(todos.select().eq("done", False).order("id").limit(20).with_count())
    for todo in page.rows:          # list[Todo]
        print(todo["title"])        # str
    print(page.total)               # int | None

    [created] = client.execute(todos.insert([{"title": "Ship it"}]))  # Todo
```

## Design

- **Types flow from one declaration.** `Table[Row, Insert]` fixes the row type a table returns
  and the shape it accepts on insert. `select()` produces a `SelectQuery[Row]`, executing it
  produces a `Page[Row]`, and `insert()` only accepts `Insert` rows. Nothing is typed `Any`: mypy
  runs in `strict` mode with `disallow_any_explicit`.
- **A pure core, two thin clients.** Queries are immutable dataclasses with no I/O. `_wire.py`
  turns them into request specs and parses responses, and both `PulsebeamClient` (`httpx.Client`)
  and `AsyncPulsebeamClient` (`httpx.AsyncClient`) just send them. The sync and async paths
  share every line of behaviour, so they cannot drift.
- **One overloaded entry point.** `execute()` returns `Page[Row]` for a select and `list[Row]`
  for an insert, resolved by `@overload` at type-check time.
- **Errors you can branch on.** Non-2xx responses raise `PostgrestError` with PostgREST's
  `code`, `message`, `details` and `hint`. Network failures raise `PulsebeamConnectionError`,
  and a malformed success body raises `UnexpectedResponseError`. All share `PulsebeamError`.

## Query reference

| Builder | PostgREST |
|---|---|
| `.eq/neq/gt/gte/lt/lte(col, v)` | `col=eq.v` and so on |
| `.like/ilike(col, "*text*")` | `col=like.*text*` |
| `.in_(col, [a, b])` | `col=in.(a,b)`, with quoting for commas, parentheses, quotes and spaces |
| `.is_(col, None \| True \| False)` | `col=is.null` |
| `.order(col, descending=True, nulls_first=False)` | `order=col.desc.nullslast` |
| `.limit(n)`, `.offset(n)` | `limit=n`, `offset=n` |
| `.with_count("exact" \| "planned" \| "estimated")` | `Prefer: count=…`, read back into `Page.total` |

Pass `token=` to either client to send a JWT as `Authorization: Bearer …`.

## Async

The async client has the same surface, so queries can be shared and run concurrently:

```python
import asyncio

from pulsebeam import AsyncPulsebeamClient

async with AsyncPulsebeamClient("http://localhost:3000") as client:
    done, still_open = await asyncio.gather(
        client.execute(todos.select().eq("done", True).with_count()),
        client.execute(todos.select().eq("done", False).with_count()),
    )
```

## Development

Requires Python 3.11+.

```bash
pip install -e ".[test]"
pytest
```

The suite has three layers:

- **Unit tests.** `test_query.py` and `test_wire.py` cover encoding and parsing without HTTP.
  `test_sync.py` and `test_async.py` cover both clients against `respx`-stubbed responses.
- **Type-level tests.** `test_typing.py` pins inferred types with `assert_type` and asserts that
  misuse, such as a misspelled column key, a missing required insert field or a wrong filter
  value type, stays a type error. The suite runs mypy itself, so a typing regression fails
  `pytest`.
- **Integration tests.** `test_integration.py` runs against a real PostgREST. They are skipped
  unless `PULSEBEAM_TEST_URL` is set:

  ```bash
  docker compose up -d
  PULSEBEAM_TEST_URL=http://localhost:3000 pytest tests/test_integration.py
  python examples/todos.py
  docker compose down -v
  ```

## Not covered yet

Update, delete, upsert, embedded resources (`select=*,author(*)`), column projection and
RPC calls.
