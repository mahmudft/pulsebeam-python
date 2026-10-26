import asyncio
import json

import httpx
import pytest
import respx

from pulsebeam import AsyncPulsebeamClient, PostgrestError, PulsebeamConnectionError
from tests.conftest import BASE_URL, TODO_ROWS, todos


async def test_select_sends_query_params_and_returns_typed_page() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/todos").respond(200, json=TODO_ROWS, headers={"Content-Range": "0-1/2"})

        async with AsyncPulsebeamClient(BASE_URL) as client:
            page = await client.execute(todos.select().eq("done", False).with_count())

    assert route.calls.last.request.url.params.multi_items() == [("select", "*"), ("done", "eq.false")]
    assert page.rows == TODO_ROWS
    assert page.total == 2


async def test_insert_posts_rows_and_returns_created_rows() -> None:
    created = {"id": 3, "title": "Ship it", "done": False}
    with respx.mock(base_url=BASE_URL) as router:
        route = router.post("/todos").respond(201, json=[created])

        async with AsyncPulsebeamClient(BASE_URL) as client:
            rows = await client.execute(todos.insert([{"title": "Ship it"}]))

    assert json.loads(route.calls.last.request.content) == [{"title": "Ship it"}]
    assert rows == [created]


async def test_selects_run_concurrently_on_one_client() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/todos").respond(200, json=TODO_ROWS)

        async with AsyncPulsebeamClient(BASE_URL) as client:
            pages = await asyncio.gather(*(client.execute(todos.select().eq("id", i)) for i in range(5)))

    assert route.call_count == 5
    assert all(page.rows == TODO_ROWS for page in pages)


async def test_select_raises_postgrest_error_on_failure() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/todos").respond(404, json={"code": "42P01", "message": 'relation "todos" does not exist'})

        async with AsyncPulsebeamClient(BASE_URL) as client:
            with pytest.raises(PostgrestError, match="42P01"):
                await client.execute(todos.select())


async def test_transport_failure_is_wrapped() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/todos").mock(side_effect=httpx.ReadTimeout("timed out"))

        async with AsyncPulsebeamClient(BASE_URL) as client:
            with pytest.raises(PulsebeamConnectionError):
                await client.execute(todos.select())


async def test_exiting_context_closes_http_client() -> None:
    async with AsyncPulsebeamClient(BASE_URL) as client:
        pass

    assert client._http.is_closed
