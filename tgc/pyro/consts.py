from pathlib import Path

from pyrogram.enums import MessageMediaType

MEDIA_TYPE_MAP: dict[MessageMediaType, str] = {
    MessageMediaType.PHOTO: "photo",
    MessageMediaType.STICKER: "sticker",
    MessageMediaType.VOICE: "voice_message",
    MessageMediaType.AUDIO: "audio_file",
    MessageMediaType.ANIMATION: "animation",
    MessageMediaType.VIDEO: "video_file",
    MessageMediaType.VIDEO_NOTE: "video_file",
    MessageMediaType.DOCUMENT: None,

    # TODO: Support these in web ui
    MessageMediaType.CONTACT: "contact",
    MessageMediaType.POLL: "poll",
    MessageMediaType.WEB_PAGE: "web_page",
    MessageMediaType.LOCATION: "location",
    MessageMediaType.VENUE: "location"
}

HTML = (Path(__file__).parent.parent / "tg-blog.html").read_text()
