"""Runs against a real PostgREST. Start one with ``docker compose up -d`` and set
``PULSEBEAM_TEST_URL=http://localhost:3000``; without it these tests are skipped."""

import os
import uuid

import pytest

from pulsebeam import AsyncPulsebeamClient, PostgrestError, PulsebeamClient
from tests.conftest import todos

URL = os.environ.get("PULSEBEAM_TEST_URL")

pytestmark = pytest.mark.skipif(URL is None, reason="PULSEBEAM_TEST_URL is not set")


def test_sync_client_round_trips_an_insert() -> None:
    assert URL is not None
    title = f"integration {uuid.uuid4()}"

    with PulsebeamClient(URL) as client:
        created = client.execute(todos.insert([{"title": title}]))
        page = client.execute(todos.select().eq("title", title).with_count())

    assert created[0]["done"] is False
    assert page.rows == created
    assert page.total == 1


async def test_async_client_filters_orders_and_counts() -> None:
    assert URL is not None

    async with AsyncPulsebeamClient(URL) as client:
        page = await client.execute(todos.select().is_("done", True).order("id", descending=True).with_count())

    assert page.rows
    assert all(row["done"] for row in page.rows)
    assert [row["id"] for row in page.rows] == sorted((row["id"] for row in page.rows), reverse=True)
    assert page.total is not None and page.total >= len(page.rows)


def test_unknown_column_surfaces_postgrest_error_code() -> None:
    assert URL is not None

    with PulsebeamClient(URL) as client, pytest.raises(PostgrestError) as caught:
        client.execute(todos.select().eq("titel", "x"))

    assert caught.value.code == "42703"
