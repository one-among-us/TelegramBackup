import tempfile
import unittest
from pathlib import Path
from PIL import Image
from tgc.image_opt import create_webp_thumbnail, optimize_post_images


class TestImageOpt(unittest.TestCase):
    def test_create_webp_thumbnail(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            orig_path = tmp_path / "test.jpg"

            # Create test image 2000x1000
            img = Image.new("RGB", (2000, 1000), color="blue")
            img.save(orig_path, "JPEG")

            thumb_path = create_webp_thumbnail(orig_path, max_size=(1000, 1000), quality=80)
            self.assertIsNotNone(thumb_path)
            self.assertTrue(thumb_path.exists())
            self.assertEqual(thumb_path.name, "test_thumb.webp")

            # Check thumbnail dimensions preserved aspect ratio (2:1 => 1000x500)
            with Image.open(thumb_path) as thumb:
                self.assertEqual(thumb.format, "WEBP")
                self.assertEqual(thumb.size, (1000, 500))

            # Calling again returns cached file immediately
            thumb_path_cached = create_webp_thumbnail(orig_path, max_size=(1000, 1000), quality=80)
            self.assertEqual(thumb_path, thumb_path_cached)

    def test_optimize_post_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            media_dir = tmp_path / "media"
            media_dir.mkdir()

            # Create test images
            img1 = Image.new("RGB", (500, 500), color="red")
            img1.save(media_dir / "1.jpg", "JPEG")
            img2 = Image.new("RGB", (800, 600), color="green")
            img2.save(media_dir / "2.png", "PNG")

            posts = [
                {
                    "id": 1,
                    "images": [
                        {"url": "media/1.jpg"},
                        {"url": "media/2.png"}
                    ]
                },
                {
                    "id": 2,
                    "reply": {
                        "id": 1,
                        "thumb": "media/1.jpg"
                    }
                }
            ]

            optimize_post_images(posts, tmp_path)

            self.assertEqual(posts[0]["images"][0]["thumb"], "media/1_thumb.webp")
            self.assertEqual(posts[0]["images"][1]["thumb"], "media/2_thumb.webp")
            self.assertEqual(posts[1]["reply"]["thumb"], "media/1_thumb.webp")
            self.assertTrue((media_dir / "1_thumb.webp").exists())
            self.assertTrue((media_dir / "2_thumb.webp").exists())


if __name__ == "__main__":
    unittest.main()
