from pyrogram.enums import MessageEntityType, MessageMediaType
from pyrogram.parser import utils
from pyrogram.raw.types import Message
from pyrogram.types import MessageEntity


# def convert_media(msg: Message) -> dict:
#     match msg.media:
#         case MessageMediaType.VIDEO:



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
