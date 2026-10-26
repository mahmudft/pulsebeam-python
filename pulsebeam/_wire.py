"""Translation between queries and HTTP, shared by both clients and free of I/O."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Generic, Literal, cast

import httpx

from pulsebeam._query import InsertQuery, SelectQuery
from pulsebeam._types import RowT
from pulsebeam._version import __version__
from pulsebeam.errors import PostgrestError, UnexpectedResponseError

_CONTENT_RANGE = re.compile(r"^(?:\d+-\d+|\*)/(\d+|\*)$")


@dataclass(frozen=True)
class Page(Generic[RowT]):
    rows: list[RowT]
    total: int | None
    """Set only when the query asked for a count with ``with_count()``."""


@dataclass(frozen=True)
class RequestSpec:
    method: Literal["GET", "POST"]
    path: str
    params: tuple[tuple[str, str], ...]
    headers: dict[str, str]
    body: list[dict[str, object]] | None = None


def default_headers(token: str | None) -> dict[str, str]:
    headers = {
        "Accept": "application/json",
        "User-Agent": f"pulsebeam-python/{__version__}",
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def build_select(query: SelectQuery[RowT]) -> RequestSpec:
    headers = {"Prefer": f"count={query.count_mode}"} if query.count_mode else {}
    return RequestSpec("GET", f"/{query.table}", tuple(query.to_params()), headers)


def build_insert(query: InsertQuery[RowT]) -> RequestSpec:
    return RequestSpec("POST", f"/{query.table}", (), {"Prefer": "return=representation"}, list(query.rows))


def parse_page(query: SelectQuery[RowT], response: httpx.Response) -> Page[RowT]:
    """``query`` is only read for its type: it is what ties the returned rows to ``RowT``."""
    rows = _parse_rows(response)
    return Page(rows=cast(list[RowT], rows), total=_parse_total(response.headers.get("Content-Range")))


def parse_inserted(query: InsertQuery[RowT], response: httpx.Response) -> list[RowT]:
    return cast(list[RowT], _parse_rows(response))


def _parse_rows(response: httpx.Response) -> list[dict[str, object]]:
    if not response.is_success:
        raise _to_postgrest_error(response)
    try:
        body: object = response.json()
    except ValueError as ex:
        raise UnexpectedResponseError(f"Response body is not JSON: {response.text[:200]!r}") from ex
    if not isinstance(body, list) or not all(isinstance(row, dict) for row in body):
        raise UnexpectedResponseError(f"Expected a JSON array of objects, got {type(body).__name__}")
    return body


def _parse_total(content_range: str | None) -> int | None:
    if content_range is None:
        return None
    match = _CONTENT_RANGE.match(content_range)
    if match is None or match.group(1) == "*":
        return None
    return int(match.group(1))


def _to_postgrest_error(response: httpx.Response) -> PostgrestError:
    try:
        body: object = response.json()
    except ValueError:
        body = None
    if not isinstance(body, Mapping):
        return PostgrestError(response.status_code, response.text or response.reason_phrase)
    return PostgrestError(
        response.status_code,
        _str_field(body, "message") or response.reason_phrase,
        code=_str_field(body, "code"),
        details=_str_field(body, "details"),
        hint=_str_field(body, "hint"),
    )


def _str_field(body: Mapping[object, object], key: str) -> str | None:
    value = body.get(key)
    return value if isinstance(value, str) else None
