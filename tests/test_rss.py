"""Tests for RSS feed parsing and keyword filtering."""

from frontier.rss import matches_keywords


class TestKeywordMatching:
    def test_matches_model_release(self):
        assert matches_keywords("Introducing Claude Opus 4.7") is True

    def test_matches_gpt_release(self):
        assert matches_keywords("Introducing GPT-5.4 for developers") is True

    def test_matches_gpt_available(self):
        assert matches_keywords("GPT-5.5 now available") is True

    def test_matches_gemini_multimodal(self):
        assert matches_keywords("Gemini 2.5 Pro with multimodal launch") is True

    def test_matches_model_vision(self):
        assert matches_keywords("Claude vision capabilities release") is True

    def test_matches_new_model(self):
        assert matches_keywords("New model release with vision support") is True

    def test_no_match_generic(self):
        assert matches_keywords("Company earnings report for Q4") is False

    def test_no_match_model_without_context(self):
        # Has model name but no release/launch context
        assert matches_keywords("How GPT-4 is used in education") is False

    def test_no_match_context_without_model(self):
        # Has context but no model name
        assert matches_keywords("Introducing a new safety policy") is False

    def test_excluded_chatgpt_for(self):
        assert matches_keywords("Introducing ChatGPT for Excel with GPT-4o") is False

    def test_excluded_enterprise(self):
        assert matches_keywords("Claude Enterprise partnership announced") is False

    def test_case_insensitive(self):
        assert matches_keywords("INTRODUCING GPT-5 FOR DEVELOPERS") is True
