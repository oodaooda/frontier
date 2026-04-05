"""Tests for table extraction evaluation — comparison and parsing."""

import json
import pytest

from frontier.table_evaluation import (
    compare_tables,
    normalize_value,
    parse_model_json,
    build_extraction_prompt,
)


class TestNormalizeValue:
    def test_basic(self):
        assert normalize_value("H.M.") == "h.m."

    def test_whitespace(self):
        assert normalize_value("  PAINT, TBD  ") == "paint, tbd"

    def test_none(self):
        assert normalize_value(None) == ""

    def test_smart_quotes(self):
        assert normalize_value("3\u2019-0\u201d") == "3'-0\""

    def test_collapse_spaces(self):
        assert normalize_value("STILE  &  RAIL") == "stile & rail"


class TestParseModelJson:
    def test_plain_json(self):
        result = parse_model_json('[{"a": "1"}, {"a": "2"}]')
        assert len(result) == 2
        assert result[0]["a"] == "1"

    def test_markdown_fenced(self):
        result = parse_model_json('```json\n[{"a": "1"}]\n```')
        assert len(result) == 1

    def test_with_preamble(self):
        result = parse_model_json('Here is the data:\n[{"a": "1"}]\nThat is all.')
        assert len(result) == 1

    def test_no_json_raises(self):
        with pytest.raises(ValueError):
            parse_model_json("No JSON here at all")

    def test_invalid_json_raises(self):
        with pytest.raises((ValueError, json.JSONDecodeError)):
            parse_model_json("[{broken json}]")


class TestCompareTables:
    def test_perfect_match(self):
        expected = [
            {"door_no": "X-01", "material": "H.M.", "qty": "1"},
            {"door_no": "X-02", "material": "WOOD", "qty": "1"},
        ]
        model = [
            {"door_no": "X-01", "material": "H.M.", "qty": "1"},
            {"door_no": "X-02", "material": "WOOD", "qty": "1"},
        ]
        result = compare_tables(expected, model, ["door_no", "material", "qty"])
        assert result.accuracy == 100.0
        assert result.matched_cells == 6
        assert result.total_cells == 6

    def test_partial_match(self):
        expected = [
            {"door_no": "X-01", "material": "H.M."},
        ]
        model = [
            {"door_no": "X-01", "material": "WOOD"},  # material wrong
        ]
        result = compare_tables(expected, model, ["door_no", "material"])
        assert result.matched_cells == 1  # door_no matches
        assert result.total_cells == 2
        assert result.accuracy == 50.0

    def test_case_insensitive(self):
        expected = [{"material": "H.M."}]
        model = [{"material": "h.m."}]
        result = compare_tables(expected, model, ["material"])
        assert result.accuracy == 100.0

    def test_missing_rows(self):
        expected = [
            {"door_no": "X-01"},
            {"door_no": "X-02"},
        ]
        model = [
            {"door_no": "X-01"},
            # X-02 missing
        ]
        result = compare_tables(expected, model, ["door_no"])
        assert result.model_row_count == 1
        assert result.expected_row_count == 2
        assert result.matched_cells == 1
        assert result.total_cells == 2

    def test_extra_rows(self):
        expected = [{"door_no": "X-01"}]
        model = [
            {"door_no": "X-01"},
            {"door_no": "X-02"},
        ]
        result = compare_tables(expected, model, ["door_no"])
        assert result.model_row_count == 2
        assert result.expected_row_count == 1
        assert result.matched_cells == 1
        assert result.total_cells == 2

    def test_column_accuracy(self):
        expected = [
            {"a": "1", "b": "x"},
            {"a": "2", "b": "y"},
        ]
        model = [
            {"a": "1", "b": "x"},  # both correct
            {"a": "2", "b": "WRONG"},  # a correct, b wrong
        ]
        result = compare_tables(expected, model, ["a", "b"])
        assert result.column_accuracy["a"]["pct"] == 100
        assert result.column_accuracy["b"]["pct"] == 50

    def test_row_accuracy(self):
        expected = [
            {"a": "1", "b": "2"},
            {"a": "3", "b": "4"},
        ]
        model = [
            {"a": "1", "b": "2"},  # 100%
            {"a": "WRONG", "b": "WRONG"},  # 0%
        ]
        result = compare_tables(expected, model, ["a", "b"])
        assert result.row_accuracy[0]["pct"] == 100
        assert result.row_accuracy[1]["pct"] == 0


class TestBuildPrompt:
    def test_includes_columns(self):
        prompt = build_extraction_prompt(["door_no", "material"], "Door Schedule")
        assert "door_no" in prompt
        assert "material" in prompt
        assert "Door Schedule" in prompt

    def test_includes_instructions(self):
        prompt = build_extraction_prompt(["a", "b"])
        assert "EVERY row" in prompt
        assert "JSON array" in prompt
