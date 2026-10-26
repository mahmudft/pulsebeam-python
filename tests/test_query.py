import pytest

from tests.conftest import todos


def test_select_defaults_to_all_columns() -> None:
    assert todos.select().to_params() == [("select", "*")]


@pytest.mark.parametrize(
    ("method", "value", "expected"),
    [
        ("eq", 1, "eq.1"),
        ("neq", "a", "neq.a"),
        ("gt", 1.5, "gt.1.5"),
        ("gte", "2026-01-01", "gte.2026-01-01"),
        ("lt", 10, "lt.10"),
        ("lte", 10, "lte.10"),
        ("like", "*query*", "like.*query*"),
        ("ilike", "*Query*", "ilike.*Query*"),
    ],
)
def test_comparison_filters_encode_operator_and_value(method: str, value: object, expected: str) -> None:
    query = getattr(todos.select(), method)("title", value)

    assert query.to_params() == [("select", "*"), ("title", expected)]


def test_booleans_encode_in_lowercase() -> None:
    assert todos.select().eq("done", True).to_params()[1] == ("done", "eq.true")


@pytest.mark.parametrize(("value", "expected"), [(None, "is.null"), (True, "is.true"), (False, "is.false")])
def test_is_filter_encodes_null_and_booleans(value: bool | None, expected: str) -> None:
    assert todos.select().is_("done", value).to_params()[1] == ("done", expected)


def test_in_filter_quotes_items_with_reserved_characters() -> None:
    query = todos.select().in_("title", ["plain", "a,b", "(x)", 'say "hi"', "back\\slash", "two words", ""])

    assert query.to_params()[1] == (
        "title",
        'in.(plain,"a,b","(x)","say \\"hi\\"","back\\\\slash","two words","")',
    )


def test_in_filter_rejects_a_bare_string() -> None:
    with pytest.raises(TypeError):
        todos.select().in_("title", "abc")


def test_filters_on_the_same_column_are_all_kept() -> None:
    query = todos.select().gte("id", 1).lt("id", 10)

    assert query.to_params() == [("select", "*"), ("id", "gte.1"), ("id", "lt.10")]


def test_order_terms_are_combined_in_call_order() -> None:
    query = todos.select().order("done").order("id", descending=True, nulls_first=False)

    assert ("order", "done.asc,id.desc.nullslast") in query.to_params()


def test_limit_and_offset_become_params() -> None:
    query = todos.select().limit(20).offset(40)

    assert query.to_params() == [("select", "*"), ("limit", "20"), ("offset", "40")]


@pytest.mark.parametrize("method", ["limit", "offset"])
def test_negative_limit_or_offset_is_rejected(method: str) -> None:
    with pytest.raises(ValueError):
        getattr(todos.select(), method)(-1)


def test_builder_methods_return_new_queries() -> None:
    base = todos.select()
    filtered = base.eq("done", False)

    assert base.to_params() == [("select", "*")]
    assert filtered is not base
