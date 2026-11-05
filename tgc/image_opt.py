from pathlib import Path
from PIL import Image, ImageOps


def create_webp_thumbnail(image_path: Path, max_size: tuple[int, int] = (1000, 1000), quality: int = 80) -> Path | None:
    """
    Generate an optimized WebP thumbnail for an image.
    Preserves aspect ratio, fixes EXIF orientation, and saves as .thumb.webp.
    If the thumbnail already exists, returns the existing path immediately.

    :param image_path: Path to the original image file
    :param max_size: Maximum (width, height) bounding box for the thumbnail
    :param quality: WebP compression quality (default: 80)
    :return: Path to the generated or existing WebP thumbnail, or None if failed
    """
    if not image_path.is_file():
        return None

    thumb_path = image_path.parent / f"{image_path.stem}_thumb.webp"
    if thumb_path.exists():
        return thumb_path

    try:
        with Image.open(image_path) as im:
            # Transpose according to EXIF orientation tag (e.g. mobile photos)
            im = ImageOps.exif_transpose(im)
            # Resize image within max_size preserving aspect ratio
            im.thumbnail(max_size, Image.Resampling.LANCZOS)
            # Ensure color mode is compatible with WebP
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "A" in im.mode or im.mode == "P" else "RGB")
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            im.save(thumb_path, "WEBP", quality=quality, method=6)
        return thumb_path
    except Exception as e:
        print(f"Warning: Failed to create WebP thumbnail for {image_path}: {e}")
        return None


def optimize_post_images(posts: list[dict], base_path: Path, max_size: tuple[int, int] = (1000, 1000), quality: int = 80):
    """
    Ensure all images (and media thumbnails) in a list of posts have optimized WebP thumbnails
    if their original source files exist on disk.

    :param posts: List of post dictionaries
    :param base_path: Root export directory containing media/
    :param max_size: Thumbnail maximum dimensions
    :param quality: WebP quality
    """
    for post in posts:
        # Optimize image posts / albums
        for img_obj in post.get("images") or []:
            if "url" in img_obj:
                img_file = base_path / img_obj["url"]
                if img_file.is_file():
                    current_thumb = img_obj.get("thumb")
                    # If thumb is missing or not a valid webp file, generate it
                    if not current_thumb or not current_thumb.endswith(".webp") or not (base_path / current_thumb).is_file():
                        thumb_file = create_webp_thumbnail(img_file, max_size=max_size, quality=quality)
                        if thumb_file:
                            img_obj["thumb"] = str(thumb_file.relative_to(base_path))

        # Check singular 'image' if present
        if post.get("image") and "url" in post["image"]:
            img_file = base_path / post["image"]["url"]
            if img_file.is_file():
                current_thumb = post["image"].get("thumb")
                if not current_thumb or not current_thumb.endswith(".webp") or not (base_path / current_thumb).is_file():
                    thumb_file = create_webp_thumbnail(img_file, max_size=max_size, quality=quality)
                    if thumb_file:
                        post["image"]["thumb"] = str(thumb_file.relative_to(base_path))

        # Also optimize video / file thumbnails if present
        for f_obj in post.get("files") or []:
            if f_obj.get("thumb"):
                thumb_file = base_path / f_obj["thumb"]
                if thumb_file.is_file() and not str(thumb_file).endswith(".webp"):
                    webp_thumb = create_webp_thumbnail(thumb_file, max_size=max_size, quality=quality)
                    if webp_thumb:
                        f_obj["thumb"] = str(webp_thumb.relative_to(base_path))

        if post.get("file") and post["file"].get("thumb"):
            thumb_file = base_path / post["file"]["thumb"]
            if thumb_file.is_file() and not str(thumb_file).endswith(".webp"):
                webp_thumb = create_webp_thumbnail(thumb_file, max_size=max_size, quality=quality)
                if webp_thumb:
                    post["file"]["thumb"] = str(webp_thumb.relative_to(base_path))

        # Optimize reply thumbnail if present
        if post.get("reply") and isinstance(post["reply"], dict) and post["reply"].get("thumb"):
            thumb_file = base_path / post["reply"]["thumb"]
            if thumb_file.is_file() and not str(thumb_file).endswith(".webp"):
                webp_thumb = create_webp_thumbnail(thumb_file, max_size=max_size, quality=quality)
                if webp_thumb:
                    post["reply"]["thumb"] = str(webp_thumb.relative_to(base_path))
