from typing import Any

from hypy_utils.dict_utils import deep_dict
from telethon.helpers import add_surrogate, del_surrogate
from telethon.tl.custom.message import Message
from telethon.tl.types import (
    MessageEntityBold,
    MessageEntityBlockquote,
    MessageEntityCode,
    MessageEntityCustomEmoji,
    MessageEntityHashtag,
    MessageEntityItalic,
    MessageEntityMention,
    MessageEntityPre,
    MessageEntitySpoiler,
    MessageEntityStrike,
    MessageEntityTextUrl,
    MessageEntityUnderline,
    MessageEntityUrl,
)

from tgc.pyro.consts import MEDIA_ATTR_MAP


def convert_media_dict(msg: Message) -> dict:
    def helper():
        for f in ['photo', 'video', 'audio', 'voice', 'document', 'sticker', 'gif', 'video_note', 'contact',
                  'geo', 'venue', 'poll', 'web_preview']:
            dct = getattr(msg, f, None)
            if dct:
                d = dict(vars(dct))
                d['media_type'] = MEDIA_ATTR_MAP.get(f)
                return d
        return {}

    d = deep_dict(helper(), {'_client'})
    if d:
        if getattr(msg.media, "spoiler", False):
            d['spoiler'] = True
        f = getattr(msg, "file", None)
        if f:
            d['mime_type'] = d.get('mime_type') if d.get('mime_type') is not None else getattr(f, "mime_type", None)

            size = d.get('size')
            file_size = d.get('file_size')
            d['file_size'] = size if size is not None else file_size if file_size is not None else getattr(f, "size", None)

            w = d.get('w')
            width = d.get('width')
            d['width'] = w if w is not None else width if width is not None else getattr(f, "width", None)

            h = d.get('h')
            height = d.get('height')
            d['height'] = h if h is not None else height if height is not None else getattr(f, "height", None)

            d['duration'] = d.get('duration') if d.get('duration') is not None else getattr(f, "duration", None)
            d['thumbs'] = d.get('thumbs') if d.get('thumbs') is not None else getattr(f, "thumbs", None)

    # Move location to one place
    if msg.venue:
        d.pop('geo', None)
        if msg.venue.geo:
            d['longitude'] = msg.venue.geo.long
            d['latitude'] = msg.venue.geo.lat

    return d


def entity_start_end(text: str, en: Any) -> tuple[str, str] | None:
    """
    Convert a message entity to a start tag and an end tag for HTML
    """
    text = text[en.offset:en.offset + en.length]
    if isinstance(en, MessageEntityStrike):
        return "<del>", "</del>"
    if isinstance(en, MessageEntityCode):
        return "<code>", "</code>"
    if isinstance(en, MessageEntityItalic):
        return "<em>", "</em>"
    if isinstance(en, MessageEntityUnderline):
        return "<u>", "</u>"
    if isinstance(en, MessageEntityBold):
        return "<b>", "</b>"
    if isinstance(en, MessageEntityBlockquote):
        return "<blockquote>", "</blockquote>"
    if isinstance(en, MessageEntitySpoiler):
        return '<span class="spoiler"><span>', '</span></span>'
    if isinstance(en, MessageEntityTextUrl):
        return f'<a href="{en.url}">', '</a>'
    if isinstance(en, MessageEntityUrl):
        return f'<a href="{text}">', '</a>'
    if isinstance(en, MessageEntityHashtag):
        return f'<a href="#{text}">', '</a>'
    if isinstance(en, MessageEntityMention):
        return f'<a href="https://t.me/{text.strip("@")}">', '</a>'
    if isinstance(en, MessageEntityCustomEmoji):
        # This will be replaced later
        return f'<i class="custom-emoji" emoji-src="emoji/{en.document_id}">', '</i>'
    if isinstance(en, MessageEntityPre):
        lang = en.language
        return f'<pre language="{lang}">' if lang else f"<pre>", f"</pre>"
    return None


def convert_text(text: str, entities: list[Any]) -> str:
    """
    Convert text to HTML
    """
    text = add_surrogate(text)

    entities_offsets = []

    for entity in entities:
        start = entity.offset
        end = start + entity.length

        tags = entity_start_end(text, entity)
        if tags is None:
            continue

        entities_offsets.append((tags[0], start,))
        entities_offsets.append((tags[1], end,))

    entities_offsets = map(
        lambda x: x[1],
        sorted(
            enumerate(entities_offsets),
            key=lambda x: (x[1][1], x[0]),
            reverse=True
        )
    )

    for entity, offset in entities_offsets:
        text = text[:offset] + entity + text[offset:]

    return del_surrogate(text)
