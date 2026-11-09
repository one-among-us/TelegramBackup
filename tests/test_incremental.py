import unittest
from tgc.pyro.crawl import get_post_ids


class TestIncremental(unittest.TestCase):
    def test_get_post_ids_simple(self):
        p = {"id": 10}
        self.assertEqual(get_post_ids(p), {10})

    def test_get_post_ids_with_media(self):
        p = {
            "id": 10,
            "images": [
                {"url": "media/10.jpg"},
                {"url": "media/11.jpg"}
            ],
            "files": [
                {"url": "media/12.mp4"}
            ]
        }
        self.assertEqual(get_post_ids(p), {10, 11, 12})

    def test_cutoff_logic_no_media_group(self):
        existing_posts = [{"id": i} for i in range(1, 101)]
        overlap_count = 20
        idx = max(0, len(existing_posts) - overlap_count)
        self.assertEqual(idx, 80)
        preserved = existing_posts[:idx]
        target = existing_posts[idx:]
        self.assertEqual(len(preserved), 80)
        self.assertEqual(len(target), 20)
        self.assertEqual(target[0]["id"], 81)

    def test_cutoff_logic_with_media_group_boundary(self):
        # Suppose post 80 and 81 belong to the same media group
        existing_posts = [{"id": i, "media_group_id": 999 if i in (80, 81) else None} for i in range(1, 101)]
        overlap_count = 20  # idx would start at 80 (where post 80 is at index 79, post 81 is at index 80)
        idx = max(0, len(existing_posts) - overlap_count)
        self.assertEqual(idx, 80)
        # existing_posts[80] has id 81 (media_group_id=999)
        # existing_posts[79] has id 80 (media_group_id=999)
        while idx > 0 and existing_posts[idx].get('media_group_id') and existing_posts[idx]['media_group_id'] == existing_posts[idx - 1].get('media_group_id'):
            idx -= 1
        # idx should be pushed back to 79 to include post 80
        self.assertEqual(idx, 79)
        preserved = existing_posts[:idx]
        target = existing_posts[idx:]
        self.assertEqual(len(preserved), 79)
        self.assertEqual(target[0]["id"], 80)

    def test_merge_posts(self):
        preserved = [{"id": 1, "text": "Old"}, {"id": 2, "text": "Old 2"}]
        new_posts = [{"id": 2, "text": "Updated 2"}, {"id": 3, "text": "New 3"}]
        new_post_ids = {p['id'] for p in new_posts}
        final = [p for p in preserved if p['id'] not in new_post_ids] + new_posts
        final.sort(key=lambda x: x['id'])
        self.assertEqual(len(final), 3)
        self.assertEqual(final[1]["text"], "Updated 2")
        self.assertEqual(final[2]["text"], "New 3")

    def test_run_async_context(self):
        from unittest.mock import patch, MagicMock, AsyncMock
        from tgc.pyro import crawl
        from tgc.pyro.config import Config

        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        # Ensure client has no .loop attribute (as in kurigram 2.2.27)
        if hasattr(mock_client, 'loop'):
            del mock_client.loop

        dummy_cfg = Config(api_id=123, api_hash="abc", bot_token="token", exports=[])

        with patch("tgc.pyro.crawl.load_config", return_value=dummy_cfg), \
             patch("tgc.pyro.crawl.Client", return_value=mock_client), \
             patch("tgc.pyro.crawl.run_app", new_callable=AsyncMock) as mock_run_app, \
             patch("sys.argv", ["tgc", "--full"]):
            crawl.run()

            mock_client.__aenter__.assert_awaited_once()
            mock_run_app.assert_awaited_once_with(full=True, overlap=None)
            mock_client.__aexit__.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
