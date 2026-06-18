import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from pathlib import Path

# Add src to sys.path
root_dir = str(Path(__file__).parent.parent)
if root_dir not in sys.path:
    sys.path.append(root_dir)

from src.telegram_alert import send_alert

class TestTelegramBot(unittest.TestCase):
    @patch('src.telegram_alert.requests.post')
    @patch('src.telegram_alert.TELEGRAM_BOT_TOKEN', 'mock_token')
    @patch('src.telegram_alert.TELEGRAM_CHAT_ID', 'mock_chat_id')
    def test_send_alert_success(self, mock_post):
        # Setup mock response
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test data
        top_insight = {
            "title": "Mock Breakthrough in AI",
            "final_score": 9.5
        }
        
        # Call the function
        send_alert(top_insight)
        
        # Verify requests.post was called with correct arguments
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs['json']['chat_id'], 'mock_chat_id')
        self.assertIn("Mock Breakthrough in AI", kwargs['json']['text'])
        print("\nTelegram alert logic verified: Payload is correct.")

if __name__ == '__main__':
    unittest.main()
