import httpx
import pytest

from pulsebeam import PostgrestError, UnexpectedResponseError
from pulsebeam._wire import build_insert, build_select, default_headers, parse_page
from tests.conftest import TODO_ROWS, todos


def test_build_select_adds_count_preference_only_when_requested() -> None:
    assert build_select(todos.select()).headers == {}
    assert build_select(todos.select().with_count()).headers == {"Prefer": "count=exact"}


def test_build_insert_asks_for_inserted_rows_back() -> None:
    spec = build_insert(todos.insert([{"title": "Ship it"}]))

    assert (spec.method, spec.path, spec.body) == ("POST", "/todos", [{"title": "Ship it"}])
    assert spec.headers == {"Prefer": "return=representation"}


def test_default_headers_include_bearer_token_only_when_given() -> None:
    assert "Authorization" not in default_headers(None)
    assert default_headers("jwt")["Authorization"] == "Bearer jwt"


@pytest.mark.parametrize(
    ("content_range", "expected"),
    [("0-1/42", 42), ("*/0", 0), ("0-1/*", None), (None, None), ("garbage", None)],
)
def test_parse_page_reads_total_from_content_range(content_range: str | None, expected: int | None) -> None:
    headers = {"Content-Range": content_range} if content_range else {}
    response = httpx.Response(200, json=TODO_ROWS, headers=headers)

    page = parse_page(todos.select(), response)

    assert page.rows == TODO_ROWS
    assert page.total == expected


def test_parse_page_maps_postgrest_error_body() -> None:
    body = {"code": "42703", "message": "column todos.titel does not exist", "details": None, "hint": "Perhaps title"}

    with pytest.raises(PostgrestError) as caught:
        parse_page(todos.select(), httpx.Response(400, json=body))

    error = caught.value
    assert (error.status_code, error.code, error.message, error.details, error.hint) == (
        400,
        "42703",
        "column todos.titel does not exist",
        None,
        "Perhaps title",
    )
    assert str(error) == "400 42703: column todos.titel does not exist"


def test_parse_page_falls_back_to_raw_text_for_non_json_errors() -> None:
    with pytest.raises(PostgrestError, match="502: upstream down"):
        parse_page(todos.select(), httpx.Response(502, text="upstream down"))


@pytest.mark.parametrize("body", [{"id": 1}, [1, 2], "rows"])
def test_parse_page_rejects_bodies_that_are_not_arrays_of_objects(body: object) -> None:
    with pytest.raises(UnexpectedResponseError):
        parse_page(todos.select(), httpx.Response(200, json=body))


def test_parse_page_rejects_non_json_success_body() -> None:
    with pytest.raises(UnexpectedResponseError, match="not JSON"):
        parse_page(todos.select(), httpx.Response(200, text="<html>"))
