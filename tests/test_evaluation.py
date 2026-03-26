"""Tests for evaluation engine — scoring and response parsing."""

import pytest

from frontier.evaluation import _simple_score, parse_response


class TestParseResponse:
    def test_standard_format(self):
        raw = "Answer: 42\nConfidence: 4"
        parsed = parse_response(raw)
        assert parsed.answer == "42"
        assert parsed.confidence == 4

    def test_with_explanation(self):
        raw = "I can see the schedule has many rows.\n\nAnswer: 38\nConfidence: 2\n\nSome rows were unclear."
        parsed = parse_response(raw)
        assert parsed.answer == "38"
        assert parsed.confidence == 2

    def test_no_structured_format(self):
        raw = "The door schedule shows 42 doors total."
        parsed = parse_response(raw)
        assert "42 doors" in parsed.answer
        assert parsed.confidence is None

    def test_answer_only(self):
        raw = "Answer: DOOR SCHEDULE"
        parsed = parse_response(raw)
        assert parsed.answer == "DOOR SCHEDULE"
        assert parsed.confidence is None

    def test_case_insensitive(self):
        raw = "answer: The Wellington\nconfidence: 5"
        parsed = parse_response(raw)
        assert parsed.answer == "The Wellington"
        assert parsed.confidence == 5


class TestSimpleScore:
    def test_exact_match(self):
        assert _simple_score("42", "42", "exact", None) is True
        assert _simple_score("DOOR SCHEDULE", "DOOR SCHEDULE", "exact", None) is True

    def test_exact_case_insensitive(self):
        assert _simple_score("Door Schedule", "DOOR SCHEDULE", "exact", None) is True

    def test_exact_mismatch(self):
        assert _simple_score("38", "42", "exact", None) is False

    def test_contains(self):
        assert _simple_score("The Wellington Residences", "The Wellington", "contains", None) is True
        assert _simple_score("HM (Hollow Metal)", "HM", "contains", None) is True

    def test_contains_mismatch(self):
        assert _simple_score("WOOD", "HM", "contains", None) is False

    def test_numeric_tolerance_pass(self):
        assert _simple_score("14", "14", "numeric_tolerance", 1.0) is True
        assert _simple_score("13.5", "14", "numeric_tolerance", 1.0) is True

    def test_numeric_tolerance_fail(self):
        assert _simple_score("100", "200", "numeric_tolerance", 10.0) is False

    def test_numeric_tolerance_exact(self):
        assert _simple_score("12.5", "12.5", "numeric_tolerance", 0.01) is True

    def test_semantic_fallback(self):
        assert _simple_score("Structural steel erection", "Structural steel erection", "semantic", None) is True
        assert _simple_score("Steel erection", "Structural steel erection", "semantic", None) is True

    def test_whitespace_handling(self):
        assert _simple_score("  42  ", "42", "exact", None) is True
