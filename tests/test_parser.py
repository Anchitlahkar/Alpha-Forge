import unittest
from unittest.mock import patch
from src import article_parser
from src.utils import make_processed_key


class TestParser(unittest.TestCase):
    def _article(self):
        return {
            "title": "A Sufficiently Long Article Title",
            "link": "https://example.com/article",
            "source_name": "Example Source",
            "category": "AI",
            "summary": "x" * 250,  # long enough to skip the fetch_article_text fallback
            "published": "2026-01-01",
        }

    def _key(self, article):
        return make_processed_key(article["link"], article["title"])

    def test_successful_analysis_marks_url_processed(self):
        article = self._article()
        processed_urls = set()
        fake_insight = {
            "title": "Insight",
            "why_it_matters": "Because it does.",
            "signal_score": 8.0,
        }
        with patch.object(article_parser, "extract_insights", return_value=fake_insight):
            result = article_parser.parse_and_analyze(article, processed_urls)

        self.assertIsNotNone(result)
        self.assertIn(self._key(article), processed_urls)

    def test_failed_analysis_does_not_mark_url_processed(self):
        # extract_insights returning None (e.g. Gemini quota exhausted) must NOT
        # blacklist the URL, otherwise it can never be retried on a future run.
        article = self._article()
        processed_urls = set()
        with patch.object(article_parser, "extract_insights", return_value=None):
            result = article_parser.parse_and_analyze(article, processed_urls)

        self.assertIsNotNone(result)
        self.assertEqual(result.get("why_it_matters"), "Analysis unavailable.")
        self.assertNotIn(self._key(article), processed_urls)

    def test_too_short_article_marks_url_processed(self):
        article = self._article()
        article["summary"] = "too short"
        processed_urls = set()
        with patch.object(article_parser, "fetch_article_text", return_value=""):
            result = article_parser.parse_and_analyze(article, processed_urls)

        self.assertIsNone(result)
        self.assertIn(self._key(article), processed_urls)

    def test_same_url_with_a_different_paper_is_not_skipped(self):
        # A listing or index URL can carry a different paper later. Keying on
        # URL + title means the new one still gets through, while an exact
        # repeat of the same piece is still skipped.
        first = self._article()
        second = dict(first, title="An Entirely Different Paper Title")

        processed_urls = set()
        fake_insight = {"title": "Insight", "why_it_matters": "Because.", "signal_score": 8.0}
        with patch.object(article_parser, "extract_insights", return_value=fake_insight):
            article_parser.parse_and_analyze(first, processed_urls)

        self.assertIn(self._key(first), processed_urls)
        self.assertNotIn(self._key(second), processed_urls)

    def test_title_casing_and_spacing_still_counts_as_a_repeat(self):
        article = self._article()
        noisy = dict(article, title="  a SUFFICIENTLY   long Article TITLE ")
        self.assertEqual(self._key(article), self._key(noisy))


if __name__ == '__main__':
    unittest.main()
