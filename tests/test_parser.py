import unittest
from unittest.mock import patch
from src import article_parser


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

    def test_successful_analysis_marks_url_processed(self):
        processed_urls = set()
        fake_insight = {
            "title": "Insight",
            "why_it_matters": "Because it does.",
            "signal_score": 8.0,
        }
        with patch.object(article_parser, "extract_insights", return_value=fake_insight):
            result = article_parser.parse_and_analyze(self._article(), processed_urls)

        self.assertIsNotNone(result)
        self.assertIn("https://example.com/article", processed_urls)

    def test_failed_analysis_does_not_mark_url_processed(self):
        # extract_insights returning None (e.g. Gemini quota exhausted) must NOT
        # blacklist the URL, otherwise it can never be retried on a future run.
        processed_urls = set()
        with patch.object(article_parser, "extract_insights", return_value=None):
            result = article_parser.parse_and_analyze(self._article(), processed_urls)

        self.assertIsNotNone(result)
        self.assertEqual(result.get("why_it_matters"), "Analysis unavailable.")
        self.assertNotIn("https://example.com/article", processed_urls)

    def test_too_short_article_marks_url_processed(self):
        article = self._article()
        article["summary"] = "too short"
        processed_urls = set()
        with patch.object(article_parser, "fetch_article_text", return_value=""):
            result = article_parser.parse_and_analyze(article, processed_urls)

        self.assertIsNone(result)
        self.assertIn("https://example.com/article", processed_urls)


if __name__ == '__main__':
    unittest.main()
