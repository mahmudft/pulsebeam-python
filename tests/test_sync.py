import json

import httpx
import pytest
import respx

from pulsebeam import PostgrestError, PulsebeamClient, PulsebeamConnectionError
from tests.conftest import BASE_URL, TODO_ROWS, todos


def test_select_sends_query_params_and_returns_typed_page() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/todos").respond(200, json=TODO_ROWS, headers={"Content-Range": "0-1/2"})

        with PulsebeamClient(BASE_URL) as client:
            page = client.execute(todos.select().eq("done", False).order("id").limit(2).with_count())

    request = route.calls.last.request
    assert request.url.params.multi_items() == [
        ("select", "*"),
        ("done", "eq.false"),
        ("order", "id.asc"),
        ("limit", "2"),
    ]
    assert request.headers["Prefer"] == "count=exact"
    assert page.rows == TODO_ROWS
    assert page.total == 2


def test_insert_posts_rows_and_returns_created_rows() -> None:
    created = {"id": 3, "title": "Ship it", "done": False}
    with respx.mock(base_url=BASE_URL) as router:
        route = router.post("/todos").respond(201, json=[created])

        with PulsebeamClient(BASE_URL) as client:
            rows = client.execute(todos.insert([{"title": "Ship it"}]))

    request = route.calls.last.request
    assert json.loads(request.content) == [{"title": "Ship it"}]
    assert request.headers["Prefer"] == "return=representation"
    assert rows == [created]


def test_insert_skips_the_request_for_no_rows() -> None:
    with respx.mock(base_url=BASE_URL, assert_all_called=False) as router:
        route = router.post("/todos")

        with PulsebeamClient(BASE_URL) as client:
            assert client.execute(todos.insert([])) == []

    assert not route.called


def test_token_is_sent_as_bearer() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        route = router.get("/todos").respond(200, json=[])

        with PulsebeamClient(BASE_URL, token="jwt") as client:
            client.execute(todos.select())

    assert route.calls.last.request.headers["Authorization"] == "Bearer jwt"


def test_select_raises_postgrest_error_on_failure() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/todos").respond(401, json={"code": "PGRST301", "message": "JWT expired"})

        with PulsebeamClient(BASE_URL) as client, pytest.raises(PostgrestError) as caught:
            client.execute(todos.select())

    assert caught.value.code == "PGRST301"


def test_transport_failure_is_wrapped() -> None:
    with respx.mock(base_url=BASE_URL) as router:
        router.get("/todos").mock(side_effect=httpx.ConnectError("connection refused"))

        with PulsebeamClient(BASE_URL) as client, pytest.raises(PulsebeamConnectionError):
            client.execute(todos.select())


def test_exiting_context_closes_http_client() -> None:
    with PulsebeamClient(BASE_URL) as client:
        pass

    assert client._http.is_closed
