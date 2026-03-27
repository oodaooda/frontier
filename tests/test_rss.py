"""Tests for RSS feed parsing and keyword filtering."""

from frontier.rss import matches_keywords


class TestKeywordMatching:
    def test_matches_model_release(self):
        assert matches_keywords("Introducing Claude Opus 4.7") is True

    def test_matches_vision(self):
        assert matches_keywords("New vision capabilities for document understanding") is True

    def test_matches_api(self):
        assert matches_keywords("API updates and new features") is True

    def test_no_match(self):
        assert matches_keywords("Company earnings report for Q4") is False

    def test_case_insensitive(self):
        assert matches_keywords("NEW MODEL RELEASE") is True

    def test_matches_gpt(self):
        assert matches_keywords("GPT-5.5 now available") is True

    def test_matches_gemini(self):
        assert matches_keywords("Gemini 2.5 Pro with multimodal support") is True

    def test_matches_pdf(self):
        assert matches_keywords("Improved PDF processing capabilities") is True
