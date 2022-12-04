import argparse
import json
import os.path
import urllib.parse
import zlib
from pathlib import Path
from subprocess import check_output

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
                    return f"<u>{t}</u>"
                case "bold":
                    return f"<b>{t}</b>"
                case "spoiler":
                    return f'<span class="spoiler"><span>{t}</span></span>'
                # case "link":
                #     return f'<a href="{t}">{t}</a>'
                # case "mention_name":
                #     id = e['user_id']
                #     return f'<a href="https://t.me/{id}">{t}</a>'
                case "text_link":
                    url = e['href']
                    return f'<a href="{url}">{t}</a>'
                case "hashtag":
                    return f'<a href="{t}">{t}</a>'
                case "mention":
                    url = f'https://t.me/{t.strip("@")}'
                    return f'<a href="{url}">{t}</a>'
                case _:
                    return t

    text = [[e, convert_entity(e)] for e in text]

    return "".join([t[1] for t in text])


def plain_text(text: str | list[dict | str] | None) -> str | None:
    """
    Convert text, remove all formats

    :param text: Telegram export text object
    :return: Plain text
    """
    if text is None:
        return None

    if isinstance(text, str):
        return text

    acc = ""
    for t in text:
        if isinstance(t, str):
            acc += t
        if isinstance(t, dict):
            acc += t["text"]

    return acc


def remove_nones(d: dict) -> dict:
    """
    Recursively remove none values from a dict

    >>> remove_nones({'a': {'b': None, 'c': 1}, 'b': None, 'c': {'a': None}})
    {'a': {'c': 1}, 'c': {}}

    :param d: Dict
    :return: Dict without nones
    """
    if not isinstance(d, dict):
        return d
    return {k: remove_nones(v) if isinstance(v, dict) else [remove_nones(i) for i in v] if isinstance(v, list) else v
            for k, v in d.items() if v is not None}


def convert_msg(d: dict) -> dict:
    """
    Convert a message object

    :param d: Message object dict from telegram export
    :return: Message object for tg-blog model
    """
    reply_id = d.get("reply_to_message_id")
    reply = id_map.get(reply_id)

    def process_file_path(path: str | None) -> str | None:
        """
        Ensure file paths are url-safe
        """
        if path is None:
            return None

        # Convert tgs stickers to apng
        if path.endswith(".tgs"):
            # Decompress to json
            json = path + ".json"
            (p / json).write_bytes(zlib.decompress((p / path).read_bytes(), 15 + 32))

            # Convert json to apng
            out = path[:-len(".tgs")] + ".apng"
            check_output(['./node_modules/.bin/puppeteer-lottie', '-i', p / json, '-o', p / out])

            # Use apng instead
            path = out

        url = urllib.parse.quote(path)
        if url == path:
            return path

        # Move file
        if not os.path.islink(p / url):
            os.symlink(p / path, p / url)
        return url

    def parse_file() -> list[dict] | None:
        file = d.get("file")
        if file is None:
            return None
        return [{
            "url": process_file_path(file),
            "thumb": process_file_path(d.get("thumbnail")),
            "mime_type": d.get("mime_type"),
            "size": os.path.getsize(p / file),

            # Media
            "media_type": d.get("media_type"),

            # Video/audio/gif
            "duration": d.get("duration_seconds"),

            # Video/sticker/gif
            "width": d.get("width"),
            "height": d.get("height"),

            # Sticker
            "sticker_emoji": d.get("sticker_emoji"),

            # Audio
            "title": d.get("title"),
            "performer": d.get("performer")
        }]

    msg = {
        "id": d["id"],
        "date": d["date"],
        "type": None if d.get("type") == "message" else d.get("type"),
        "text": convert_text(d.get("text")),
        "views": d.get("views"),  # Views cannot be exported in the current version
        "images": None if d.get("photo") is None else [
            {"url": d.get("photo"), "width": d.get("width"), "height": d.get("height")}
        ],
        "forwarded_from": d.get("forwarded_from"),

        # TODO: Add this in front end
        "video": None if d.get("media_type") != "video_file" else {
            "thumb": d.get("thumbnail"), "duration": d.get("duration_seconds"), "src": d.get("file")
        },
        "reply": None if reply_id is None else {
            "id": reply_id,
            "text": plain_text(reply.get("text")),
            "thumb": reply.get("thumbnail") or reply.get("photo"),
        },
        "author": d.get("author"),
        "files": parse_file()
        # TODO: Add more fields
    }

    return remove_nones(msg)


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
    id_map = {d['id']: d for d in j}

    # Convert
    j = [convert_msg(d) for d in j]

    (p / "posts.json").write_text(json.dumps(j, indent=2, ensure_ascii=False))
