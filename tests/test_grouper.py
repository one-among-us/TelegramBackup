import unittest
from tgc.pyro.grouper import group_msgs


class TestGrouper(unittest.TestCase):
    def test_single_message(self):
        msgs = [{"id": 1, "text": "Hello"}]
        res = group_msgs(msgs)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], 1)
        self.assertEqual(res[0]["text"], "Hello")

    def test_media_group(self):
        msgs = [
            {"id": 2, "media_group_id": 100, "image": {"url": "media/2.jpg", "thumb": "media/2_thumb.jpg"}},
            {"id": 3, "media_group_id": 100, "text": "Photo caption", "image": {"url": "media/3.jpg", "thumb": "media/3_thumb.jpg"}}
        ]
        res = group_msgs(msgs)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["id"], 3)  # Dominant message with text
        self.assertEqual(res[0]["text"], "Photo caption")
        self.assertEqual(len(res[0]["images"]), 2)

    def test_reply_within_batch(self):
        msgs = [
            {"id": 10, "text": "Original message", "image": {"thumb": "media/10_thumb.jpg"}},
            {"id": 11, "text": "Reply message", "reply_id": 10}
        ]
        res = group_msgs(msgs)
        self.assertEqual(len(res), 2)
        self.assertIn("reply", res[1])
        self.assertEqual(res[1]["reply"]["id"], 10)
        self.assertEqual(res[1]["reply"]["text"], "Original message")
        self.assertEqual(res[1]["reply"]["thumb"], "media/10_thumb.jpg")

    def test_reply_to_external_post(self):
        lookup = [
            {
                "id": 5,
                "text": "Old message",
                "images": [{"url": "media/5.jpg", "thumb": "media/5_thumb.jpg"}]
            }
        ]
        msgs = [
            {"id": 20, "text": "Reply to old message", "reply_id": 5}
        ]
        res = group_msgs(msgs, lookup_posts=lookup)
        self.assertEqual(len(res), 1)
        self.assertIn("reply", res[0])
        self.assertEqual(res[0]["reply"]["id"], 5)
        self.assertEqual(res[0]["reply"]["text"], "Old message")
        self.assertEqual(res[0]["reply"]["thumb"], "media/5_thumb.jpg")

    def test_reply_to_external_media_group_item(self):
        lookup = [
            {
                "id": 5,
                "text": "Album post",
                "images": [
                    {"url": "media/5.jpg", "thumb": "media/5_thumb.jpg"},
                    {"url": "media/6.jpg", "thumb": "media/6_thumb.jpg"}
                ]
            }
        ]
        # Message replies to ID 6 (the second image in the album)
        msgs = [
            {"id": 20, "text": "Reply to image 6", "reply_id": 6}
        ]
        res = group_msgs(msgs, lookup_posts=lookup)
        self.assertEqual(len(res), 1)
        self.assertIn("reply", res[0])
        self.assertEqual(res[0]["reply"]["id"], 5)  # Resolves to parent album post
        self.assertEqual(res[0]["reply"]["text"], "Album post")

    def test_reply_to_unknown_message(self):
        msgs = [
            {"id": 30, "text": "Reply to missing message", "reply_id": 999}
        ]
        # Should not throw KeyError!
        res = group_msgs(msgs)
        self.assertEqual(len(res), 1)
        self.assertIn("reply", res[0])
        self.assertEqual(res[0]["reply"]["id"], 999)


if __name__ == "__main__":
    unittest.main()
