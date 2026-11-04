import unittest
from pyrogram.types import Message, WebPage
import pyrogram.raw.types as r
from tgc.pyro.convert import convert_media_dict
from hypy_utils import json_stringify


class TestConvert(unittest.TestCase):
    def test_webpage_serialization(self):
        # Construct a WebPage with raw MessageMediaWebPage TL object
        raw_media = r.MessageMediaWebPage(webpage=r.WebPageEmpty(id=123))
        wp = WebPage(id="123", url="https://example.com", raw=raw_media)
        msg = Message(id=1, web_page=wp)

        d = convert_media_dict(msg)
        self.assertNotIn("raw", d)
        self.assertNotIn("_client", d)

        # Must be JSON serializable
        s = json_stringify(d)
        self.assertIn("https://example.com", s)


if __name__ == "__main__":
    unittest.main()
