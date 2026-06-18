import unittest
from src.deduplicate import deduplicate_insights

class TestDedup(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(deduplicate_insights([]), [])
        
    def test_single_item(self):
        data = [{"title": "Test", "tldr": "Test TLDR"}]
        res = deduplicate_insights(data)
        self.assertEqual(len(res), 1)

if __name__ == '__main__':
    unittest.main()