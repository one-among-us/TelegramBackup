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
                    # return f'<a href="{t}">{t}</a>'
                case "hashtag":
                    return f'<a href="{t}">{t}</a>'
                case "mention":
                    url = f'https://t.me/{t.strip("@")}'
                    return f'<a href="{url}">{t}</a>'
                case _:
                    return t

    text = [[e, convert_entity(e)] for e in text]

    # Add spaces in between markdown elements and regular text
    # for i, tup in enumerate(text):
    #     e, t = tup
    #     if isinstance(e, str):
    #         continue
    #
    #     if not t.startswith(" ") and i > 0 and not text[i - 1][1].endswith(" "):
    #         t = " " + t
    #     if not t.endswith(" ") and i < len(text) - 1 and not text[i + 1][1].startswith(" "):
    #         t = t + " "
    #     text[i][1] = t

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
        "text": convert_text(d.get("text"))
        # TODO: Add more fields
        # TODO: Convert photo message
    }

    return {k: v for k, v in msg.items() if v is not None}


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

