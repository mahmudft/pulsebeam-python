"""Type-level tests.

The ``_check_*`` functions are never called; they exist for mypy. ``assert_type`` pins the inferred
types, and each ``# type: ignore[...]`` marks a line that must stay a type error: with ``strict``
enabled, mypy reports an unused ignore if the error ever disappears. ``test_mypy_strict_passes``
runs mypy so that ``pytest`` alone covers both layers.
"""

from pathlib import Path
from typing import assert_type

from mypy import api

from pulsebeam import AsyncPulsebeamClient, InsertQuery, Page, PulsebeamClient, SelectQuery
from tests.conftest import Todo, todos

ROOT = Path(__file__).resolve().parent.parent


def _check_row_type_flows_from_table(client: PulsebeamClient) -> None:
    query = todos.select().eq("done", False).order("id").limit(10)
    assert_type(query, SelectQuery[Todo])

    page = client.execute(query)
    assert_type(page, Page[Todo])
    assert_type(page.rows[0]["title"], str)
    assert_type(page.total, int | None)

    insert = todos.insert([{"title": "Ship it"}, {"title": "Review it", "done": True}])
    assert_type(insert, InsertQuery[Todo])

    created = client.execute(insert)
    assert_type(created, list[Todo])


async def _check_async_client_matches_sync(client: AsyncPulsebeamClient) -> None:
    assert_type(await client.execute(todos.select()), Page[Todo])
    assert_type(await client.execute(todos.insert([{"title": "Ship it"}])), list[Todo])


def _check_invalid_usage(client: PulsebeamClient) -> None:
    page = client.execute(todos.select())
    page.rows[0]["titel"]  # type: ignore[typeddict-item]
    client.execute(todos.insert([{"done": True}]))  # type: ignore[typeddict-item]
    client.execute(todos.insert([{"id": 1, "title": "x", "done": False}]))  # type: ignore[typeddict-unknown-key]
    todos.select().eq("done", None)  # type: ignore[arg-type]
    todos.select().gt("id", [1, 2])  # type: ignore[arg-type]
    todos.select().with_count("approximate")  # type: ignore[arg-type]


def test_mypy_strict_passes() -> None:
    stdout, stderr, status = api.run(
        ["--config-file", str(ROOT / "pyproject.toml"), str(ROOT / "pulsebeam"), str(ROOT / "tests"), str(ROOT / "examples")]
    )

    assert status == 0, stdout + stderr
