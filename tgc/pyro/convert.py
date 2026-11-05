from hypy_utils.dict_utils import deep_dict
from pyrogram.enums import MessageEntityType
from pyrogram.parser import utils
from pyrogram.types import MessageEntity, Message

from tgc.pyro.consts import MEDIA_TYPE_MAP


def convert_media_dict(msg: Message) -> dict:
    def helper():
        for f in ['photo', 'live_photo', 'video', 'audio', 'voice', 'document', 'sticker', 'animation', 'video_note',
                  'contact', 'location', 'venue', 'poll', 'web_page',
                  'dice', 'game', 'story', 'giveaway', 'giveaway_winners', 'invoice', 'paid_media', 'checklist']:
            dct = getattr(msg, f, None)
            if dct:
                return dict(vars(dct))
        return {}

    d = deep_dict(helper(), {'_client', 'raw'})
    if d:
        d['media_type'] = MEDIA_TYPE_MAP.get(getattr(msg, 'media', None))
        if getattr(msg, 'has_media_spoiler', False):
            d['spoiler'] = True

    # Move location to one place
    if getattr(msg, 'venue', None):
        d.pop('location', None)
        if msg.venue.location:
            d['longitude'] = msg.venue.location.longitude
            d['latitude'] = msg.venue.location.latitude

    return d


def entity_start_end(text: str, en: MessageEntity) -> tuple[str, str] | None:
    """
    Convert a message entity to a start tag and an end tag for HTML
    """
    text = text[en.offset:en.offset + en.length]
    match en.type:
        case MessageEntityType.STRIKETHROUGH:
            return "<del>", "</del>"
        case MessageEntityType.CODE:
            return "<code>", "</code>"
        case MessageEntityType.ITALIC:
            return "<em>", "</em>"
        case MessageEntityType.UNDERLINE:
            return "<u>", "</u>"
        case MessageEntityType.BOLD:
            return "<b>", "</b>"
        case MessageEntityType.BLOCKQUOTE:
            if getattr(en, "expandable", False):
                return '<blockquote expandable class="expandable">', '</blockquote>'
            return "<blockquote>", "</blockquote>"
        case MessageEntityType.SPOILER:
            return '<span class="spoiler"><span>', '</span></span>'
        case MessageEntityType.TEXT_LINK:
            return f'<a href="{en.url}">', '</a>'
        case MessageEntityType.URL:
            return f'<a href="{text}">', '</a>'
        case MessageEntityType.HASHTAG:
            return f'<a href="#{text}">', '</a>'
        case MessageEntityType.CASHTAG:
            return f'<a href="https://t.me/share/url?url={text}">', '</a>'
        case MessageEntityType.MENTION:
            return f'<a href="https://t.me/{text.strip("@")}">', '</a>'
        case MessageEntityType.CUSTOM_EMOJI:
            # This will be replaced later
            return f'<i class="custom-emoji" emoji-src="emoji/{en.custom_emoji_id}">', '</i>'
        case MessageEntityType.BOT_COMMAND:
            return "<code>", "</code>"
        case MessageEntityType.EMAIL:
            return f'<a href="mailto:{text}">', '</a>'
        case MessageEntityType.PHONE_NUMBER:
            return f'<a href="tel:{text}">', '</a>'
        case MessageEntityType.BANK_CARD:
            return "<code>", "</code>"
        case MessageEntityType.PRE:
            lang = en.language
            return f'<pre language="{lang}">' if lang else f"<pre>", f"</pre>"
        case _:
            # Check expandable blockquote if supported by runtime
            if getattr(MessageEntityType, 'EXPANDABLE_BLOCKQUOTE', None) and en.type == MessageEntityType.EXPANDABLE_BLOCKQUOTE:
                return '<blockquote expandable class="expandable">', '</blockquote>'
            return None


def convert_text(text: str, entities: list[MessageEntity] | None) -> str:
    """
    Convert text to HTML
    """
    if not text:
        return ""
    if not entities:
        return text

    text = utils.add_surrogates(text)

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

    return utils.remove_surrogates(text)
