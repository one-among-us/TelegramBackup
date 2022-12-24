import argparse
import json
import os.path
import shutil
from pathlib import Path
from subprocess import check_call, CalledProcessError

from hypy_utils import printc, write, json_stringify
from hypy_utils.dict_utils import remove_nones

from .convert_media_types import tgs_to_apng, extract_album_art
from .pyro.consts import HTML

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
                    return f"<del>{t}</del>"
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
                case "link":
                    return f'<a href="{t}">{t}</a>'
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
                case "custom_emoji":
                    url: str = e['document_id']
                    # if url.endswith(".webm"):
                    #     url = webm_to_apng(url)
                    return f'<i class="custom-emoji" emoji-src="{url}">{t}</i>'
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


def process_file_path(path: str | None) -> str | None:
    """
    Ensure file paths are url-safe
    """
    if path is None:
        return None

    # Convert tgs stickers to apng
    if path.endswith(".tgs"):
        path = str(tgs_to_apng(p / path).relative_to(p))

    return path


def parse_file(d: dict) -> dict | None:
    file = d.get("file")
    if file is None:
        return None

    # Create file
    file = {
        "url": process_file_path(file),
        "thumb": process_file_path(d.get("thumbnail")),
        "mime_type": d.get("mime_type"),
        "size": os.path.getsize(p / file),
        "original_name": d.get("original_name"),

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
    }

    # Convert image file to photo
    if not file['media_type'] and file['mime_type'].startswith('image'):
        file['media_type'] = "photo"

    # Add image for missing album cover art
    if file['media_type'] == 'audio_file' and not file['thumb']:
        fp = p / file['url']
        op = extract_album_art(fp)
        if op:
            file['thumb'] = op.relative_to(p)

    return file


def get_image(d: dict) -> dict:
    return {"url": d.get("photo"), "width": d.get("width"), "height": d.get("height")}


def convert_msg(d: dict) -> dict | None:
    """
    Convert a message object

    :param d: Message object dict from telegram export
    :return: Message object for tg-blog model
    """
    # Message group quirks
    grp = d.get("media_group_id")
    if grp in processed_groups:
        return None
    if grp is not None:
        processed_groups[grp] = d['id']

    def get_group_text():
        if grp is None:
            return convert_text(d.get("text"))
        for msg in groups[grp]:
            t = convert_text(msg.get("text"))
            if t:
                return t
        return None

    def get_group_images():
        if d.get("photo") is None:
            return None
        if grp is None:
            return [get_image(d)]
        return [get_image(m) for m in groups[grp]]

    def get_group_files():
        if d.get("file") is None:
            return None
        if grp is None:
            return [parse_file(d)]
        return [parse_file(m) for m in groups[grp]]

    reply = id_map.get(d.get("reply_to_message_id"))
    # Resolve reply group to the final message id
    if reply and reply.get('media_group_id'):
        reply = id_map.get(processed_groups[reply.get("media_group_id")])

    msg = {
        "id": d["id"],
        "date": d["date"],
        "type": None if d.get("type") == "message" else d.get("type"),
        "text": get_group_text(),
        "views": d.get("views"),  # Views cannot be exported in the current version
        "images": get_group_images(),
        "forwarded_from": d.get("forwarded_from"),

        # TODO: Add this in front end
        "video": None if d.get("media_type") != "video_file" else {
            "thumb": d.get("thumbnail"), "duration": d.get("duration_seconds"), "src": d.get("file")
        },
        "reply": None if reply is None else {
            "id": reply['id'],
            "text": plain_text(reply.get("text")),
            "thumb": reply.get("thumbnail") or reply.get("photo"),
        },
        "author": d.get("author"),
        "files": get_group_files()
        # TODO: Add more fields
    }

    # Convert image file group to photo group
    if msg.get('files') and msg['files'][0]['media_type'] == 'photo':
        msg['images'] = msg.pop('files')

    return remove_nones(msg)


def infer_groups(msgs: list[dict]):
    """
    Infer message media/file/photo groups from timestamp and media type

    :param msgs: Messages (will be modified)
    :return: None
    """
    i = 0
    c_group = 0
    c_type = ""
    c_time = 0
    c_count = 0
    while i < len(msgs):
        it = msgs[i]
        time = int(it['date_unixtime'])

        if it.get('photo'):
            ty = "photo"
        else:
            ty = it.get("media_type")

        try:
            # Type cannot be a sticker / video / regular message
            assert ty is not None and ty != "sticker" and ty != 'video'

            # Timestamps are within 5 seconds
            assert abs(c_time - time) < 5

            # Types must match
            assert c_type == ty

            # Assign group id
            msgs[i - 1]['media_group_id'] = c_group
            it['media_group_id'] = c_group
            c_count += 1

        except AssertionError:
            c_type = ty
            c_time = time
            c_count = 0
            c_group += 1
            pass

        i += 1


p: Path
id_map: dict[int, dict]
groups: dict[int, list[dict]]
processed_groups: dict[int, int]


def convert_original_filenames(json_path: Path):
    """
    Convert filenames in the original result.json
    """
    renamed: dict[str, str] = {}
    results = json.loads(json_path.read_text())

    if results.get('processed'):
        return

    for k in ['file', 'thumbnail']:
        for r in [r for r in results['messages'] if k in r]:
            orig = str(r[k])
            if orig in renamed:
                r[k] = renamed[orig]
                continue

            f = p / r[k]
            new = f.with_name(f"{r['id']}{'_thumb' if k == 'thumbnail' else ''}{f.suffix}")
            np = str(new.relative_to(p))
            if new != f:
                printc(f"&6Renaming &r{orig} &6to &r{np}")
                shutil.move(f, new)
                if k == 'file':
                    r['original_name'] = f.name
                r[k] = np
                renamed[orig] = np
    results['processed'] = True

    write(json_path, json_stringify(results, indent=2))


def run():
    global p, id_map, groups, processed_groups
    parser = argparse.ArgumentParser("Telegram export converter",
                                     description="A tool to convert exported json into tg-blog json")
    parser.add_argument("dir", help="Export directory")
    args = parser.parse_args()

    p = Path(args.dir)
    f = p / "result.json"
    assert f.is_file(), f"Error: File {f} not found"

    # Convert file names to url-safe file names
    convert_original_filenames(f)

    # Read export result json
    j: list[dict] = json.loads(f.read_text())["messages"]
    id_map = {d['id']: d for d in j}

    # Assign groups
    infer_groups(j)

    # Group groups
    tmp_grouped: list[dict] = [d for d in j if 'media_group_id' in d]
    group_ids: set[int] = {d['media_group_id'] for d in tmp_grouped}
    groups = {g: [d for d in tmp_grouped if d['media_group_id'] == g] for g in group_ids}
    processed_groups = {}

    # print(json.dumps(j, indent=2, ensure_ascii=False))

    # Convert
    j = [convert_msg(d) for d in j]
    j = [d for d in j if d is not None]

    write(p / "posts.json", json_stringify(j, indent=2))
    write(p / "index.html", HTML.replace("$$POSTS_DATA$$", json_stringify(j)))

    printc(f"&aDone! Saved to {p / 'posts.json'}")


if __name__ == '__main__':
    run()
