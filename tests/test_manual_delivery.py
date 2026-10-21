import io
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from test_bridge import payload

from twintext.bridge import Inbox, capture, send_to_reader
from twintext.config import update_settings
from twintext.service import context


class ManualDeliveryTests(unittest.TestCase):
    def test_manual_buttons_disable_automatic_capture_and_model_forwarding(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, TWINTEXT_HOME=folder):
            update_settings(workflow="chat", chat_presentation="floating", message_buttons=True,
                            response_scope="all")
            with patch("twintext.bridge.launch_desktop") as launch:
                capture(io.StringIO(json.dumps(payload())))
                self.assertFalse(send_to_reader("Do not translate automatically")["received"])
                launch.assert_not_called()
            self.assertEqual(Inbox().history(), [])
            instructions = context()
            self.assertIn("manual", instructions)
            self.assertNotIn("Stop hook forwards", instructions)
            self.assertIn("Do not call", instructions)
