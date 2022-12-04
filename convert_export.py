import argparse
import json
from pathlib import Path

test_text = [
    "test ",
    {"type": "strikethrough", "text": "strikethrough"},
    {"type": "code", "text": "mono"},
    {"type": "italic", "text": "italic"},
    {"type": "underline", "text": "underline"},
    {"type": "bold", "text": "bold"},
    {"type": "spoiler", "text": "spoiler"}
]


def convert_text(text: str | list[dict | str] | None) -> str | None:
    """
    Convert text to markdown/html

    >>> convert_text(test_text)
    'test ~~strikethrough~~ `mono` __italic__ underline **bold** ||spoiler||'

    :param text: Telegram text
    :return: Markdown text
    """
    if text is None:
        return None

    if isinstance(text, str):
        return text

    def convert_entity(e: dict | str) -> str:
        if isinstance(e, str):
            return e
        if isinstance(e, dict):
            t = e["text"]
            match e["type"]:
                case "strikethrough":
                    return f"<strike>{t}</strike>"
                case "code":
                    return f"<code>{t}</code>"
                case "italic":
                    return f"<em>{t}</em>"
                case "underline":
                    return f"<u>{text}</u>"
                case "bold":
                    return f"<b>{t}</b>"
                case "spoiler":
                    return f'<span class="spoiler"><span>{t}</span></span>'
                # case "link":
                #     return f'<a href="{t}">{t}</a>'
                # case "mention_name":
                #     id = e['user_id']
                #     return f'<a href="https://t.me/{id}">{t}</a>'
                case "hashtag":
                    return f'<a href="{t}">{t}</a>'
                case "mention":
                    url = f'https://t.me/{t.strip("@")}'
                    return f'<a href="{url}">{t}</a>'
                case _:
                    return t

    text = [[e, convert_entity(e)] for e in text]

    return "".join([t[1] for t in text])


def convert_msg(d: dict) -> dict:
    """
    Convert a message object

    :param d: Message object dict from telegram export
    :return: Message object for tg-blog model
    """
    msg = {
        "id": d["id"],
        "date": d["date"],
        "type": None if d.get("type") == "message" else d.get("type"),
        "text": convert_text(d.get("text")),
        "views": d.get("views"),  # Views cannot be exported in the current version
        "images": None if d.get("photo") is None else [
            {"url": d.get("photo"), "width": d.get("width"), "height": d.get("height")}
        ],
        # TODO: Add this in front end
        "forwarded_From": None if d.get("forwarded_from") is None else [
            f'<b>forwarded from: {d.get("forwarded_from")}</b>'],

        # TODO: Add this in front end
        "video": None if d.get("media_type") != "video_file" else {
            "thumb": d.get("thumbnail"), "duration": d.get("duration_seconds"), "src": d.get("file")
        },
        # TODO: Add this in front end
        "reply": None if d.get("reply_to_message_id") is None else {
            "id": d.get("reply_to_message_id"),
            "text": get_topic_content(d["reply_to_message_id"],"text"),
            "thumb": get_topic_content(d["reply_to_message_id"],"thumbnail"),
        }
        # TODO: Add more fields
    }

    return {k: v for k, v in msg.items() if v is not None}


def get_topic_content(id: int, type: str) -> str | None:
    for i in j:
        if i["id"] == id:
            match (type):
                case "thumbnail":
                    return None if i.get("thumbnail") is None else i.get("thumbnail")
                case "text":
                    return convert_text(i.get("text"))


if __name__ == '__main__':
    parser = argparse.ArgumentParser("Telegram export converter",
                                     description="A tool to convert exported json into tg-blog json")
    parser.add_argument("dir", help="Export directory")
    args = parser.parse_args()

    p = Path(args.dir)
    f = p / "result.json"
    assert f.is_file(), f"Error: File {f} not found"

    # Read export result json
    j: list[dict] = json.loads(f.read_text())["messages"]

    # Convert
    j = [convert_msg(d) for d in j]

    (p / "posts.json").write_text(json.dumps(j, indent=2, ensure_ascii=False))
