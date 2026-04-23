from pathlib import Path

MEDIA_ATTR_MAP: dict[str, str | None] = {
    "photo": "photo",
    "sticker": "sticker",
    "voice": "voice_message",
    "audio": "audio_file",
    "gif": "animation",
    "video": "video_file",
    "video_note": "video_file",
    "document": None,
    "contact": "contact",
    "poll": "poll",
    "web_preview": "web_page",
    "geo": "location",
    "venue": "location",
}

HTML = (Path(__file__).parent.parent / "tg-blog.html").read_text()
