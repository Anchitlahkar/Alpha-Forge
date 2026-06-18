import unittest
from src.relevance_ranker import rank_insights

class TestRanker(unittest.TestCase):
    def test_ranking_order(self):
        insights = [
            {"title": "A", "signal_score": 5, "personal_relevance": 5, "category": "Consumer Tech"},
            {"title": "B", "signal_score": 10, "personal_relevance": 10, "category": "AI Research"}
        ]
        ranked = rank_insights(insights)
        self.assertEqual(ranked[0]["title"], "B")
        self.assertEqual(ranked[1]["title"], "A")

if __name__ == '__main__':
    unittest.main()