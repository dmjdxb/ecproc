"""Tests for ecproc.sdk.variables — template variable resolution."""

from __future__ import annotations

from ecproc.sdk.variables import has_variables, resolve_variables

# ---------------------------------------------------------------------------
# resolve_variables
# ---------------------------------------------------------------------------


class TestResolveVariables:
    """Tests for resolve_variables()."""

    def test_simple_name_replacement(self):
        result = resolve_variables("Hello {name}", {"name": "World"})
        assert result == "Hello World"

    def test_multiple_replacements(self):
        result = resolve_variables(
            "{greeting} {name}!",
            {"greeting": "Hello", "name": "World"},
        )
        assert result == "Hello World!"

    def test_nested_dot_path(self):
        result = resolve_variables(
            "Count is {loop.count}",
            {"loop": {"count": 10}},
        )
        assert result == "Count is 10"

    def test_loop_index(self):
        result = resolve_variables(
            "Index: {loop.index}",
            {"loop": {"index": 3}},
        )
        assert result == "Index: 3"

    def test_elapsed_hours(self):
        result = resolve_variables(
            "Elapsed: {elapsed.hours} h",
            {"elapsed": {"hours": 2.5}},
        )
        assert result == "Elapsed: 2.5 h"

    def test_timestamp(self):
        result = resolve_variables(
            "File: data_{timestamp}.csv",
            {"timestamp": "20240101_120000"},
        )
        assert result == "File: data_20240101_120000.csv"

    def test_no_variables_returns_unchanged(self):
        text = "No variables here"
        result = resolve_variables(text, {"name": "ignored"})
        assert result == text

    def test_missing_variable_left_as_placeholder(self):
        result = resolve_variables("Hello {missing}", {})
        assert result == "Hello {missing}"

    def test_partial_resolution(self):
        result = resolve_variables(
            "{found} and {notfound}",
            {"found": "yes"},
        )
        assert result == "yes and {notfound}"

    def test_numeric_value_converted_to_string(self):
        result = resolve_variables("{n}", {"n": 42})
        assert result == "42"

    def test_deeply_nested_path(self):
        result = resolve_variables(
            "{a.b.c}",
            {"a": {"b": {"c": "deep"}}},
        )
        assert result == "deep"

    def test_nested_path_missing_intermediate_key(self):
        result = resolve_variables(
            "{a.b.c}",
            {"a": {"x": "wrong"}},
        )
        assert result == "{a.b.c}"

    def test_non_dict_intermediate_value(self):
        result = resolve_variables(
            "{a.b}",
            {"a": "string_not_dict"},
        )
        assert result == "{a.b}"

    def test_empty_context(self):
        result = resolve_variables("{x}", {})
        assert result == "{x}"

    def test_empty_template(self):
        result = resolve_variables("", {"name": "test"})
        assert result == ""


# ---------------------------------------------------------------------------
# has_variables
# ---------------------------------------------------------------------------


class TestHasVariables:
    """Tests for has_variables()."""

    def test_returns_true_for_simple_variable(self):
        assert has_variables("{name}") is True

    def test_returns_true_for_nested_variable(self):
        assert has_variables("{loop.count}") is True

    def test_returns_false_for_no_variables(self):
        assert has_variables("no variables here") is False

    def test_returns_false_for_empty_string(self):
        assert has_variables("") is False

    def test_returns_true_with_surrounding_text(self):
        assert has_variables("file_{timestamp}.csv") is True

    def test_returns_false_for_empty_braces(self):
        # {} does not match \w+ pattern, so should be False
        assert has_variables("{}") is False

    def test_returns_true_for_multiple_variables(self):
        assert has_variables("{a} and {b}") is True
