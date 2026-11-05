from pathlib import Path

from pyrogram.enums import MessageMediaType

MEDIA_TYPE_MAP: dict[MessageMediaType, str] = {
    MessageMediaType.PHOTO: "photo",
    getattr(MessageMediaType, "LIVE_PHOTO", "live_photo"): "live_photo",
    MessageMediaType.STICKER: "sticker",
    MessageMediaType.VOICE: "voice_message",
    MessageMediaType.AUDIO: "audio_file",
    MessageMediaType.ANIMATION: "animation",
    MessageMediaType.VIDEO: "video_file",
    MessageMediaType.VIDEO_NOTE: "video_file",
    MessageMediaType.DOCUMENT: None,

    MessageMediaType.CONTACT: "contact",
    MessageMediaType.POLL: "poll",
    MessageMediaType.WEB_PAGE: "web_page",
    MessageMediaType.LOCATION: "location",
    MessageMediaType.VENUE: "location",

    # Newer media types
    getattr(MessageMediaType, "DICE", "dice"): "dice",
    getattr(MessageMediaType, "GAME", "game"): "game",
    getattr(MessageMediaType, "GIVEAWAY", "giveaway"): "giveaway",
    getattr(MessageMediaType, "GIVEAWAY_WINNERS", "giveaway_winners"): "giveaway_winners",
    getattr(MessageMediaType, "STORY", "story"): "story",
    getattr(MessageMediaType, "INVOICE", "invoice"): "invoice",
    getattr(MessageMediaType, "PAID_MEDIA", "paid_media"): "paid_media",
    getattr(MessageMediaType, "CHECKLIST", "checklist"): "checklist",
}

HTML = (Path(__file__).parent.parent / "tg-blog.html").read_text()
