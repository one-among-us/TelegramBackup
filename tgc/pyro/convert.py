from pyrogram.enums import MessageEntityType, MessageMediaType
from pyrogram.parser import utils
from pyrogram.types import MessageEntity, Photo, Message


def convert_media_dict(msg: Message) -> dict:
    def helper():
        match msg.media:
            case MessageMediaType.PHOTO:
                return vars(msg.photo)
            case MessageMediaType.VIDEO:
                return vars(msg.video)
            case MessageMediaType.AUDIO:
                return vars(msg.audio)
            case MessageMediaType.VOICE:
                return vars(msg.voice)
            case MessageMediaType.DOCUMENT:
                return vars(msg.document)
            case MessageMediaType.STICKER:
                return vars(msg.sticker)
            case MessageMediaType.ANIMATION:
                return vars(msg.animation)
            case MessageMediaType.VIDEO_NOTE:
                return vars(msg.video_note)
            case MessageMediaType.CONTACT:
                return vars(msg.contact)
            case MessageMediaType.LOCATION:
                return vars(msg.location)
            case MessageMediaType.VENUE:
                return vars(msg.venue)
            case MessageMediaType.POLL:
                return vars(msg.poll)
            case MessageMediaType.WEB_PAGE:
                return vars(msg.web_page)
        return {}

    d = helper()
    d = {k: v for k, v in d.items() if k not in {'_client', 'file_id', 'file_unique_id'}}

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
            return "<blockquote>", "</blockquote>"
        case MessageEntityType.SPOILER:
            return '<span class="spoiler"><span>', '</span></span>'
        case MessageEntityType.TEXT_LINK:
            return f'<a href="{en.url}">', '</a>'
        case MessageEntityType.HASHTAG:
            return f'<a href="#{text}">', '</a>'
        case MessageEntityType.MENTION:
            return f'<a href="https://t.me/{text.strip("@")}">', '</a>'
        case MessageEntityType.CUSTOM_EMOJI:
            # TODO: Download emoji to the right place
            return f'<i class="custom-emoji" emoji-src="emoji/{en.custom_emoji_id}">', '</i>'
        case MessageEntityType.PRE:
            lang = en.language
            return f'<pre language="{lang}">' if lang else f"<pre>", f"</pre>"
        case _:
            return None


def convert_text(text: str, entities: list[MessageEntity]) -> str:
    """
    Convert text to HTML
    """
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
