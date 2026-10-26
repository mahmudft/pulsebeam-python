from types import TracebackType
from typing import overload

import httpx

from pulsebeam._query import InsertQuery, SelectQuery
from pulsebeam._types import RowT
from pulsebeam._wire import (
    Page,
    RequestSpec,
    build_insert,
    build_select,
    default_headers,
    parse_inserted,
    parse_page,
)
from pulsebeam.errors import PulsebeamConnectionError


class AsyncPulsebeamClient:
    def __init__(self, base_url: str, *, token: str | None = None, timeout: float = 10.0) -> None:
        self._http = httpx.AsyncClient(base_url=base_url, headers=default_headers(token), timeout=timeout)

    @overload
    async def execute(self, query: SelectQuery[RowT]) -> Page[RowT]: ...

    @overload
    async def execute(self, query: InsertQuery[RowT]) -> list[RowT]: ...

    async def execute(self, query: SelectQuery[RowT] | InsertQuery[RowT]) -> Page[RowT] | list[RowT]:
        if isinstance(query, SelectQuery):
            return parse_page(query, await self._send(build_select(query)))
        if not query.rows:
            return []
        return parse_inserted(query, await self._send(build_insert(query)))

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "AsyncPulsebeamClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def _send(self, spec: RequestSpec) -> httpx.Response:
        try:
            return await self._http.request(
                spec.method, spec.path, params=spec.params, headers=spec.headers, json=spec.body
            )
        except httpx.TransportError as ex:
            raise PulsebeamConnectionError(str(ex)) from ex
